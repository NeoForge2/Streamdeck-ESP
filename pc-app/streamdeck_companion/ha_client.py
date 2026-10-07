"""Client Home Assistant minimal : lecture d'etat et appel de service via
l'API REST (pas de websocket - un polling simple suffit pour rafraichir
quelques widgets toutes les quelques secondes, voir ha_poller.py).

Utilise pour :
- les emplacements de type widget ("barre"/"texte") qui affichent l'etat
  en direct d'une entite Home Assistant (temperature, volume, etc.)
- le type d'action "home_assistant" (un bouton qui appelle un service HA,
  ex: basculer une lumiere/prise/scene)
- le picker d'entites de la popup d'emplacement (list_entities), pour
  choisir une entite dans une liste recherchable plutot que de taper son
  entity_id a la main.
"""

from __future__ import annotations

import math

import requests

# Services HA courants par domaine, pour le menu deroulant du picker
# d'action "home_assistant" - pas une introspection complete de l'API HA
# (qui exposerait des centaines de services), juste les plus utiles pour
# un bouton de Stream Deck. "toggle" en tete quand disponible (le plus
# frequent pour un bouton).
COMMON_SERVICES: dict[str, list[str]] = {
    "light": ["toggle", "turn_on", "turn_off"],
    "switch": ["toggle", "turn_on", "turn_off"],
    "fan": ["toggle", "turn_on", "turn_off"],
    "input_boolean": ["toggle", "turn_on", "turn_off"],
    "cover": ["toggle", "open_cover", "close_cover", "stop_cover"],
    "lock": ["lock", "unlock"],
    "climate": ["turn_on", "turn_off", "set_temperature"],
    "media_player": [
        "media_play_pause", "media_play", "media_pause", "media_stop",
        "media_next_track", "media_previous_track", "volume_up", "volume_down", "volume_mute",
    ],
    "scene": ["turn_on"],
    "script": ["turn_on"],
    "automation": ["trigger", "turn_on", "turn_off"],
    "vacuum": ["start", "pause", "stop", "return_to_base"],
    "alarm_control_panel": ["alarm_arm_away", "alarm_arm_home", "alarm_disarm"],
    "update": ["install", "skip", "clear_skipped"],
}
DEFAULT_SERVICES = ["turn_on", "turn_off", "toggle"]


def common_services(domain: str) -> list[str]:
    return COMMON_SERVICES.get(domain, DEFAULT_SERVICES)


class HomeAssistantClient:
    def __init__(self, base_url: str, token: str, timeout: float = 5.0):
        self.base_url = (base_url or "").rstrip("/")
        self.token = token or ""
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.token)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def get_state(self, entity_id: str) -> dict | None:
        if not self.configured or not entity_id:
            return None
        url = f"{self.base_url}/api/states/{entity_id}"
        resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def list_entities(self) -> list[dict]:
        """Toutes les entites de l'installation HA, pour le picker
        recherchable (popup d'emplacement) - evite d'avoir a connaitre/
        taper un entity_id a la main."""
        if not self.configured:
            return []
        url = f"{self.base_url}/api/states"
        resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
        resp.raise_for_status()
        entities = []
        for item in resp.json():
            entity_id = item.get("entity_id", "")
            domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
            name = (item.get("attributes") or {}).get("friendly_name") or entity_id
            entities.append({
                "entity_id": entity_id,
                "name": name,
                "domain": domain,
                "state": item.get("state", ""),
            })
        entities.sort(key=lambda e: e["name"].lower())
        return entities

    def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str | None = None,
        data: dict | None = None,
    ) -> None:
        if not self.configured:
            raise RuntimeError("Home Assistant n'est pas configure (url/token manquants)")
        url = f"{self.base_url}/api/services/{domain}/{service}"
        payload = dict(data or {})
        if entity_id:
            payload.setdefault("entity_id", entity_id)
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
        resp.raise_for_status()


def _kelvin_to_hex(kelvin: float) -> str:
    """Approxime une couleur RGB a partir d'une temperature de couleur
    (algorithme de Tanner Helland), pour les ampoules "blanc variable" qui
    n'exposent pas de rgb_color propre - juste assez fidele pour un
    indicateur visuel sur un petit bouton, pas une reproduction exacte."""
    temp = max(1000.0, min(40000.0, kelvin)) / 100.0
    if temp <= 66:
        red = 255.0
        green = 99.4708025861 * math.log(temp) - 161.1195681661
    else:
        red = 329.698727446 * ((temp - 60) ** -0.1332047592)
        green = 288.1221695283 * ((temp - 60) ** -0.0755148492)
    if temp >= 66:
        blue = 255.0
    elif temp <= 19:
        blue = 0.0
    else:
        blue = 138.5177312231 * math.log(temp - 10) - 305.0447927307

    def clamp(v: float) -> int:
        return max(0, min(255, round(v)))

    return f"#{clamp(red):02X}{clamp(green):02X}{clamp(blue):02X}"


