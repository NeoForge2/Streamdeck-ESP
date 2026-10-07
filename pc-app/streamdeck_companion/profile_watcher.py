"""Surveille l'application au premier plan sur le PC et bascule
automatiquement l'ecran sur le profil dont le declencheur correspond (voir
profiles.py) - le comportement "profils par application" d'un Stream Deck
du commerce : la grille change toute seule selon l'appli active, sans
intervention. Tourne dans son propre thread (voir tray.py), a l'image de
ha_poller.py.

Windows uniquement (necessite pywin32 + psutil pour identifier la fenetre
au premier plan) - no-op silencieux sur les autres systemes, la bascule
manuelle (bouton "Forcer ce profil") reste utilisable partout.
"""

from __future__ import annotations

import logging
import threading

from . import profiles as profile_utils
from .actions import SYSTEM
from .device_client import DeviceClient

LOG = logging.getLogger("streamdeck_profile_watcher")

POLL_INTERVAL = 1.5


def foreground_process_name() -> str | None:
    """Nom (minuscules, ex 'obs64.exe') du processus de la fenetre au
    premier plan sur le PC, ou None si indisponible/non-Windows."""
    if SYSTEM != "Windows":
        return None
    import psutil
    import win32gui
    import win32process

    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return None
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    if not pid:
        return None
    try:
        return psutil.Process(pid).name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def list_open_windows() -> list[dict[str, str]]:
    """Liste [{title, process, target}] des applications actuellement
    ouvertes sur le PC (une entree par processus, dedupliquee) - `target`
    est le chemin complet de l'executable (via psutil), utilisable comme
    cible d'action 'launch' pour un emplacement, exactement comme `process`
    sert de declencheur de profil. Meme source pour les deux usages plutot
    que de "detecter" la fenetre active (piege : cliquer un bouton dans le
    navigateur remet toujours le navigateur au premier plan avant que la
    detection s'execute). Windows uniquement."""
    if SYSTEM != "Windows":
        return []
    import psutil
    import win32gui
    import win32process

    seen: set[str] = set()
    windows: list[dict[str, str]] = []

    def _on_window(hwnd: int, _extra) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if not pid:
            return
        try:
            proc = psutil.Process(pid)
            process = proc.name()
            exe_path = proc.exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return
        key = process.lower()
        if key in seen or key == "streamdeck_companion.exe":
            return
        seen.add(key)
        target = f'"{exe_path}"' if exe_path and " " in exe_path else (exe_path or process)
        windows.append({"title": title, "process": process, "target": target})

    win32gui.EnumWindows(_on_window, None)
    windows.sort(key=lambda w: w["title"].lower())
    return windows


def run_forever(device_client: DeviceClient, stop_event: threading.Event) -> None:
    if SYSTEM != "Windows":
        LOG.info("Bascule automatique de profil indisponible sur cette plateforme (Windows uniquement)")
        return
    while not stop_event.is_set():
        try:
            if device_client.manual_override is None:
                process_name = foreground_process_name()
                matched = profile_utils.match_profile(device_client.profiles, process_name)
                device_client.schedule_set_active_profile(matched.get("name"))
        except Exception:
            LOG.exception("Echec de la verification du profil actif")
        stop_event.wait(POLL_INTERVAL)
