"""Modele des profils : chaque profil a sa propre grille de 36
emplacements physiques (la grille invisible 9x4, voir GRID_COLS/GRID_ROWS
- seuls ceux avec un `library_id` assigne s'affichent) + 3 encodeurs, et
un declencheur optionnel (nom de
processus). L'ecran bascule automatiquement sur le profil dont le
declencheur correspond a l'application au premier plan sur le PC (voir
profile_watcher.py) - le comportement "profils par application" d'un
Stream Deck du commerce. Le premier profil sans declencheur ("Defaut")
sert de repli quand aucun declencheur ne correspond.

Module partage par dashboard.py (edition web) et device_client.py
(resolution des actions + push vers l'ecran) - independant des deux pour
eviter tout import circulaire.
"""

from __future__ import annotations

SLOT_COUNT = 36
DEFAULT_PROFILE_NAME = "Defaut"

# Nombre d'emplacements de l'ancien format "tout-en-un" (avant la
# bibliotheque illimitee) - fige a 16, NE DOIT PAS suivre SLOT_COUNT :
# sert uniquement a migrate_profile_library() pour ne convertir que les
# emplacements qui existaient reellement dans les anciens profils, sans
# creer des entrees de bibliotheque vides pour les emplacements physiques
# ajoutes depuis (17-36, voir ensure_slot_count).
_LEGACY_SLOT_COUNT = 16

# Grille invisible de cases carrees (voir firmware/slot_grid.yaml et
# scripts/gen_slot_grid.py - CES 3 endroits doivent rester coherents si la
# geometrie change un jour) : un emplacement occupe 1 ou plusieurs cases
# ("colspan"/"rowspan"), facon "sections" de Home Assistant, au lieu d'une
# grille fixe 4x4 a une seule taille de tuile.
GRID_COLS = 9
GRID_ROWS = 4


