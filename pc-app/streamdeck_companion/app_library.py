"""Bibliotheque d'applications installees, pour choisir une appli a lancer
dans une liste plutot que de taper/chercher un chemin a la main (voir le
menu "Applications installees" de la popup d'emplacement, type d'action
'launch'). Windows uniquement : parcourt les raccourcis du menu Demarrer
(commun a tous les utilisateurs + ceux de l'utilisateur courant) via
winshell/pywin32 - la meme technique que Windows lui-meme utilise pour
afficher son propre menu Demarrer.

Le bouton enregistre le CHEMIN DU RACCOURCI (.lnk) lui-meme, pas sa cible
resolue (Targetpath) - une appli qui se met a jour toute seule (Discord,
Claude Desktop...) change souvent de dossier versionne, ce qui rend un
chemin .exe fige invalide au prochain lancement/extraction d'icone (voir
icon_extract.py) sans que l'utilisateur ne comprenne pourquoi. Le
raccourci, lui, reste au meme endroit et est mis a jour EN PLACE par
l'installeur/le mecanisme d'auto-update - _launch() (actions.py, via le
shell) et extract_icon_png() (icon_extract.py, deja capable de resoudre un
.lnk) suivent donc automatiquement la cible actuelle sans jamais avoir a
recreer le bouton.
"""

from __future__ import annotations

from pathlib import Path

from .actions import SYSTEM

# Raccourcis a exclure (desinstalleurs, aide, liens web...) - ils polluent
# la liste sans jamais etre une appli qu'on veut lancer depuis un bouton.
_EXCLUDE_NAME_HINTS = ("uninstall", "desinstall", "readme", "changelog", "help", "licence", "license")


def list_installed_apps() -> list[dict[str, str]]:
    """Retourne [{name, target}], trie par nom, deduplique par cible reelle
    (evite les doublons quand plusieurs raccourcis pointent vers la meme
    appli) - `target` est le chemin du RACCOURCI (.lnk), pas la cible
    resolue (voir docstring du module)."""
    if SYSTEM != "Windows":
        raise RuntimeError("La bibliotheque d'applications n'est disponible que sur Windows")

    import pythoncom
    import winshell
    from win32com.client import Dispatch

    seen_targets: set[str] = set()
    apps: list[dict[str, str]] = []

    # Dispatch() cree un objet COM, qui exige que l'appartement COM du
    # thread courant ait ete initialise - ce qui n'est pas garanti sur les
    # threads du pool de Flask (threaded=True), d'ou CoInitialize/
    # CoUninitialize explicites autour de son utilisation.
    pythoncom.CoInitialize()
    try:
        shell = Dispatch("WScript.Shell")

        # "Programs" = raccourcis d'applications (le sous-dossier utile) ; le
        # dossier utilisateur (common=0) ET le dossier commun a tous les
        # utilisateurs (common=1) pour couvrir les applis installees pour soi
        # seul ou pour toute la machine.
        for folder in (winshell.programs(), winshell.programs(common=1)):
            for lnk_path in Path(folder).rglob("*.lnk"):
                name = lnk_path.stem
                if any(hint in name.lower() for hint in _EXCLUDE_NAME_HINTS):
                    continue
                try:
                    target = shell.CreateShortCut(str(lnk_path)).Targetpath
                except Exception:
                    continue
                if not target or target in seen_targets:
                    continue
                seen_targets.add(target)
                lnk_str = str(lnk_path)
                apps.append({"name": name, "target": f'"{lnk_str}"' if " " in lnk_str else lnk_str})
    finally:
        pythoncom.CoUninitialize()

    apps.sort(key=lambda a: a["name"].lower())
    return apps
