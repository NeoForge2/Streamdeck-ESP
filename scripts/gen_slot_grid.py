#!/usr/bin/env python3
"""Regenere firmware/slot_grid_1.yaml + slot_grid_2.yaml (une entite texte
'Slot N - grille' par emplacement + le lambda qui la traduit en
position/taille LVGL) - a relancer si la formule de conversion case->pixel
change (taille de case, espacement, nombre de colonnes...), voir
CELL/GAP/PITCH/COLS ci-dessous et package.yaml::action_grid (doit rester
coherent avec ces constantes). Deux fichiers (au lieu d'un seul) pour
rester sous 500 lignes chacun avec 36 emplacements (~24 lignes/emplacement).

Usage: python3 scripts/gen_slot_grid.py
"""

from __future__ import annotations

from pathlib import Path

CELL = 96
GAP = 12
PITCH = 108
COLS = 9
SLOT_COUNT = 36
# Repli sous 500 lignes/fichier (~24 lignes/emplacement, voir module docstring).
SPLIT_AT = 18

FIRMWARE_DIR = Path(__file__).resolve().parent.parent / "firmware"

HEADER = """# Position/taille des emplacements {lo} a {hi} sur la grille invisible de
# cases carrees (9 colonnes x 4 lignes, cases de 96px, 12px d'espacement -
# voir package.yaml::action_grid) - facon "sections" de Home Assistant :
# chaque emplacement peut occuper 1 ou plusieurs cases, redimensionne/
# repositionne en direct depuis l'appli PC (glisser-depose/redimensionner,
# voir dashboard.js), sans reflasher.
#
# Une seule entite texte par emplacement (au lieu de 4 nombres separes) -
# format compact "colonne,ligne,largeur_cases,hauteur_cases", ex "2,1,3,2"
# = demarre a la colonne 2/ligne 1, large de 3 cases, haut de 2 cases.
# Le lambda calcule les pixels et repositionne/redimensionne le bouton ET
# ses sous-widgets (titre/barre/zones tactiles gauche-droite) en
# proportion - on_clockwise/on_click etc. (slot_widgets.yaml) restent
# inchanges, seule la geometrie bouge ici.
#
# Genere par scripts/gen_slot_grid.py, ne pas editer a la main.
text:"""


def slot_block(i: int) -> str:
    idx = i - 1
    col, row = idx % COLS, idx // COLS
    initial = f"{col},{row},1,1"
    code_lines = [
        "int col=0,row=0,cs=1,rs=1;",
        'sscanf(x.c_str(), "%d,%d,%d,%d", &col, &row, &cs, &rs);',
        f"const int cell={CELL}, gap={GAP}, pitch={PITCH};",
        "int px = col*pitch, py = row*pitch;",
        "int pw = cs*cell + (cs-1)*gap;",
        "int ph = rs*cell + (rs-1)*gap;",
        f"lv_obj_set_pos(id(slot{i}_btn), px, py);",
        f"lv_obj_set_size(id(slot{i}_btn), pw, ph);",
        f"lv_obj_set_width(id(slot{i}_title), pw > 16 ? pw - 16 : pw);",
        f"lv_obj_set_width(id(slot{i}_bar), pw > 16 ? pw - 16 : pw);",
        f"lv_obj_set_width(id(slot{i}_barre_dec), pw / 2);",
        f"lv_obj_set_width(id(slot{i}_barre_inc), pw / 2);",
        f"lv_obj_set_height(id(slot{i}_barre_dec), ph > 6 ? ph - 6 : ph);",
        f"lv_obj_set_height(id(slot{i}_barre_inc), ph > 6 ? ph - 6 : ph);",
    ]
    code = "\n".join(" " * 10 + line for line in code_lines)
    return (
        f'  - platform: template\n'
        f'    id: slot{i}_grid_text\n'
        f'    name: "Slot {i} - grille"\n'
        f'    mode: text\n'
        f'    optimistic: true\n'
        f'    initial_value: "{initial}"\n'
        f'    max_length: 16\n'
        f'    on_value:\n'
        f'      - lambda: |-\n'
        f'{code}'
    )


def write_chunk(lo: int, hi: int, filename: str) -> None:
    blocks = [HEADER.format(lo=lo, hi=hi)] + [slot_block(i) for i in range(lo, hi + 1)]
    out = FIRMWARE_DIR / filename
    out.write_text("\n".join(blocks) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({sum(b.count(chr(10)) + 1 for b in blocks)} lines)")


def main() -> None:
    write_chunk(1, SPLIT_AT, "slot_grid_1.yaml")
    write_chunk(SPLIT_AT + 1, SLOT_COUNT, "slot_grid_2.yaml")


if __name__ == "__main__":
    main()
