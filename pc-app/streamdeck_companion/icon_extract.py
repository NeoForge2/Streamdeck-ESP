"""Extraction des vraies icones d'appli/jeu (fichier .exe/.lnk) pour les
afficher sur l'ecran physique (voir firmware/slot_icons.yaml - l'entite
"Slot N - icone" declenche online_image.set_url avec l'URL de
dashboard.py::slot_icon()). Windows uniquement : icoextract lit la
ressource icone d'un executable, Pillow la redimensionne et l'aplatit sur
le fond du bouton (evite d'avoir a decoder un canal alpha PNG sur l'ESP),
winshell/pywin32 resolvent un raccourci .lnk (cible reelle + IconLocation
eventuelle, comme le fait l'Explorateur Windows).
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

from .actions import SYSTEM

ICON_SIZE = 40
# Couleur de fond des boutons (voir firmware/package.yaml, slot*_btn
# bg_color) - l'icone est aplatie dessus plutot que d'envoyer un PNG avec
# alpha, pour ne pas avoir a gerer la transparence cote firmware.
BUTTON_BG = (0x0F, 0x29, 0x42)

_cache: dict[str, tuple[str, bytes]] = {}  # chemin resolu -> (version, PNG)


def _first_token(target: str) -> str:
    """Chemin executable d'une cible d'action 'launch' (peut contenir des
    guillemets et des arguments, voir actions.py::run)."""
    target = target.strip()
    if target.startswith('"'):
        end = target.find('"', 1)
        return target[1:end] if end != -1 else target[1:]
    return target.split(" ", 1)[0]


def resolve_icon_target(target: str) -> str | None:
    """Chemin .exe/.lnk a utiliser pour extraire une icone - None si le
    type de cible n'est pas supporte (commande sans executable clair...)."""
    if not target:
        return None
    path = _first_token(target)
    if not path.lower().endswith((".exe", ".lnk")):
        return None
    return path


def icon_version(target: str) -> str | None:
    """Jeton court a pousser dans 'Slot N - icone' (voir device_client.py)
    pour forcer l'ecran a re-telecharger l'image quand la cible change."""
    path = resolve_icon_target(target)
    if not path:
        return None
    return hashlib.sha1(path.encode("utf-8")).hexdigest()[:8]


def _resolve_lnk(path: Path) -> tuple[str, str]:
    """Cible reelle + IconLocation ('chemin,index') eventuelle d'un .lnk."""
    import pythoncom
    from win32com.client import Dispatch

    pythoncom.CoInitialize()
    try:
        shortcut = Dispatch("WScript.Shell").CreateShortCut(str(path))
        return shortcut.Targetpath or str(path), shortcut.IconLocation or ""
    finally:
        pythoncom.CoUninitialize()


def _extract_ico(exe_path: str, index: int):
    from icoextract import IconExtractor, IconExtractorError

    try:
        return IconExtractor(exe_path).get_icon(num=index)
    except (IconExtractorError, FileNotFoundError, OSError):
        return None


def extract_icon_png(target: str) -> bytes | None:
    """PNG (32x32, fond aplati sur BUTTON_BG) de l'icone reelle de
    `target`, ou None si non disponible/non Windows. Mise en cache en
    memoire par cible resolue, invalidee automatiquement si la cible
    change (voir icon_version, meme cle de hash)."""
    if SYSTEM != "Windows":
        return None
    path = resolve_icon_target(target)
    if not path or not Path(path).exists():
        return None

    version = icon_version(target)
    cached = _cache.get(path)
    if cached and cached[0] == version:
        return cached[1]

    exe_path, icon_index = path, 0
    if path.lower().endswith(".lnk"):
        real_target, icon_location = _resolve_lnk(Path(path))
        loc_path, _, loc_index = icon_location.rpartition(",")
        if loc_path and Path(loc_path).exists():
            exe_path, icon_index = loc_path, int(loc_index or 0)
        elif real_target:
            exe_path = real_target

    ico_buf = _extract_ico(exe_path, icon_index)
    if ico_buf is None and icon_index != 0:
        ico_buf = _extract_ico(exe_path, 0)
    if ico_buf is None:
        return None

    from PIL import Image

    try:
        icon = Image.open(ico_buf)
        # Un .ico embarque generalement plusieurs resolutions (16/32/48/256...)
        # - Pillow charge par defaut la PREMIERE du fichier, pas la plus
        # grande (l'ordre depend de l'outil qui a construit l'executable,
        # souvent du plus petit au plus grand) : sans ca on recupere souvent
        # une icone 16x16 remontee en 40x40, floue et avec moins de couleurs.
        sizes = icon.info.get("sizes") or [icon.size]
        best = max(sizes, key=lambda s: s[0] * s[1])
        if best != icon.size:
            icon.size = best
        icon.load()
    except Exception:
        return None

    background = Image.new("RGB", icon.size, BUTTON_BG)
    if icon.mode in ("RGBA", "LA") or (icon.mode == "P" and "transparency" in icon.info):
        icon = icon.convert("RGBA")
        background.paste(icon, mask=icon.split()[-1])
    else:
        background.paste(icon.convert("RGB"))
    background = background.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)

    buf = io.BytesIO()
    background.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    _cache[path] = (version, png_bytes)
    return png_bytes
