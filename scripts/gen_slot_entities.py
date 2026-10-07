#!/usr/bin/env python3
"""Genere les entites text/select/switch (libelle/valeur/icone/couleur/
type/visible) d'une plage d'emplacements physiques - meme structure que
firmware/slots_1_5.yaml / slots_6_11.yaml / slots_12_16.yaml (ecrits a la
main avant que ce generateur n'existe, PAS regeneres par ce script pour ne
pas risquer de casser un firmware deja teste), utilise ici pour ajouter
les emplacements 17 a 36 (voir docs/ARCHITECTURE.md, bibliotheque
illimitee + 36 emplacements physiques).

Usage: python3 scripts/gen_slot_entities.py
"""

from __future__ import annotations

from pathlib import Path

FIRMWARE_DIR = Path(__file__).resolve().parent.parent / "firmware"

# Chunks sous 500 lignes chacun (meme convention que slots_1_5/6_11/12_16),
# ~80 lignes par emplacement.
CHUNKS = [(17, 21), (22, 26), (27, 31), (32, 36)]


def text_block(i: int) -> str:
    return (
        f'  - platform: template\n'
        f'    id: slot{i}_label\n'
        f'    name: "Slot {i} - libelle"\n'
        f'    mode: text\n'
        f'    optimistic: true\n'
        f'    initial_value: "Slot {i}"\n'
        f'    max_length: 24\n'
        f'    on_value:\n'
        f'      - lvgl.label.update: {{ id: slot{i}_title, text: !lambda "return x;" }}\n'
        f'  - platform: template\n'
        f'    id: slot{i}_value\n'
        f'    name: "Slot {i} - valeur"\n'
        f'    mode: text\n'
        f'    optimistic: true\n'
        f'    initial_value: ""\n'
        f'    max_length: 24\n'
        f'    on_value:\n'
        f'      - lvgl.label.update: {{ id: slot{i}_value_lbl, text: !lambda "return x;" }}\n'
        f'      - lambda: |-\n'
        f'          char *endptr;\n'
        f'          long v = strtol(x.c_str(), &endptr, 10);\n'
        f'          if (endptr != x.c_str()) {{\n'
        f'            if (v < 0) v = 0;\n'
        f'            if (v > 100) v = 100;\n'
        f'            lv_bar_set_value(id(slot{i}_bar), (int) v, LV_ANIM_OFF);\n'
        f'          }}\n'
        f'  - platform: template\n'
        f'    id: slot{i}_icon\n'
        f'    name: "Slot {i} - icone"\n'
        f'    mode: text\n'
        f'    optimistic: true\n'
        f'    initial_value: ""\n'
        f'    max_length: 20\n'
        f'    on_value: [{{if: {{condition: {{lambda: \'return x.rfind("REAL:", 0) == 0;\'}}, then: '
        f'[{{lambda: "lv_obj_add_flag(id(slot{i}_icon_lbl), LV_OBJ_FLAG_HIDDEN); lv_obj_clear_flag(id(slot{i}_icon_widget), LV_OBJ_FLAG_HIDDEN);"}}, '
        f'{{online_image.set_url: {{id: slot{i}_icon_img, url: !lambda \'return id(pc_base_url_text).state + "/slot-icon/{i}.png?v=" + x.substr(5);\'}}}}], '
        f'else: [{{lambda: "lv_obj_clear_flag(id(slot{i}_icon_lbl), LV_OBJ_FLAG_HIDDEN); lv_obj_add_flag(id(slot{i}_icon_widget), LV_OBJ_FLAG_HIDDEN);"}}, '
        f'{{lvgl.label.update: {{id: slot{i}_icon_lbl, text: !lambda "return x;"}}}}]}}}}]\n'
        f'  - platform: template\n'
        f'    id: slot{i}_color\n'
        f'    name: "Slot {i} - couleur"\n'
        f'    mode: text\n'
        f'    optimistic: true\n'
        f'    initial_value: ""\n'
        f'    max_length: 7\n'
        f'    on_value:\n'
        f'      - lvgl.obj.update: {{id: slot{i}_btn, bg_color: !lambda \'return x.length() == 7 ? '
        f'Color(strtoul(x.substr(1,2).c_str(), nullptr, 16), strtoul(x.substr(3,2).c_str(), nullptr, 16), '
        f'strtoul(x.substr(5,2).c_str(), nullptr, 16)) : Color(0x0F, 0x29, 0x42);\'}}\n'
    )


