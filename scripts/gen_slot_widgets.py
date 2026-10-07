#!/usr/bin/env python3
"""Regenere firmware/slot_widgets.yaml (36 emplacements LVGL, mecaniquement
identiques a part leur index, PLUS le bouton de la carte meteo en 37e
element) - a relancer si la structure d'un emplacement change (nouveau
sous-widget, etc.), pas pour changer la position/taille par defaut d'un
emplacement precis (ca, c'est firmware/slot_grid.yaml, pousse par l'appli
PC a la connexion).

Le bouton de la carte meteo (weather_card_btn) est ajoute ICI plutot que
dans weather_card.yaml : il doit etre un ENFANT de package.yaml::action_grid
(meme espace de coordonnees que les 36 emplacements, voir gen_weather_card.py
pour le detail) - `!include` ne remplace qu'une seule cle, donc les deux
!include (celui-ci pour la liste de widgets, `packages:` pour le reste de
la logique meteo) doivent rester coherents.

Usage: python3 scripts/gen_slot_widgets.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_weather_card import weather_button_widget  # noqa: E402

CELL = 96
GAP = 12
PITCH = 108
COLS = 9
SLOT_COUNT = 36

OUTPUT = Path(__file__).resolve().parent.parent / "firmware" / "slot_widgets.yaml"

HEADER = """# Widgets LVGL des 36 emplacements + la carte meteo (style YAML flow pour
# rester compact/sous 500 lignes). Genere par scripts/gen_slot_widgets.py,
# ne pas editer a la main - voir docs/ARCHITECTURE.md pour le systeme de
# grille redimensionnable. Position/taille par defaut (colonne i%9,
# ligne i//9, 1x1 case pour un emplacement) - la vraie disposition est
# poussee par le PC (voir firmware/slot_grid.yaml/weather_card.yaml,
# 'Slot N - grille'/'Meteo - grille') des la connexion, ces valeurs ne sont
# qu'un repli avant le premier push."""


def slot_line(i: int) -> str:
    idx = i - 1
    col = idx % COLS
    row = idx // COLS
    x, y = col * PITCH, row * PITCH
    w = h = CELL
    hidden = "false" if idx < 12 else "true"
    title_w = w - 16
    bar_w = w - 16
    zone_w = w // 2
    return (
        f'- button: {{id: slot{i}_btn, x: {x}, y: {y}, align: top_left, width: {w}, height: {h}, '
        f'bg_color: 0x0F2942, border_color: 0x1A3A52, border_width: 1, radius: 12, hidden: {hidden}, '
        f'on_click: [{{event.trigger: {{id: action_button_event, event_type: "action_{i}"}}}}], '
        f'on_long_press: [{{event.trigger: {{id: action_button_event, event_type: "hold_{i}"}}}}], '
        f'widgets: ['
        f'{{image: {{id: slot{i}_icon_widget, src: slot{i}_icon_img, width: 40, height: 40, align: top_mid, y: 0, radius: 8, clip_corner: true, hidden: true}}}}, '
        f'{{label: {{id: slot{i}_icon_lbl, text: "", text_font: font_icons, text_color: 0x00B4D8, align: top_mid, y: 4}}}}, '
        f'{{label: {{id: slot{i}_title, text: "Slot {i}", text_font: font_body, text_color: 0xFFFFFF, text_align: center, align: top_mid, y: 42, long_mode: dot, width: {title_w}}}}}, '
        f'{{label: {{id: slot{i}_value_lbl, text: "", text_font: font_mono, text_color: 0x8FAFC7, align: bottom_mid, y: -6, hidden: true}}}}, '
        f'{{bar: {{id: slot{i}_bar, width: {bar_w}, height: 8, align: bottom_mid, y: -8, min_value: 0, max_value: 100, value: 0, hidden: true}}}}, '
        f'{{button: {{id: slot{i}_barre_dec, width: {zone_w}, height: {h - 6}, align: left_mid, bg_opa: 0, border_width: 0, shadow_width: 0, hidden: true, on_click: [{{event.trigger: {{id: action_button_event, event_type: "barre_dec_{i}"}}}}]}}}}, '
        f'{{button: {{id: slot{i}_barre_inc, width: {zone_w}, height: {h - 6}, align: right_mid, bg_opa: 0, border_width: 0, shadow_width: 0, hidden: true, on_click: [{{event.trigger: {{id: action_button_event, event_type: "barre_inc_{i}"}}}}]}}}}'
        f']}}'
    )


def main() -> None:
    lines = [HEADER] + [slot_line(i) for i in range(1, SLOT_COUNT + 1)] + [weather_button_widget()]
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
