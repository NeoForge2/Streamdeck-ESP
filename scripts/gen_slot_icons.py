#!/usr/bin/env python3
"""Regenere firmware/slot_icons.yaml (une entite online_image par
emplacement physique, pour les vraies icones d'appli/jeu - voir
icon_extract.py cote PC, slots_*.yaml pour le fetch declenche par "Slot N -
icone") - a relancer si SLOT_COUNT change ou si la structure de l'entite
online_image change.

Usage: python3 scripts/gen_slot_icons.py
"""

from __future__ import annotations

from pathlib import Path

SLOT_COUNT = 36

OUTPUT = Path(__file__).resolve().parent.parent / "firmware" / "slot_icons.yaml"

HEADER = """# Icones reelles (vraies icones d'appli/jeu extraites cote PC, voir
# icon_extract.py) pour les emplacements physiques - une entite online_image
# par emplacement, fetch declenche depuis slots_*.yaml (voir "Slot N -
# icone"). NB: online_image est un composant a part entiere dans cette
# version d'ESPHome (cle top-level 'online_image:', pas 'image: platform:').
# Le telechargement etant async et le pointeur LVGL fige au setup, on
# rappelle lvgl.image.update (re-attache la source, dimensions incluses)
# une fois les pixels reellement prets, sinon le widget reste vide.
#
# Genere par scripts/gen_slot_icons.py, ne pas editer a la main.
online_image:"""


def slot_line(i: int) -> str:
    return (
        f'  - {{id: slot{i}_icon_img, url: "http://0.0.0.0/x.png", format: PNG, type: RGB565, '
        f'byte_order: LITTLE_ENDIAN, resize: 40x40, buffer_size: 8192, update_interval: never, '
        f'http_request_id: http_client, on_download_finished: '
        f'[{{lvgl.image.update: {{id: slot{i}_icon_widget, src: slot{i}_icon_img}}}}, '
        f'{{lambda: "lv_obj_invalidate(id(slot{i}_icon_widget));"}}]}}'
    )


def main() -> None:
    lines = [HEADER] + [slot_line(i) for i in range(1, SLOT_COUNT + 1)]
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
