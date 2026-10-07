"""Volume par application et volume general Windows (pycaw), pour :
- l'action 'app_volume' des encodeurs (regler le volume d'une appli
  precise en tournant, voir actions.py) ;
- l'action 'app_mute' (bascule du son d'une appli precise, typiquement
  sur l'appui de l'encodeur en complement de 'app_volume' sur la rotation) ;
- l'affichage de la vraie valeur sur la barre d'un encodeur (voir
  encoder_sync.py), que ce soit le volume general (encodeur configure en
  'media' vol_up/vol_down) ou celui d'une appli (encodeur configure en
  'app_volume').

pycaw ne permet pas de nommer une session par son executable directement -
`AudioUtilities.GetAllSessions()` doit etre parcourue a chaque fois (les
sessions vont et viennent avec les fenetres/apps ouvertes), d'ou l'absence
de cache ici contrairement a audio_devices.py (peripheriques, eux, stables)."""

from __future__ import annotations

from .actions import SYSTEM


def _require_windows() -> None:
    if SYSTEM != "Windows":
        raise RuntimeError("Le volume par application n'est disponible que sur Windows")


def list_audio_sessions() -> list[dict]:
    """[{key, name}] pour chaque application ayant une session audio
    active - `key` est le nom du processus (ex 'chrome.exe'), stable d'un
    lancement a l'autre contrairement au PID, utilise pour cibler l'appli
    depuis la config (voir actions.py::_app_volume)."""
    _require_windows()
    import pythoncom
    from pycaw.utils import AudioUtilities

    pythoncom.CoInitialize()
    try:
        seen: dict[str, str] = {}
        for session in AudioUtilities.GetAllSessions():
            process = session.Process
            if process is None:
                continue
            key = process.name()
            seen.setdefault(key, session.DisplayName or key)
        return [{"key": k, "name": n} for k, n in sorted(seen.items(), key=lambda kv: kv[1].lower())]
    finally:
        pythoncom.CoUninitialize()


def _session_volume(app_key: str):
    from pycaw.utils import AudioUtilities

    for session in AudioUtilities.GetAllSessions():
        process = session.Process
        if process is not None and process.name() == app_key:
            return session.SimpleAudioVolume
    return None


def get_app_volume(app_key: str) -> float | None:
    """Volume actuel (0-100) de `app_key`, ou None si l'appli n'a pas
    (ou plus) de session audio active."""
    _require_windows()
    import pythoncom

    pythoncom.CoInitialize()
    try:
        volume = _session_volume(app_key)
        if volume is None:
            return None
        return round(volume.GetMasterVolume() * 100)
    finally:
        pythoncom.CoUninitialize()


def adjust_app_volume(app_key: str, direction: int, step: int = 5) -> None:
    """Augmente/diminue (direction +1/-1) le volume de `app_key` par pas
    de `step` % - ne fait rien si l'appli n'a pas de session active (ex:
    lancee mais pas encore de son joue)."""
    _require_windows()
    import pythoncom

    pythoncom.CoInitialize()
    try:
        volume = _session_volume(app_key)
        if volume is None:
            return
        current_pct = round(volume.GetMasterVolume() * 100)
        new_pct = max(0, min(100, current_pct + direction * step))
        volume.SetMasterVolume(new_pct / 100, None)
    finally:
        pythoncom.CoUninitialize()


def toggle_app_mute(app_key: str) -> None:
    """Bascule le mute de `app_key` - pense pour l'appui d'un encodeur
    configure en 'app_volume' (voir actions.py::_app_mute), en complement
    du reglage par rotation. Ne fait rien si l'appli n'a pas de session
    active."""
    _require_windows()
    import pythoncom

    pythoncom.CoInitialize()
    try:
        volume = _session_volume(app_key)
        if volume is None:
            return
        volume.SetMute(not volume.GetMute(), None)
    finally:
        pythoncom.CoUninitialize()


def get_system_volume() -> float | None:
    """Volume general Windows actuel (0-100) - complement en lecture de
    l'action 'media' vol_up/vol_down (qui pilote le volume via une touche
    media simulee, sans jamais renvoyer la valeur resultante)."""
    _require_windows()
    import pythoncom
    from pycaw.utils import AudioUtilities

    pythoncom.CoInitialize()
    try:
        speakers = AudioUtilities.GetSpeakers()
        if speakers is None:
            return None
        return round(speakers.EndpointVolume.GetMasterVolumeLevelScalar() * 100)
    finally:
        pythoncom.CoUninitialize()