def select_block(i: int) -> str:
    return (
        f'  - platform: template\n'
        f'    id: slot{i}_type\n'
        f'    name: "Slot {i} - type"\n'
        f'    optimistic: true\n'
        f'    options: ["bouton", "barre", "texte"]\n'
        f'    initial_option: "bouton"\n'
        f'    on_value:\n'
        f'      - lambda: |-\n'
        f'          if (x == "barre") {{\n'
        f'            lv_obj_clear_flag(id(slot{i}_bar), LV_OBJ_FLAG_HIDDEN);\n'
        f'            lv_obj_add_flag(id(slot{i}_value_lbl), LV_OBJ_FLAG_HIDDEN);\n'
        f'            lv_obj_clear_flag(id(slot{i}_barre_dec), LV_OBJ_FLAG_HIDDEN);\n'
        f'            lv_obj_clear_flag(id(slot{i}_barre_inc), LV_OBJ_FLAG_HIDDEN);\n'
        f'          }} else if (x == "texte") {{\n'
        f'            lv_obj_add_flag(id(slot{i}_bar), LV_OBJ_FLAG_HIDDEN);\n'
        f'            lv_obj_clear_flag(id(slot{i}_value_lbl), LV_OBJ_FLAG_HIDDEN);\n'
        f'            lv_obj_add_flag(id(slot{i}_barre_dec), LV_OBJ_FLAG_HIDDEN);\n'
        f'            lv_obj_add_flag(id(slot{i}_barre_inc), LV_OBJ_FLAG_HIDDEN);\n'
        f'          }} else {{\n'
        f'            lv_obj_add_flag(id(slot{i}_bar), LV_OBJ_FLAG_HIDDEN);\n'
        f'            lv_obj_add_flag(id(slot{i}_value_lbl), LV_OBJ_FLAG_HIDDEN);\n'
        f'            lv_obj_add_flag(id(slot{i}_barre_dec), LV_OBJ_FLAG_HIDDEN);\n'
        f'            lv_obj_add_flag(id(slot{i}_barre_inc), LV_OBJ_FLAG_HIDDEN);\n'
        f'          }}\n'
    )


def switch_block(i: int) -> str:
    idx = i - 1
    restore = "RESTORE_DEFAULT_ON" if idx < 12 else "RESTORE_DEFAULT_OFF"
    return (
        f'  - platform: template\n'
        f'    id: slot{i}_visible\n'
        f'    name: "Slot {i} - visible"\n'
        f'    optimistic: true\n'
        f'    restore_mode: {restore}\n'
        f'    on_state:\n'
        f'      - lambda: |-\n'
        f'          if (x) {{\n'
        f'            lv_obj_clear_flag(id(slot{i}_btn), LV_OBJ_FLAG_HIDDEN);\n'
        f'          }} else {{\n'
        f'            lv_obj_add_flag(id(slot{i}_btn), LV_OBJ_FLAG_HIDDEN);\n'
        f'          }}\n'
    )


def generate_file(lo: int, hi: int) -> str:
    header = (
        f"# Entites des emplacements {lo} a {hi} (voir docs/ARCHITECTURE.md pour le\n"
        f"# systeme de 36 emplacements physiques configurables). Genere par\n"
        f"# scripts/gen_slot_entities.py, ne pas editer a la main.\n"
        f"text:\n"
    )
    parts = [header]
    parts += [text_block(i) for i in range(lo, hi + 1)]
    parts.append("\nselect:\n")
    parts += [select_block(i) for i in range(lo, hi + 1)]
    parts.append("\nswitch:\n")
    parts += [switch_block(i) for i in range(lo, hi + 1)]
    return "".join(parts)


def main() -> None:
    for lo, hi in CHUNKS:
        content = generate_file(lo, hi)
        out = FIRMWARE_DIR / f"slots_{lo}_{hi}.yaml"
        out.write_text(content, encoding="utf-8")
        print(f"Wrote {out} ({content.count(chr(10))} lines)")


if __name__ == "__main__":
    main()