def light_color_hex(state: dict) -> str:
    """Couleur hex (format '#RRGGBB') a pousser vers le slot lie a une
    ampoule : sa vraie couleur RGB si l'ampoule en expose une, sinon une
    approximation depuis sa temperature de couleur (ampoules "blanc
    variable"), sinon un blanc chaud generique (ampoule on/off simple,
    sans aucune info de couleur). Chaine vide si eteinte - le firmware
    revient alors a la couleur par defaut du bouton (voir
    firmware/slots_*.yaml, entites 'Slot N - couleur')."""
    if (state or {}).get("state") != "on":
        return ""
    attrs = state.get("attributes") or {}
    rgb = attrs.get("rgb_color")
    if isinstance(rgb, (list, tuple)) and len(rgb) == 3:
        r, g, b = (max(0, min(255, int(c))) for c in rgb)
        return f"#{r:02X}{g:02X}{b:02X}"
    kelvin = attrs.get("color_temp_kelvin")
    if not kelvin and attrs.get("color_temp"):
        kelvin = 1_000_000 / attrs["color_temp"]  # mired -> kelvin
    if kelvin:
        return _kelvin_to_hex(kelvin)
    return "#FFE9B0"


# Domaines dont un widget "barre" peut ajuster la valeur au tactile
# (gauche/droite sur l'ecran, voir device_client.py::_adjust_barre) :
# attribut a lire pour l'etat courant, echelle pour le convertir en 0-100,
# service/parametre a appeler pour l'ecrire. "as_fraction" : le parametre
# HA attend 0.0-1.0 plutot que 0-100 (ex volume_level).
_PERCENT_ADJUSTABLE: dict[str, dict] = {
    "light": {"attr": "brightness", "scale": 255, "service": "turn_on", "param": "brightness_pct"},
    "media_player": {
        "attr": "volume_level", "scale": 1.0, "service": "volume_set", "param": "volume_level", "as_fraction": True,
    },
    "fan": {"attr": "percentage", "scale": 100, "service": "set_percentage", "param": "percentage"},
    "cover": {"attr": "current_position", "scale": 100, "service": "set_cover_position", "param": "position"},
}

# Domaines dont la barre d'un encodeur peut afficher la vraie valeur (voir
# encoder_sync.py) - reutilise les memes domaines que _PERCENT_ADJUSTABLE
# (echelle fixe 0-scale) plus 'climate', dont la temperature cible n'est
# pas un pourcentage : "range" indique de calculer le pourcentage a partir
# de min_attr/max_attr (attributs de l'entite, ou une plage par defaut si
# absents) plutot que d'une echelle fixe, et "unit" formate l'etiquette
# affichee en valeur reelle (ex "21.5°C") plutot qu'en "%".
_ENCODER_DISPLAY: dict[str, dict] = {
    **_PERCENT_ADJUSTABLE,
    "climate": {
        "attr": "temperature", "range": True,
        "min_attr": "min_temp", "max_attr": "max_temp", "default_min": 7.0, "default_max": 35.0, "unit": "°C",
        "service": "set_temperature", "param": "temperature", "step": 0.5,
    },
}


def _adjust_scale(client: "HomeAssistantClient", domain: str, spec: dict, entity_id: str, direction: int, step: int) -> None:
    state = client.get_state(entity_id)
    if state is None:
        raise RuntimeError(f"Entite introuvable : {entity_id}")
    raw = (state.get("attributes") or {}).get(spec["attr"])
    try:
        current_pct = round(float(raw) / spec["scale"] * 100) if raw is not None else 0
    except (TypeError, ValueError, ZeroDivisionError):
        current_pct = 0
    new_pct = max(0, min(100, current_pct + direction * step))
    value = new_pct / 100 if spec.get("as_fraction") else new_pct
    client.call_service(domain, spec["service"], entity_id=entity_id, data={spec["param"]: value})


