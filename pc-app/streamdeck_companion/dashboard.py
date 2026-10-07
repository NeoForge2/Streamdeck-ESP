"""Page de configuration visuelle du Stream Deck, en 2 pages pour eviter la
surcharge (esprit "gerer ses pages d'applications sur son iPhone") :

- **Accueil** (`/`) : la grille des emplacements (36 possibles) ET les 3 encodeurs,
  chacun configurable via sa propre popup (glisser-deposer pour les
  emplacements). C'est la seule page qu'on utilise au quotidien - plus
  besoin d'une page separee pour les encodeurs.
- **Reglages** (`/reglages`) : connexion a l'ecran, cle API, Home
  Assistant, forme des boutons - des reglages qu'on ne touche qu'une fois.
  Demandee automatiquement au tout premier lancement (connexion vide).

Chaque page sauvegarde uniquement SA partie de la config (pas de risque
d'ecraser les emplacements en modifiant les reglages, etc.) et pousse vers
l'ecran via device_client.DeviceClient (connexion deja ouverte, pas de
reconnexion).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import requests
from flask import Flask, Response, jsonify, redirect, render_template, request, url_for

from . import actions as action_runner
from . import app_volume
from . import audio_devices
from . import ha_client
from . import ha_mqtt
from . import icon_extract
from . import icons
from . import profiles as profile_utils
from .app_library import list_installed_apps
from .browse import browse_for_executable
from .custom_apps import add_custom_app, list_custom_apps, remove_custom_app
from .device_client import DEFAULT_CONFIG_PATH, SLOT_COUNT, DeviceClient, load_config, save_config
from .profile_watcher import list_open_windows

LOG = logging.getLogger("streamdeck_dashboard")

DASHBOARD_PORT = 8080

app = Flask(__name__)
_config_path: Path = DEFAULT_CONFIG_PATH
_device_client: DeviceClient | None = None

ACTION_TYPES = [
    "none", "keys", "launch", "url", "media", "home_assistant", "audio_output",
    "app_volume", "app_mute", "ha_adjust",
]
# Sous-ensemble propose sur un BOUTON (popup d'emplacement) - exclut
# ha_adjust/app_volume, qui n'ont de sens qu'avec un sens de rotation
# horaire/antihoraire (augmenter/diminuer par pas) : sur un bouton
# (simple clic), ils faisaient doublon avec "home_assistant"/"app_mute"
# sans que la difference soit claire. Restent proposes tels quels sur les
# encodeurs (voir ENCODER_ACTION_TYPES), leur seul contexte utile.
SLOT_ACTION_TYPES = [t for t in ACTION_TYPES if t not in ("ha_adjust", "app_volume")]
ENCODER_ACTION_TYPES = ACTION_TYPES
# Libelles en clair pour le menu deroulant du type d'action (voir
# home.html) - les noms techniques ci-dessus (ACTION_TYPES) restent les
# valeurs stockees en config/comparees en JS, seul le texte affiche change.
ACTION_TYPE_LABELS = {
    "none": "Aucune",
    "keys": "Raccourci clavier",
    "launch": "Lancer une application",
    "url": "Ouvrir un site web",
    "media": "Musique / volume du PC",
    "home_assistant": "Action Home Assistant (ex: allumer, eteindre, basculer...)",
    "audio_output": "Changer de haut-parleur",
    "app_volume": "Volume d'une application",
    "app_mute": "Couper le son d'une application",
    "ha_adjust": "Ajuster un appareil Home Assistant",
}
SLOT_TYPES = ["bouton", "barre", "texte"]
SLOT_TYPE_LABELS = {
    "bouton": "Bouton - declenche une action au clic",
    "barre": "Jauge - affiche une valeur Home Assistant en barre (ex: batterie, luminosite)",
    "texte": "Texte - affiche une valeur Home Assistant en chiffres (ex: temperature)",
}
DIRECTIONS = ["clockwise", "anticlockwise", "press"]


def field_to_target(action_type: str, field_value: str):
    """'keys' se stocke en liste (ex ["ctrl","shift","s"]) ; 'home_assistant'
    se stocke en dict (parse_ha_target) ; les autres restent une chaine."""
    if action_type == "keys":
        return [part.strip() for part in field_value.split("+") if part.strip()]
    if action_type == "home_assistant":
        return parse_ha_target(field_value)
    return field_value


def target_to_field(action_type: str, target) -> str:
    if action_type == "keys" and isinstance(target, list):
        return "+".join(target)
    if action_type == "home_assistant" and isinstance(target, dict):
        return format_ha_target(target)
    return target or ""


def parse_ha_target(field_value: str) -> dict:
    """Format compact 'domaine.service:entity_id', ex 'light.toggle:light.bureau'."""
    try:
        service_part, entity_id = field_value.split(":", 1)
        domain, service = service_part.split(".", 1)
        return {"domain": domain.strip(), "service": service.strip(), "entity_id": entity_id.strip()}
    except ValueError:
        return {"domain": "", "service": "", "entity_id": ""}


def format_ha_target(action: dict) -> str:
    domain, service, entity_id = action.get("domain", ""), action.get("service", ""), action.get("entity_id", "")
    return f"{domain}.{service}:{entity_id}" if domain and service else ""


def normalize_slots(raw_slots: list[dict] | None) -> list[dict]:
    """Complete a exactement SLOT_COUNT emplacements PHYSIQUES (position/
    taille + quelle entree de bibliotheque y est assignee - voir
    profiles.py::resolve_slot pour le contenu resolu). Tronque/complete
    avec des valeurs par defaut si la config sur disque en a moins/plus."""
    slots = list(raw_slots or [])
    normalized = []
    for i in range(SLOT_COUNT):
        slot = {**profile_utils.default_slot(i), **(slots[i] if i < len(slots) else {})}
        normalized.append(slot)
    return normalized


def normalize_library(raw_library: list[dict] | None) -> list[dict]:
    """Bibliotheque de boutons enregistres - PAS limitee a SLOT_COUNT (voir
    profiles.py, module docstring) : autant d'entrees que l'utilisateur en
    cree, seules SLOT_COUNT peuvent etre assignees a un emplacement visible
    a la fois. Complete chaque entree avec les valeurs par defaut (profils
    enregistres avant l'introduction de la bibliotheque)."""
    normalized = []
    for entry in (raw_library or []):
        entry_id = entry.get("id") or f"lib-{len(normalized)}-{id(entry)}"
        merged = {**profile_utils.default_library_entry(entry_id), **entry, "id": entry_id}
        if merged["type"] != "bouton":
            merged["action"] = {"type": "none", "target": ""}
        normalized.append(merged)
    return normalized


def normalize_weather(raw_weather: dict | None) -> dict:
    """Complete la carte meteo avec les valeurs par defaut - profils
    enregistres avant l'introduction de ce widget (pas de cle 'weather')."""
    return {**profile_utils.default_weather(), **(raw_weather or {})}


def push_to_screen() -> str | None:
    """Tente de pousser la config vers l'ecran. Retourne un message d'erreur
    (ou None si tout va bien) - a chaque endpoint de decider quoi en faire."""
    if _device_client is None:
        return None
    try:
        _device_client.schedule_push()
        return None
    except Exception as exc:
        LOG.exception("Echec de l'envoi vers l'ecran")
        return str(exc)


def encoders_to_fields(encoders: list[dict]) -> list[dict]:
    """Convertit les cibles (liste/dict selon le type) en simples chaines
    affichables/editables dans les champs du popup encodeur."""
    return [
        {
            direction: {
                **enc.get(direction, {}),
                "target": target_to_field(
                    enc.get(direction, {}).get("type", "none"), enc.get(direction, {}).get("target")
                ),
            }
            for direction in DIRECTIONS
        }
        for enc in (encoders or profile_utils.default_encoders())
    ]


def fields_to_encoders(raw_encoders: list[dict]) -> list[dict]:
    encoders = []
    for i in range(3):
        enc = raw_encoders[i] if i < len(raw_encoders) else {}
        encoders.append({
            direction: {
                "type": (t := (enc.get(direction) or {}).get("type", "none")),
                "target": field_to_target(t, (enc.get(direction) or {}).get("target", "")),
            }
            for direction in DIRECTIONS
        })
    return encoders


def profile_to_fields(profile: dict) -> dict:
    """Version d'un profil prete pour le template/JS : emplacements
    physiques (position/assignation) + bibliotheque complete (avec
    action_field), encoders en forme champ texte. La resolution
    emplacement<->contenu se fait cote JS (voir dashboard.js::resolveSlot),
    comme pour weather/encoders - le backend ne fait que normaliser/
    persister."""
    library = normalize_library(profile.get("library"))
    for entry in library:
        entry["action_field"] = target_to_field(entry["action"].get("type", "none"), entry["action"].get("target"))
    return {
        "name": profile.get("name", profile_utils.DEFAULT_PROFILE_NAME),
        "trigger": profile.get("trigger"),
        "slots": normalize_slots(profile.get("slots")),
        "library": library,
        "encoders": encoders_to_fields(profile.get("encoders")),
        "weather": normalize_weather(profile.get("weather")),
    }


def _resolve_icon_char(entry: dict) -> str:
    """Icone poussee vers l'ecran (voir device_client.py::push_config) :
    icone reelle de l'appli/jeu si l'action est 'launch' et que
    l'extraction reussit tout de suite (voir icon_extract.py - Windows
    uniquement, appelle deja l'extraction pour peupler son cache et
    valider la cible), sinon le glyphe Material Icons choisi (icons.py)."""
    action = entry.get("action") or {}
    if action.get("type") == "launch":
        target = action.get("target") or ""
        if icon_extract.extract_icon_png(target) is not None:
            return f"REAL:{icon_extract.icon_version(target)}"
    return icons.icon_char(entry.get("icon", ""))


def fields_to_profile(raw_profile: dict) -> dict:
    """Inverse de profile_to_fields : reconvertit un profil recu du
    formulaire (bibliotheque/encoders en forme champ texte) vers le format
    persistable dans dashboard_config.yaml."""
    library = normalize_library(raw_profile.get("library"))
    for entry in library:
        action_type = entry.get("action", {}).get("type", "none")
        action_field = entry.pop("action_field", "")
        entry["action"] = {"type": action_type, "target": field_to_target(action_type, action_field)}
        entry["show_light_color"] = bool(entry.get("show_light_color"))
        entry["icon_char"] = _resolve_icon_char(entry)
        entry["label"] = (entry.get("label") or "").strip()[:24] or entry["label"]
    library_ids = {entry["id"] for entry in library}
    slots = normalize_slots(raw_profile.get("slots"))
    for slot in slots:
        # Une entree assignee a un emplacement peut avoir ete supprimee de
        # la bibliotheque entre-temps (voir "Supprimer" du popup) - on
        # libere alors l'emplacement plutot que de garder une reference
        # morte.
        if slot.get("library_id") not in library_ids:
            slot["library_id"] = None
    name = (raw_profile.get("name") or "").strip()[:24] or profile_utils.DEFAULT_PROFILE_NAME
    trigger = raw_profile.get("trigger")
    trigger = {"process": trigger["process"].strip()} if trigger and (trigger.get("process") or "").strip() else None
    return {
        "name": name,
        "trigger": trigger,
        "slots": slots,
        "library": library,
        "encoders": fields_to_encoders(raw_profile.get("encoders") or []),
        "weather": normalize_weather(raw_profile.get("weather")),
    }


@app.route("/", methods=["GET"])
def index():
    config = load_config(_config_path)
    if not (config.get("connection") or {}).get("host"):
        return redirect(url_for("settings", premiere_fois="1"))
    profiles = [profile_to_fields(p) for p in profile_utils.migrate_profiles(config)]
    active_profile_name = _device_client.active_profile_name if _device_client else None
    manual_override = bool(_device_client and _device_client.manual_override)
    return render_template(
        "home.html",
        active_page="home",
        profiles=profiles,
        active_profile_name=active_profile_name or (profiles[0]["name"] if profiles else None),
        manual_override=manual_override,
        shape=config.get("shape", "carre"),
        action_types=SLOT_ACTION_TYPES,
        encoder_action_types=ENCODER_ACTION_TYPES,
        action_type_labels=ACTION_TYPE_LABELS,
        slot_types=SLOT_TYPES,
        slot_type_labels=SLOT_TYPE_LABELS,
        directions=DIRECTIONS,
        icon_choices=icons.icon_choices(),
        saved=request.args.get("saved") == "1",
        error=request.args.get("error"),
    )


@app.route("/save", methods=["POST"])
def save():
    config = load_config(_config_path)
    try:
        raw_profiles = json.loads(request.form.get("profiles_json", "[]"))
    except (TypeError, ValueError):
        raw_profiles = []
    if raw_profiles:
        profiles = [fields_to_profile(p) for p in raw_profiles]
        config["profiles"] = profiles
        config.pop("slots", None)  # ancien format pre-profils, remplace par profiles[0]
        config.pop("encoders", None)
    else:
        # profiles_json vide/invalide : ne pas ecraser la config existante.
        profiles = profile_utils.migrate_profiles(config)
    save_config(_config_path, config)

    if _device_client is not None:
        _device_client.profiles = profiles

    error = push_to_screen()
    if error:
        return redirect(url_for("index", error=error))
    return redirect(url_for("index", saved="1"))


@app.route("/profiles/force", methods=["POST"])
def force_profile():
    """Bouton "Forcer ce profil" d'un onglet : fige l'ecran sur ce profil
    jusqu'a "Automatique" (utile pour previsualiser un profil qu'on vient
    d'editer sans attendre que son application soit au premier plan)."""
    name = request.form.get("name", "")
    if _device_client is None:
        return jsonify({"error": "Non connecte a l'ecran"}), 400
    try:
        _device_client.schedule_force_profile(name)
    except Exception as exc:
        LOG.exception("Echec du changement de profil force")
        return jsonify({"error": str(exc)}), 500
    return jsonify({"ok": True, "active_profile_name": _device_client.active_profile_name})


@app.route("/profiles/auto", methods=["POST"])
def auto_profile():
    """Reprend la bascule automatique de profil (profile_watcher.py)."""
    if _device_client is not None:
        _device_client.schedule_clear_override()
    return jsonify({"ok": True})


@app.route("/profiles/status", methods=["GET"])
def profiles_status():
    """Sondee periodiquement par la page pour afficher quel profil est
    reellement actif sur l'ecran (bascule automatique en arriere-plan)."""
    if _device_client is None:
        return jsonify({"active_profile_name": None, "manual_override": False})
    return jsonify({
        "active_profile_name": _device_client.active_profile_name,
        "manual_override": bool(_device_client.manual_override),
    })


@app.route("/open-windows", methods=["GET"])
def open_windows():
    """Popup profil : liste les applications actuellement ouvertes sur le
    PC pour choisir un declencheur directement dedans, plutot que de
    "detecter" la fenetre active (qui detecte toujours le navigateur, vu
    qu'il faut y cliquer un bouton pour declencher la detection)."""
    try:
        windows = list_open_windows()
    except Exception as exc:
        LOG.exception("Echec de la lecture des applications ouvertes")
        return jsonify({"error": str(exc)}), 500
    return jsonify({"windows": windows})


def _ha_error_message(exc: Exception) -> str:
    """Message d'erreur lisible pour un utilisateur non-technique - les
    exceptions brutes de `requests` (NameResolutionError, stack complet...)
    ne veulent rien dire pour quelqu'un qui configure juste une URL."""
    if isinstance(exc, requests.exceptions.Timeout):
        return "Home Assistant ne repond pas (delai depasse) - verifiez l'URL dans Reglages."
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "Impossible de joindre Home Assistant - verifiez l'URL dans Reglages."
    if isinstance(exc, requests.exceptions.HTTPError):
        status = exc.response.status_code if exc.response is not None else None
        if status == 401:
            return "Cle d'acces Home Assistant refusee - verifiez le jeton dans Reglages."
        return f"Home Assistant a repondu une erreur (code {status})."
    return str(exc)


@app.route("/ha-entities", methods=["GET"])
def ha_entities():
    """Picker d'entites Home Assistant (source d'un widget barre/texte,
    entite ciblee par une action 'home_assistant') : liste recherchable
    plutot que de taper un entity_id a la main."""
    config = load_config(_config_path)
    ha_conf = config.get("home_assistant") or {}
    client = ha_client.HomeAssistantClient(ha_conf.get("url", ""), ha_conf.get("token", ""))
    if not client.configured:
        return jsonify({"entities": [], "error": "Home Assistant n'est pas configure (voir Reglages)."})
    try:
        entities = client.list_entities()
    except Exception as exc:
        LOG.exception("Echec de la lecture des entites Home Assistant")
        return jsonify({"entities": [], "error": _ha_error_message(exc)}), 500
    return jsonify({"entities": entities})


@app.route("/ha-services/<domain>", methods=["GET"])
def ha_services(domain):
    """Services HA courants pour un domaine (ex 'light' -> toggle/turn_on/
    turn_off), pour le menu deroulant du picker d'action 'home_assistant'."""
    return jsonify({"services": ha_client.common_services(domain)})


@app.route("/audio-devices", methods=["GET"])
def audio_devices_route():
    """Picker de l'action 'audio_output' (popup d'emplacement) : liste des
    peripheriques de sortie audio actifs, pour basculer casque/enceintes
    depuis un bouton sans taper d'identifiant a la main."""
    try:
        devices = audio_devices.list_playback_devices()
    except Exception as exc:
        LOG.exception("Echec de la lecture des peripheriques audio")
        return jsonify({"devices": [], "error": str(exc)}), 500
    return jsonify({"devices": devices})


@app.route("/audio-sessions", methods=["GET"])
def audio_sessions_route():
    """Picker de l'action 'app_volume' (encodeurs) : liste des applications
    ayant actuellement une session audio active, pour regler leur volume
    sans taper le nom de l'executable a la main."""
    try:
        sessions = app_volume.list_audio_sessions()
    except Exception as exc:
        LOG.exception("Echec de la lecture des sessions audio")
        return jsonify({"sessions": [], "error": str(exc)}), 500
    return jsonify({"sessions": sessions})


@app.route("/reglages", methods=["GET"])
def settings():
    config = load_config(_config_path)
    return render_template(
        "settings.html",
        active_page="settings",
        connection=config.get("connection") or {},
        shape=config.get("shape", "carre"),
        home_assistant=config.get("home_assistant") or {},
        mqtt=config.get("mqtt") or {},
        premiere_fois=request.args.get("premiere_fois") == "1",
        saved=request.args.get("saved") == "1",
        error=request.args.get("error"),
    )


@app.route("/reglages/save", methods=["POST"])
def save_settings():
    config = load_config(_config_path)
    config["connection"] = {
        "host": request.form.get("conn_host", "").strip(),
        "port": int(request.form.get("conn_port") or 6053),
        "api_key": request.form.get("conn_key", "").strip(),
    }
    config["shape"] = request.form.get("shape", "carre")
    config["home_assistant"] = {
        "url": request.form.get("ha_url", "").strip(),
        "token": request.form.get("ha_token", "").strip(),
    }
    config["mqtt"] = {
        "host": request.form.get("mqtt_host", "").strip(),
        "port": int(request.form.get("mqtt_port") or ha_mqtt.DEFAULT_PORT),
        "username": request.form.get("mqtt_username", "").strip(),
        "password": request.form.get("mqtt_password", "").strip(),
        "base_topic": request.form.get("mqtt_base_topic", "").strip() or ha_mqtt.DEFAULT_BASE_TOPIC,
    }
    config["profiles"] = profile_utils.migrate_profiles(config)
    save_config(_config_path, config)

    error = push_to_screen()
    if error:
        return redirect(url_for("settings", error=error))
    return redirect(url_for("index" if request.form.get("premiere_fois") == "1" else "settings", saved="1"))


@app.route("/preview-icon.png", methods=["GET"])
def preview_icon():
    """Vraie icone d'une cible 'launch' pour l'apercu dans le navigateur
    (grille d'emplacements) - endpoint distinct de icon_server.py (qui sert
    l'ecran physique via le profil ACTIF) : ici on extrait directement la
    cible passee en parametre, peu importe le profil en cours d'edition."""
    target = request.args.get("target", "")
    png = icon_extract.extract_icon_png(target) if target else None
    if png is None:
        return Response(status=404)
    return Response(png, mimetype="image/png")


@app.route("/installed-apps", methods=["GET"])
def installed_apps():
    """Bibliotheque d'applications du picker (popup d'emplacement, type
    d'action 'launch') : applications detectees (raccourcis du menu
    Demarrer) + applications personnalisees ajoutees via la tuile
    "+ Ajouter" (voir custom_apps.py). Ne renvoie jamais d'erreur bloquante
    - si la detection systeme echoue (non-Windows...), on retombe juste sur
    la liste personnalisee (peut-etre vide)."""
    try:
        apps = list_installed_apps()
        detect_error = None
    except Exception as exc:
        LOG.exception("Echec de la lecture de la bibliotheque d'applications")
        apps, detect_error = [], str(exc)
    return jsonify({"apps": apps, "custom": list_custom_apps(_config_path), "detect_error": detect_error})


@app.route("/custom-apps", methods=["POST"])
def add_custom_app_route():
    """Tuile "+ Ajouter" du picker : ouvre le selecteur de fichier natif
    (browse.py) puis persiste le choix dans dashboard_config.yaml pour
    qu'il rejoigne la bibliotheque durablement (custom_apps.py)."""
    try:
        path = browse_for_executable()
    except Exception as exc:
        LOG.exception("Echec de l'ouverture du selecteur de fichier")
        return jsonify({"error": str(exc)}), 500
    if not path:
        return jsonify({"target": None})
    name = Path(path.strip('"')).stem
    apps = add_custom_app(_config_path, name, path)
    return jsonify({"name": name, "target": path, "apps": apps})


@app.route("/custom-apps/remove", methods=["POST"])
def remove_custom_app_route():
    apps = remove_custom_app(_config_path, request.form.get("target", ""))
    return jsonify({"apps": apps})


@app.route("/run", methods=["POST"])
def run_action():
    """Endpoint optionnel : permet a Home Assistant (ou tout autre outil) de
    declencher une action locale en plus du fonctionnement direct (voir
    receiver.token dans dashboard_config.yaml)."""
    config = load_config(_config_path)
    token = (config.get("receiver") or {}).get("token")
    if not token or request.headers.get("X-Auth-Token") != token:
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(force=True, silent=True) or {}
    action_type = data.get("type")
    if not action_type:
        return jsonify({"error": "champ 'type' manquant"}), 400
    try:
        action_runner.run({"type": action_type, "target": data.get("target")})
    except Exception as exc:
        LOG.exception("Echec de l'action %r", data)
        return jsonify({"error": str(exc)}), 500
    return jsonify({"ok": True})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


def run_server(config_path: Path, device_client: DeviceClient | None = None, port: int = DASHBOARD_PORT) -> None:
    global _config_path, _device_client  # noqa: PLW0603
    _config_path = config_path
    _device_client = device_client
    LOG.info("Page de configuration sur http://127.0.0.1:%d", port)
    # threaded=True : le selecteur de fichier natif (/browse-app) bloque son
    # thread le temps du choix - sans threaded=True, ca gelerait toute la
    # page de config pendant ce temps.
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
