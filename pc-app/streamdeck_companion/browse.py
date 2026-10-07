"""Selecteur de fichier natif pour choisir une application a lancer, plutot
que de demander a l'utilisateur de taper un chemin a la main (voir le bouton
"Parcourir..." de la popup d'emplacement). L'appli tourne en local sur le
PC de l'utilisateur, donc ouvrir une boite de dialogue systeme depuis le
serveur Flask est possible et affiche bien sur l'ecran de l'utilisateur."""

from __future__ import annotations

from .actions import SYSTEM

if SYSTEM == "Windows":
    _FILETYPES = [("Applications et raccourcis", "*.exe;*.lnk;*.bat"), ("Tous les fichiers", "*.*")]
elif SYSTEM == "Darwin":
    _FILETYPES = [("Applications", "*.app"), ("Tous les fichiers", "*.*")]
else:
    _FILETYPES = [("Tous les fichiers", "*.*")]


def browse_for_executable() -> str | None:
    """Ouvre le selecteur de fichier natif du systeme et retourne le chemin
    choisi (ou None si annule). Bloque le thread appelant le temps que
    l'utilisateur choisisse - appelee depuis une route Flask dediee."""
    import tkinter
    from tkinter import filedialog

    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        path = filedialog.askopenfilename(title="Choisir une application", filetypes=_FILETYPES)
    finally:
        root.destroy()
    if not path:
        return None
    return f'"{path}"' if " " in path else path