def default_grid(i: int) -> dict:
    """Disposition par defaut (avant toute personnalisation au glisser-
    depose/redimensionnement) : range dans l'ordre de lecture, 1x1 case."""
    return {"col": i % GRID_COLS, "row": i // GRID_COLS, "colspan": 1, "rowspan": 1}


def default_slot(i: int) -> dict:
    """Emplacement PHYSIQUE i (0 a SLOT_COUNT-1) - juste sa position/taille et QUELLE
    entree de bibliotheque (voir default_library_entry) y est affichee, si
    aucune (`library_id: None`) l'emplacement est simplement vide/invisible.
    Le contenu (libelle/icone/action...) ne vit plus ici depuis l'ajout de
    la bibliotheque illimitee - voir resolve_slot()."""
    return {"library_id": None, "grid": default_grid(i)}


def default_slots() -> list[dict]:
    return [default_slot(i) for i in range(SLOT_COUNT)]


def default_library_entry(entry_id: str) -> dict:
    """Entree de bibliotheque vide (voir bouton "+" de l'appli PC) - le
    nombre d'entrees n'est PAS limite contrairement aux emplacements
    physiques : on peut en enregistrer autant que voulu, seuls SLOT_COUNT
    (36, un par case de la grille invisible) au maximum peuvent etre
    assignes a un emplacement visible a la fois (limite materielle du
    firmware, voir slot_widgets.yaml)."""
    return {
        "id": entry_id,
        "label": "Nouveau bouton",
        "icon": "",
        "icon_char": "",
        "type": "bouton",
        "action": {"type": "none", "target": ""},
        "ha_entity": "",
        "show_light_color": False,
    }


def find_library_entry(library: list[dict] | None, entry_id: str | None) -> dict | None:
    if not entry_id:
        return None
    return next((e for e in (library or []) if e.get("id") == entry_id), None)


def resolve_slot(profile: dict, idx: int) -> dict:
    """Emplacement physique idx (0 a SLOT_COUNT-1) RESOLU : combine sa position/taille
    de grille avec le contenu (libelle/icone/action/...) de l'entree de
    bibliotheque qui lui est assignee, dans le MEME format qu'un ancien
    emplacement "tout-en-un" - pour que push_config()/_resolve_action()/
    ha_poller.py n'aient pas besoin de connaitre la bibliotheque. Renvoie
    un emplacement vide/invisible si rien n'y est assigne."""
    slots = profile.get("slots") or []
    phys = slots[idx] if idx < len(slots) else {}
    grid = phys.get("grid") or default_grid(idx)
    entry = find_library_entry(profile.get("library"), phys.get("library_id"))
    if entry is None:
        return {
            "label": f"Slot {idx + 1}", "icon": "", "icon_char": "", "type": "bouton", "visible": False,
            "action": {"type": "none", "target": ""}, "ha_entity": "", "show_light_color": False,
            "grid": grid, "library_id": None,
        }
    return {**entry, "visible": True, "grid": grid, "library_id": phys.get("library_id")}


def migrate_profile_library(profile: dict) -> None:
    """Migre un profil de l'ancien format (_LEGACY_SLOT_COUNT emplacements
    "tout-en-un" - libelle/icone/action directement dans slots[i]) vers le
    modele bibliotheque+assignation (voir resolve_slot) - modifie `profile`
    sur place, ne fait rien si une cle "library" existe deja. Preserve
    integralement le contenu et l'etat visible/masque existants : chaque
    ancien emplacement devient une entree de bibliotheque, assignee au
    meme emplacement physique s'il etait visible. Ne cree PAS d'entrees
    pour les emplacements physiques 17-36 (voir ensure_slot_count) - ils
    n'existaient pas dans l'ancien format, ca ne ferait qu'ajouter des
    "Nouveau bouton" vides et jamais assignes dans la bibliotheque."""
    if "library" in profile:
        return
    old_slots = profile.get("slots") or []
    library, new_slots = [], []
    for i in range(_LEGACY_SLOT_COUNT):
        old = old_slots[i] if i < len(old_slots) else {}
        entry_id = f"lib-{i}"
        library.append({
            "id": entry_id,
            "label": old.get("label") or f"Slot {i + 1}",
            "icon": old.get("icon", ""),
            "icon_char": old.get("icon_char", ""),
            "type": old.get("type", "bouton"),
            "action": old.get("action") or {"type": "none", "target": ""},
            "ha_entity": old.get("ha_entity", ""),
            "show_light_color": bool(old.get("show_light_color")),
        })
        new_slots.append({
            "library_id": entry_id if old.get("visible", i < 12) else None,
            "grid": old.get("grid") or default_grid(i),
        })
    profile["slots"] = new_slots
    profile["library"] = library


def ensure_slot_count(profile: dict) -> None:
    """Complete `profile["slots"]` a SLOT_COUNT emplacements physiques
    (position/taille + `library_id: None`) si besoin - independant de
    migrate_profile_library() pour que les profils DEJA migres (avant un
    passage de SLOT_COUNT 16->36) recuperent les emplacements physiques
    supplementaires sans repasser par la migration bibliotheque (qui ne
    s'execute qu'une fois, voir le garde "library" in profile ci-dessus)."""
    slots = profile.setdefault("slots", [])
    for i in range(len(slots), SLOT_COUNT):
        slots.append(default_slot(i))


def default_encoders() -> list[dict]:
    empty = {"type": "none", "target": ""}
    return [{"clockwise": dict(empty), "anticlockwise": dict(empty), "press": dict(empty)} for _ in range(3)]


def default_weather() -> dict:
    """Carte meteo : widget dedie (pas un des emplacements generiques),
    au plus une par profil - voir weather.py et firmware/weather_card.yaml.
    2x2 cases par defaut (assez pour icone + temperature + condition)."""
    return {"visible": False, "entity": "", "grid": {"col": 0, "row": 0, "colspan": 2, "rowspan": 2}}


def default_profile(name: str = DEFAULT_PROFILE_NAME, trigger: dict | None = None) -> dict:
    return {
        "name": name, "trigger": trigger, "slots": default_slots(), "encoders": default_encoders(),
        "weather": default_weather(), "library": [],
    }


def migrate_profiles(config: dict) -> list[dict]:
    """Retourne config['profiles'], migrant l'ancien format (slots/encoders
    a la racine, avant l'introduction des profils) vers un profil "Defaut"
    unique si besoin - transparent pour les configs existantes. Migre
    egalement chaque profil vers le modele bibliotheque+assignation si
    besoin (voir migrate_profile_library)."""
    profiles = config.get("profiles")
    if not profiles:
        profile = default_profile()
        if "slots" in config:
            profile["slots"] = config["slots"]
        if "encoders" in config:
            profile["encoders"] = config["encoders"]
        profiles = [profile]
    for profile in profiles:
        migrate_profile_library(profile)
        ensure_slot_count(profile)
    return profiles


def find_profile(profiles: list[dict], name: str | None) -> dict | None:
    if name is None:
        return None
    return next((p for p in profiles if p.get("name") == name), None)


def match_profile(profiles: list[dict], process_name: str | None) -> dict:
    """Le premier profil (dans l'ordre de la liste) dont le declencheur
    correspond au processus au premier plan sur le PC, sinon le premier
    profil sans declencheur ("Defaut"). `profiles` ne devrait jamais etre
    vide en pratique (migrate_profiles en garantit au moins un), mais on
    retombe sur un profil par defaut "en memoire" par securite."""
    if process_name:
        needle = process_name.lower()
        for profile in profiles:
            trigger = profile.get("trigger")
            if trigger and (trigger.get("process") or "").lower() == needle:
                return profile
    for profile in profiles:
        if not profile.get("trigger"):
            return profile
    return profiles[0] if profiles else default_profile()