def adjust_entity_percent(client: "HomeAssistantClient", entity_id: str, direction: int, step: int = 5) -> None:
    """Augmente/diminue (direction +1/-1) la valeur d'une entite HA d'un
    widget "barre" par pas de `step` %, pour l'ajustement tactile gauche/
    droite sur l'ecran - lit l'etat courant pour partir de la bonne valeur
    plutot que d'ecraser avec une valeur absolue arbitraire."""
    domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
    spec = _PERCENT_ADJUSTABLE.get(domain)
    if not spec:
        raise ValueError(f"Ajustement tactile non pris en charge pour le domaine {domain!r}")
    _adjust_scale(client, domain, spec, entity_id, direction, step)


def adjust_encoder_entity(client: "HomeAssistantClient", entity_id: str, direction: int) -> None:
    """Augmente/diminue (direction +1/-1) la valeur reellement pilotee par
    un encodeur configure en action 'ha_adjust' (voir
    device_client.py::_run_ha_adjust) - meme principe que
    adjust_entity_percent (ajustement tactile des barres) mais etendu aux
    domaines a plage reelle plutot qu'a echelle 0-100 (climate : la
    temperature cible se regle par pas de `step` degres, pas par pourcentage),
    et destine a la rotation d'un encodeur plutot qu'un tap tactile - permet
    de vraiment regler fan/cover/climate au lieu de se limiter a l'affichage
    de encoder_sync.py quand aucun service HA sans parametre n'existe
    (ex: pas de 'climate.increase_temperature')."""
    domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
    spec = _ENCODER_DISPLAY.get(domain)
    if not spec:
        raise ValueError(f"Ajustement par encodeur non pris en charge pour le domaine {domain!r}")
    if not spec.get("range"):
        _adjust_scale(client, domain, spec, entity_id, direction, step=1)
        return
    state = client.get_state(entity_id)
    if state is None:
        raise RuntimeError(f"Entite introuvable : {entity_id}")
    attrs = state.get("attributes") or {}
    try:
        current = float(attrs.get(spec["attr"]))
    except (TypeError, ValueError):
        current = spec["default_min"]
    lo = float(attrs.get(spec["min_attr"]) or spec["default_min"])
    hi = float(attrs.get(spec["max_attr"]) or spec["default_max"])
    new_value = max(lo, min(hi, current + direction * spec["step"]))
    client.call_service(domain, spec["service"], entity_id=entity_id, data={spec["param"]: new_value})


def encoder_display_domain(domain: str) -> bool:
    """True si `domain` fait partie des domaines dont un encodeur peut
    afficher la vraie valeur (voir encoder_sync.py::encoder_source)."""
    return domain in _ENCODER_DISPLAY


def read_entity_level(client: "HomeAssistantClient", entity_id: str) -> tuple[float, str] | None:
    """(pourcentage 0-100 pour la barre, etiquette humaine pour le texte)
    de `entity_id`, ou None si le domaine n'est pas pris en charge ou que
    l'attribut est absent (entite eteinte/indisponible) - voir
    encoder_sync.py, qui pousse ces deux valeurs vers l'ecran."""
    domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
    spec = _ENCODER_DISPLAY.get(domain)
    if not spec:
        return None
    state = client.get_state(entity_id)
    if state is None:
        return None
    raw = (state.get("attributes") or {}).get(spec["attr"])
    if raw is None:
        return None
    try:
        raw = float(raw)
    except (TypeError, ValueError):
        return None
    if spec.get("range"):
        attrs = state.get("attributes") or {}
        lo = float(attrs.get(spec["min_attr"]) or spec["default_min"])
        hi = float(attrs.get(spec["max_attr"]) or spec["default_max"])
        pct = 0.0 if hi <= lo else max(0.0, min(100.0, (raw - lo) / (hi - lo) * 100))
        label = f"{raw:g}{spec['unit']}"
    else:
        pct = max(0.0, min(100.0, raw / spec["scale"] * 100))
        label = f"{round(pct)}%"
    return pct, label


def format_widget_value(state: dict, slot_type: str) -> str:
    """Convertit un etat HA en texte a pousser vers l'ecran.

    'barre' -> pourcentage entier 0-100 (l'entite doit avoir un etat
    numerique, ex: un capteur de volume/luminosite/batterie).
    'texte' -> valeur brute + unite si connue (ex: '21.5°C')."""
    raw = state.get("state", "")
    if slot_type == "barre":
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return "0"
        value = max(0, min(100, round(value)))
        return str(int(value))
    unit = (state.get("attributes") or {}).get("unit_of_measurement", "")
    return f"{raw}{unit}" if unit else str(raw)
