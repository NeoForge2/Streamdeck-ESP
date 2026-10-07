"""Synchronise la barre/l'etiquette des 3 encodeurs avec la vraie valeur
qu'ils pilotent - volume general Windows, volume d'une application, ou
une entite Home Assistant (luminosite, volume, vitesse, position,
temperature) - au lieu du compteur brut local de l'encodeur (voir
firmware/encoder_sync.yaml, qui decouple l'affichage de la rotation
physique).

Pas de nouveau champ de configuration : la "source" de chaque encodeur
est deduite de ses actions sens horaire/antihoraire deja configurees
(encoder_source()) - si les deux sont symetriques (meme cible, sens
opposes), on sait ce que l'encodeur represente et on peut en lire la
vraie valeur pour l'afficher, en plus de la piloter."""

from __future__ import annotations

import logging
import threading

from . import app_volume
from . import ha_client as ha
from .actions import SYSTEM
from .device_client import DeviceClient

LOG = logging.getLogger("streamdeck_encoder_sync")

POLL_INTERVAL = 2.0


def encoder_source(enc: dict) -> dict | None:
    """Deduit ce qu'un encodeur pilote reellement a partir de ses actions
    sens horaire ('clockwise')/antihoraire ('anticlockwise') - None si
    elles ne sont pas symetriques (meme cible, sens opposes) ou pas d'un
    type pris en charge, auquel cas la barre reste neutre (voir
    device_client.py::active_profile pour la forme du profil)."""
    cw = enc.get("clockwise") or {}
    ccw = enc.get("anticlockwise") or {}
    cw_type, ccw_type = cw.get("type", "none"), ccw.get("type", "none")

    if cw_type == "media" and ccw_type == "media":
        if cw.get("target") == "vol_up" and ccw.get("target") == "vol_down":
            return {"kind": "windows_volume"}
        return None

    if cw_type == "app_volume" and ccw_type == "app_volume":
        cw_dir, _, cw_app = (cw.get("target") or "").partition(":")
        ccw_dir, _, ccw_app = (ccw.get("target") or "").partition(":")
        if cw_dir == "up" and ccw_dir == "down" and cw_app and cw_app == ccw_app:
            return {"kind": "app_volume", "app": cw_app}
        return None

    if cw_type == "home_assistant" and ccw_type == "home_assistant":
        cw_target, ccw_target = cw.get("target") or {}, ccw.get("target") or {}
        entity_id = cw_target.get("entity_id")
        if entity_id and entity_id == ccw_target.get("entity_id"):
            domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
            if ha.encoder_display_domain(domain):
                return {"kind": "home_assistant", "entity_id": entity_id}
        return None

    if cw_type == "ha_adjust" and ccw_type == "ha_adjust":
        cw_dir, _, cw_entity = (cw.get("target") or "").partition(":")
        ccw_dir, _, ccw_entity = (ccw.get("target") or "").partition(":")
        if cw_dir == "up" and ccw_dir == "down" and cw_entity and cw_entity == ccw_entity:
            domain = cw_entity.split(".", 1)[0] if "." in cw_entity else ""
            if ha.encoder_display_domain(domain):
                return {"kind": "home_assistant", "entity_id": cw_entity}
        return None

    return None


def _read_source(device_client: DeviceClient, source: dict) -> tuple[float, str] | None:
    kind = source["kind"]
    if kind in ("windows_volume", "app_volume") and SYSTEM != "Windows":
        return None
    if kind == "windows_volume":
        pct = app_volume.get_system_volume()
    elif kind == "app_volume":
        pct = app_volume.get_app_volume(source["app"])
    elif kind == "home_assistant":
        ha_conf = device_client.config.get("home_assistant") or {}
        client = ha.HomeAssistantClient(ha_conf.get("url", ""), ha_conf.get("token", ""))
        if not client.configured:
            return None
        return ha.read_entity_level(client, source["entity_id"])
    else:
        return None
    return (pct, f"{pct}%") if pct is not None else None


def poll_once(device_client: DeviceClient) -> None:
    if not device_client.connected:
        return
    encoders = device_client.active_profile().get("encoders") or []
    for idx, enc in enumerate(encoders):
        source = encoder_source(enc or {})
        if source is None:
            continue
        try:
            result = _read_source(device_client, source)
        except Exception:
            LOG.exception("Echec de lecture de la source de l'encodeur %d (%s)", idx + 1, source)
            continue
        if result is None:
            continue
        pct, label = result
        device_client.schedule_push_encoder_display(idx, pct, label)


def run_forever(device_client: DeviceClient, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            poll_once(device_client)
        except Exception:
            LOG.exception("Echec de la synchronisation des encodeurs")
        stop_event.wait(POLL_INTERVAL)
