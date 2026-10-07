"""Petit serveur HTTP separe (0.0.0.0, port dedie) qui ne sert QUE les
icones reelles d'appli/jeu pour l'ecran (voir icon_extract.py,
firmware/slot_icons.yaml) ainsi que les icones meteo amCharts pre-
converties (voir weather.py, firmware/weather_card.yaml) - isole du
dashboard principal (dashboard.py, 127.0.0.1 uniquement) pour ne pas
exposer le reste de la configuration (raccourcis clavier, jeton Home
Assistant...) sur le reseau local. Ce serveur ne fait que lire des
fichiers deja resolus/bundles, rien de sensible.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from flask import Flask, Response

from . import icon_extract
from . import profiles as profile_utils
from .device_client import ICON_SERVER_PORT, DeviceClient
from .weather import WEATHER_ICON_KEYS

LOG = logging.getLogger("streamdeck_icon_server")

# PNG 1x1 transparent, servi quand aucune icone reelle n'est disponible
# (emplacement non-'launch', extraction echouee...) - laisse le firmware
# afficher un pixel invisible plutot qu'une erreur reseau.
_BLANK_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15"
    "c4890000000a4944415478da6360000000020001e221bc330000000049454e"
    "44ae426082"
)

# Icones meteo pre-converties (SVG amCharts -> PNG aplati sur le fond de
# la carte, voir docs/ARCHITECTURE.md) - fichiers bundles dans le repo,
# pas de conversion a la volee (evite une dependance cairosvg cote
# utilisateur final). WEATHER_ICON_KEYS (weather.py) est la liste blanche
# des cles valides - pas de lecture de fichier arbitraire depuis l'URL.
_WEATHER_ICONS_DIR = Path(__file__).resolve().parent / "static" / "weather_icons"


def create_app(device_client: DeviceClient) -> Flask:
    app = Flask(__name__)

    @app.get("/slot-icon/<int:n>.png")
    def slot_icon(n: int):
        png = None
        try:
            if 1 <= n <= profile_utils.SLOT_COUNT:
                slot = profile_utils.resolve_slot(device_client.active_profile(), n - 1)
                action = slot.get("action") or {}
                if slot.get("type") == "bouton" and action.get("type") == "launch":
                    png = icon_extract.extract_icon_png(action.get("target") or "")
        except Exception:
            LOG.exception("Echec de generation de l'icone pour le slot %d", n)
        return Response(png or _BLANK_PNG, mimetype="image/png")

    @app.get("/weather-icon/<key>.png")
    def weather_icon(key: str):
        png = None
        if key in WEATHER_ICON_KEYS:
            try:
                png = (_WEATHER_ICONS_DIR / f"{key}.png").read_bytes()
            except OSError:
                LOG.exception("Icone meteo introuvable sur disque : %s", key)
        return Response(png or _BLANK_PNG, mimetype="image/png")

    return app


def run_forever(device_client: DeviceClient, port: int = ICON_SERVER_PORT) -> None:
    create_app(device_client).run(host="0.0.0.0", port=port, debug=False, threaded=True)


def start_in_thread(device_client: DeviceClient, port: int = ICON_SERVER_PORT) -> threading.Thread:
    thread = threading.Thread(target=run_forever, args=(device_client, port), daemon=True)
    thread.start()
    return thread
