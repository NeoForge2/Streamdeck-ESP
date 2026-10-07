"""Sondage periodique de Home Assistant pour les emplacements de type
widget (barre/texte) : relit l'etat des entites configurees toutes les
POLL_INTERVAL secondes et pousse la valeur formatee vers l'ecran via
device_client.schedule_push_values() (thread-safe, voir device_client.py).

Tourne dans son propre thread (voir tray.py) - un simple polling REST
suffit pour rafraichir une poignee de widgets, pas besoin de websocket.
"""

from __future__ import annotations

import logging
import threading

from . import ha_client as ha
from . import icons
from . import profiles as profile_utils
from . import weather as weather_module
from .device_client import DeviceClient
from .runtime_state import STATE_STORE
from .state_adapters import update_home_assistant_entity

LOG = logging.getLogger("streamdeck_ha_poller")

POLL_INTERVAL = 15.0
# Nombre d'echecs de lecture CONSECUTIFS avant de considerer une entite
# hors ligne (~30s a POLL_INTERVAL=15s) - pas un simple blip reseau isole,
# pour eviter qu'un widget clignote "Hors ligne" a chaque sondage manque.
# Tant que le seuil n'est pas atteint, la derniere valeur connue reste
# affichee telle quelle (rien n'est pousse), comme avant.
STALE_AFTER = 2
OFFLINE_TEXT = "Hors ligne"

# Compteur d'echecs consecutifs par entite - en memoire seulement (reset
# au redemarrage de l'appli), partage entre widgets et carte meteo.
_fail_counts: dict[str, int] = {}


def _read_state_or_offline(client: ha.HomeAssistantClient, entity_id: str) -> tuple[dict | None, bool]:
    """Lit l'etat HA de `entity_id`, en trackant les echecs consecutifs.

    En plus du comportement historique d'affichage, alimente le StateStore V2
    partage. Une lecture reussie publie immediatement l'etat reel ; une entite
    n'est publiee DISCONNECTED qu'apres STALE_AFTER echecs consecutifs afin de
    conserver exactement la tolerance reseau deja utilisee par les widgets.
    """
    try:
        state = client.get_state(entity_id)
    except Exception:
        LOG.exception("Echec de lecture de l'etat HA pour %s", entity_id)
        state = None
    if state is not None:
        _fail_counts[entity_id] = 0
        update_home_assistant_entity(STATE_STORE, entity_id, state)
        return state, False
    _fail_counts[entity_id] = _fail_counts.get(entity_id, 0) + 1
    offline = _fail_counts[entity_id] >= STALE_AFTER
    if offline:
        update_home_assistant_entity(STATE_STORE, entity_id, None)
    return None, offline


def poll_once(device_client: DeviceClient) -> dict[int, str]:
    """Une passe de sondage. Retourne les valeurs poussees (utile pour les
    tests). Ne fait rien si Home Assistant n'est pas configure ou si le
    client n'est pas connecte a l'ecran. Lit les emplacements du profil
    ACTIF (pas d'un eventuel config['slots'] racine, qui n'existe plus
    depuis l'introduction des profils - voir profiles.py)."""
    config = device_client.config
    ha_conf = config.get("home_assistant") or {}
    client = ha.HomeAssistantClient(ha_conf.get("url", ""), ha_conf.get("token", ""))
    if not client.configured:
        return {}
    active = device_client.active_profile()
    values: dict[int, str] = {}
    colors: dict[int, str] = {}
    for idx in range(profile_utils.SLOT_COUNT):
        slot = profile_utils.resolve_slot(active, idx)
        slot_type = slot.get("type", "bouton")
        if slot_type in ("barre", "texte"):
            entity_id = slot.get("ha_entity")
            if entity_id:
                state, offline = _read_state_or_offline(client, entity_id)
                if state is not None:
                    values[idx] = ha.format_widget_value(state, slot_type)
                elif offline and slot_type == "texte":
                    # "barre" n'a pas de texte visible (juste la jauge, voir
                    # firmware/slot_widgets.yaml) - rien de propre a afficher
                    # pour signaler hors ligne sans nouvelle entite firmware,
                    # la derniere position connue reste affichee telle quelle.
                    values[idx] = OFFLINE_TEXT

        action = slot.get("action") or {}
        if action.get("type") == "home_assistant" and slot.get("show_light_color"):
            target = action.get("target") or {}
            entity_id = target.get("entity_id")
            if target.get("domain") == "light" and entity_id:
                # Pas d'indicateur hors ligne dedie ici (contrairement a
                # texte/meteo) : sans lecture recente, l'apercu couleur
                # reste simplement a sa derniere valeur connue - acceptable
                # pour un simple apercu, pas la donnee principale du bouton.
                state, _offline = _read_state_or_offline(client, entity_id)
                if state is not None:
                    colors[idx] = ha.light_color_hex(state)

    weather = active.get("weather") or {}
    if weather.get("visible") and weather.get("entity"):
        weather_entity = weather["entity"]
        try:
            info = weather_module.read_weather(client, weather_entity)
        except Exception:
            LOG.exception("Echec de lecture de la carte meteo pour %s", weather_entity)
            info = None
        if info is not None:
            _fail_counts[weather_entity] = 0
            if device_client.connected:
                device_client.schedule_push_weather_display(
                    info["icon_char"], info["animation_style"], info["temperature"], info["condition_label"]
                )
        else:
            _fail_counts[weather_entity] = _fail_counts.get(weather_entity, 0) + 1
            if _fail_counts[weather_entity] >= STALE_AFTER and device_client.connected:
                device_client.schedule_push_weather_display(icons.icon_char("warning"), "aucune", OFFLINE_TEXT, "")

    if device_client.connected:
        if values:
            device_client.schedule_push_values(values)
        if colors:
            device_client.schedule_push_slot_colors(colors)
    return values


def run_forever(device_client: DeviceClient, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            poll_once(device_client)
        except Exception:
            LOG.exception("Echec du sondage Home Assistant")
        stop_event.wait(POLL_INTERVAL)
