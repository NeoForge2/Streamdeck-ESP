"""Lance l'appli compagnon Stream Deck comme une icone de barre des taches
Windows (system tray), sans fenetre de terminal visible : c'est la facon
recommandee de faire tourner ce programme au quotidien.

Trois choses tournent en fond :
  - device_client.DeviceClient : connexion persistante a l'ecran (thread
    dedie avec sa propre boucle asyncio), execute les actions configurees.
  - dashboard.py : page web de configuration (autre thread), lit/ecrit
    dashboard_config.yaml et demande a DeviceClient de pousser les
    changements vers l'ecran.
  - profile_watcher.py : surveille l'application au premier plan et bascule
    automatiquement le profil actif (voir profiles.py).
  - icon_server.py : petit serveur HTTP separe (0.0.0.0) qui sert les
    vraies icones d'appli/jeu a l'ecran, isole du dashboard (127.0.0.1).

Lancer :
    pythonw -m streamdeck_companion.tray      (pythonw = pas de console)

Pour un demarrage automatique avec Windows, voir install_startup.ps1 et le
README de ce dossier.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from . import dashboard
from . import encoder_sync
from . import ha_mqtt
from . import ha_poller
from . import icon_server
from . import profile_watcher
from . import profiles as profile_utils
from .dashboard_v2_routes import register_dashboard_v2_routes
from .device_client import DEFAULT_CONFIG_PATH, DeviceClient, load_config, save_config
from .v2_device_client import V2DeviceClient

LOG = logging.getLogger("streamdeck_tray")

# Couleurs du design system (navy / signal)
NAVY = (11, 25, 41, 255)
SIGNAL = (0, 180, 216, 255)

# Port arbitraire, jamais ecoute - sert uniquement de verrou local (voir
# _acquire_single_instance_lock) pour empecher deux instances de tourner en
# meme temps : chacune ouvrirait sa propre connexion a l'ecran, qui recevrait
# alors chaque appui en double/triple (chaque instance execute l'action
# independamment - vecu en pratique lors de sessions de debug avec plusieurs
# terminaux ouverts en parallele).
SINGLE_INSTANCE_PORT = 47823


def _acquire_single_instance_lock() -> socket.socket:
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock_socket.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
    except OSError:
        lock_socket.close()
        raise RuntimeError(
            "Une autre instance de l'appli Stream Deck tourne deja - "
            "ferme-la (icone barre des taches, ou Gestionnaire des taches) avant de relancer."
        ) from None
    return lock_socket


def _show_error_dialog(message: str) -> None:
    """Boite de dialogue de secours - lance via pythonw, aucune console
    n'est visible pour lire le message d'erreur du logger."""
    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("Stream Deck", message)
        root.destroy()
    except Exception:
        pass


def make_icon_image() -> Image.Image:
    """Genere l'icone directement en memoire (pas de fichier .ico a fournir) :
    un cercle signal sur fond navy, aux couleurs du design system."""
    size = 64
    img = Image.new("RGBA", (size, size), NAVY)
    draw = ImageDraw.Draw(img)
    margin = 14
    draw.ellipse((margin, margin, size - margin, size - margin), fill=SIGNAL)
    return img


def build_menu(config: dict, device_client: DeviceClient) -> pystray.Menu:
    ha_conf = config.get("home_assistant") or {}
    ha_url = ha_conf.get("url") or "http://homeassistant.local:8123"

    def open_dashboard(_icon, _item):
        webbrowser.open(f"http://127.0.0.1:{dashboard.DASHBOARD_PORT}")

    def open_home_assistant(_icon, _item):
        webbrowser.open(ha_url)

    def active_profile_label(_item):
        name = device_client.active_profile_name or "Defaut"
        suffix = " (fige)" if device_client.manual_override else " (auto)"
        return f"Profil actif : {name}{suffix}"

    def resume_auto(_icon, _item):
        device_client.schedule_clear_override()

    def quit_app(icon, _item):
        icon.stop()
        os._exit(0)  # noqa: SLF001 - threads daemon, on arrete tout le process direct

    return pystray.Menu(
        pystray.MenuItem("Stream Deck", None, enabled=False),
        pystray.MenuItem(active_profile_label, None, enabled=False),
        pystray.MenuItem(
            "Reprendre la bascule automatique", resume_auto,
            visible=lambda _item: bool(device_client.manual_override),
        ),
        pystray.MenuItem("Configurer le Stream Deck", open_dashboard, default=True),
        pystray.MenuItem("Ouvrir Home Assistant", open_home_assistant),
        pystray.MenuItem("Quitter", quit_app),
    )


def run_device_client(client: DeviceClient) -> None:
    """Cible du thread de connexion : sa propre boucle asyncio, tourne en
    continu (reconnecte si l'ecran redemarre ou change d'IP apres correction
    dans la page de config, puisque asyncio.run() relance run_forever a
    chaque erreur non geree via la boucle exterieure ci-dessous)."""
    while True:
        try:
            asyncio.run(client.run_forever())
        except Exception:
            LOG.exception("Connexion au Stream Deck perdue, nouvelle tentative dans 10s")
        client.connected = False
        client.loop = None
        time.sleep(10)


def ensure_config_exists(config_path: Path) -> None:
    """Cree un fichier de config vide (connexion non renseignee) au tout
    premier lancement, plutot que de demander a l'utilisateur de copier un
    fichier .example a la main - la page 'Reglages' (voir dashboard.py) se
    charge de demander les infos manquantes des l'ouverture de l'appli."""
    if config_path.exists():
        return
    config_path.parent.mkdir(parents=True, exist_ok=True)
    save_config(config_path, {
        "connection": {"host": "", "port": 6053, "api_key": ""},
        "shape": "carre",
        "home_assistant": {"url": "", "token": ""},
        "mqtt": {"host": "", "port": ha_mqtt.DEFAULT_PORT, "username": "", "password": "", "base_topic": ha_mqtt.DEFAULT_BASE_TOPIC},
        "profiles": [profile_utils.default_profile()],
    })
    LOG.info("Fichier de config cree: %s", config_path)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        _lock_socket = _acquire_single_instance_lock()  # noqa: F841 - garde une reference, voir la fonction
    except RuntimeError as exc:
        LOG.error(str(exc))
        _show_error_dialog(str(exc))  # pythonw n'a pas de console visible
        sys.exit(1)
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG_PATH
    ensure_config_exists(config_path)
    config = load_config(config_path)

    device_client = V2DeviceClient(config_path)
    client_thread = threading.Thread(target=run_device_client, args=(device_client,), daemon=True)
    client_thread.start()

    register_dashboard_v2_routes(dashboard.app)
    dashboard_thread = threading.Thread(
        target=dashboard.run_server, args=(config_path, device_client), daemon=True
    )
    dashboard_thread.start()

    icon_server.start_in_thread(device_client)

    # ha_mqtt complete ha_poller (filet de securite REST, toujours actif)
    # par des mises a jour instantanees si un broker MQTT est renseigne
    # dans Reglages - voir ha_mqtt.py pour le detail du fonctionnement.
    ha_mqtt.start_in_thread(device_client, config.get("mqtt") or {})

    ha_stop_event = threading.Event()
    ha_thread = threading.Thread(
        target=ha_poller.run_forever, args=(device_client, ha_stop_event), daemon=True
    )
    ha_thread.start()

    profile_stop_event = threading.Event()
    profile_thread = threading.Thread(
        target=profile_watcher.run_forever, args=(device_client, profile_stop_event), daemon=True
    )
    profile_thread.start()

    encoder_stop_event = threading.Event()
    encoder_thread = threading.Thread(
        target=encoder_sync.run_forever, args=(device_client, encoder_stop_event), daemon=True
    )
    encoder_thread.start()

    icon = pystray.Icon("streamdeck", make_icon_image(), "Stream Deck", menu=build_menu(config, device_client))
    icon.run()


if __name__ == "__main__":
    main()
