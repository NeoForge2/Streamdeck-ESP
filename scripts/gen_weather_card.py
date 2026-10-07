#!/usr/bin/env python3
"""Regenere firmware/weather_card.yaml (carte meteo dediee, un seul
exemplaire - voir docs/ARCHITECTURE.md). Contrairement aux emplacements,
peu d'interet a scripter un template par "instance" ici (il n'y en a
qu'une) - le generateur sert surtout a eviter de recompter les positions
des gouttes/flocons/nuages a la main si on change leur nombre.

Le bouton de la carte elle-meme (weather_card_btn) n'est PAS dans ce
fichier : il doit partager le meme espace de coordonnees que les
emplacements (enfant de package.yaml::action_grid, positionne relatif a
son origine), donc weather_button_widget() est importee et ajoutee par
scripts/gen_slot_widgets.py a la fin de firmware/slot_widgets.yaml -
`!include` ne pouvant remplacer qu'une seule cle, ce sont deux fichiers
distincts INCLUS de deux facons differentes (`packages:` pour celui-ci,
liste `widgets:` pour le bouton) qui doivent rester coherents.

Usage: python3 scripts/gen_weather_card.py
"""

from __future__ import annotations

from pathlib import Path

CELL = 96
GAP = 12
PITCH = 108

RAIN_COUNT = 5
SNOW_COUNT = 5
STAR_COUNT = 3
RAY_COUNT = 5
CLOUD_COUNT = 2

OUTPUT = Path(__file__).resolve().parent.parent / "firmware" / "weather_card.yaml"

HEADER = """# Carte meteo (widget dedie, distinct des emplacements generiques -
# voir docs/ARCHITECTURE.md) : icone + temperature, animee selon la
# condition (pluie qui tombe, neige, soleil qui scintille, nuages qui
# derivent, etoiles la nuit). Un seul exemplaire par profil - le bouton
# lui-meme (weather_card_btn) est dans slot_widgets.yaml (voir
# scripts/gen_weather_card.py pour le pourquoi), CE fichier ne contient que
# les entites/la logique d'animation qui le pilotent.
#
# L'appli PC (weather.py) traduit l'entite weather.* de Home Assistant en
# 4 valeurs poussees ici : "Meteo - icone" (illustration amCharts ou glyphe
# de repli), "Meteo - animation" (style : soleil/nuit/nuage/pluie/neige/
# aucune), "Meteo - temperature" (texte forme) et "Meteo - condition"
# (libelle en clair, ex "Ensoleille" - facon breezy-weather, dont l'en-tete
# affiche la condition en texte au-dessus d'un gros numero, plutot que
# bramkragten/weather-card qui n'en montre pas). Le firmware ne connait PAS
# Home Assistant - il se
# contente d'afficher/animer selon le style recu, comme les emplacements
# recoivent deja leur glyphe tout fait plutot que de choisir eux-memes.
#
# Animation : PAS de lv_anim_t (API dont la disponibilite/signature exacte
# depend trop precisement de la version LVGL packagee par ESPHome pour
# etre fiable sans pouvoir compiler/tester) - un seul `interval:` (90ms)
# deplace/montre/cache les objets pre-declares via des appels bruts deja
# eprouves ailleurs dans ce firmware (lv_obj_set_x/y, lv_obj_set_style_bg_opa,
# add_flag/clear_flag LV_OBJ_FLAG_HIDDEN - memes primitives que
# slot_grid.yaml/button_shape). Position/taille de la carte : meme
# mecanisme que slot_grid.yaml (une entite texte compacte + lambda),
# CELL/GAP/PITCH doivent rester coherents avec scripts/gen_slot_grid.py.
#
# Genere par scripts/gen_weather_card.py, ne pas editer a la main."""


def _obj_decl(obj_id: str, width: int, height: int, radius: int, bg_color: str) -> str:
    # Opacite fixe (bg_opa: statique en YAML) volontairement omise partout -
    # incertitude sur le format exact accepte par le schema ESPHome (mot-cle
    # vs pourcentage vs entier 0-255), a l'inverse de lv_obj_set_style_bg_opa()
    # (API LVGL brute, stable, deja utilisee ailleurs dans ce fichier pour le
    # scintillement) : mieux vaut un nuage/etoile/rayon opaque a l'affichage
    # que de risquer une valeur de config invalide qui casse toute la build.
    return (
        f'{{obj: {{id: {obj_id}, x: 0, y: 0, width: {width}, height: {height}, '
        f'radius: {radius}, bg_color: {bg_color}, border_width: 0, '
        f'shadow_width: 0, hidden: true, clickable: false}}}}'
    )


def _sub_widgets() -> list[str]:
    parts = []
    for i in range(1, RAIN_COUNT + 1):
        parts.append(_obj_decl(f"weather_rain{i}", 2, 10, 1, "0x4FC3F7"))
    for i in range(1, SNOW_COUNT + 1):
        parts.append(_obj_decl(f"weather_snow{i}", 5, 5, 999, "0xFFFFFF"))
    for i in range(1, CLOUD_COUNT + 1):
        parts.append(_obj_decl(f"weather_cloud{i}", 40, 18, 9, "0xC7D9E8"))
    for i in range(1, STAR_COUNT + 1):
        parts.append(_obj_decl(f"weather_star{i}", 3, 3, 999, "0xFFF176"))
    for i in range(1, RAY_COUNT + 1):
        # Petits points (pas des barres orientees, voir build_interval_lambda
        # pour le pourquoi) disposes en halo circulaire autour de l'icone.
        parts.append(_obj_decl(f"weather_ray{i}", 5, 5, 999, "0xFFC107"))
    # Synthese finale (apres 3 references differentes) : condition en texte
    # en haut ("Ensoleille"), icone amCharts au milieu, GROSSE temperature
    # en bas - facon breezy-weather (gros numero = le vrai "hero", condition
    # au-dessus, PAS d'icone dans son en-tete a elle) combine a l'illustration
    # amCharts (bramkragten/weather-card, deja convertie) et au regroupement
    # compact centre (retour utilisateur : un ancrage aux bords laisse un
    # grand vide sur une carte redimensionnee haute/etroite). Empile
    # verticalement, ancre au CENTRE de la carte (decalages en y depuis le
    # centre, pas depuis un bord) pour rester equilibre quelle que soit la
    # forme de la carte.
    parts.append(
        '{label: {id: weather_condition_lbl, text: "", text_font: font_body, '
        'text_color: 0xB8C7D6, text_align: center, align: center, y: -46, '
        'long_mode: dot, width: 140}}'
    )
    # Illustration amCharts (voir weather.py::WEATHER_ICON_KEYS) OU glyphe
    # Material Icons de repli - meme bascule "REAL:<cle>" que les icones
    # d'appli/jeu (voir slots_*.yaml/slot_icons.yaml), un seul des deux est
    # visible a la fois (voir le lambda "Meteo - icone" dans weather_card.yaml).
    parts.append(
        '{image: {id: weather_icon_widget, src: weather_icon_img, width: 56, height: 56, '
        'align: center, y: -2, hidden: true}}'
    )
    parts.append(
        '{label: {id: weather_icon_lbl, text: "", text_font: font_icons, '
        'text_color: 0xFFFFFF, align: center, y: -2}}'
    )
    parts.append(
        '{label: {id: weather_temp_lbl, text: "", text_font: font_mono_xl, '
        'text_color: 0xFFFFFF, text_align: center, align: center, y: 40, '
        'long_mode: dot, width: 150}}'
    )
    return parts


def weather_button_widget() -> str:
    """Le bouton de la carte meteo (une seule ligne YAML flow), a inserer
    comme 17e element de la liste widgets: de slot_widgets.yaml (voir
    gen_slot_widgets.py) - meme espace de coordonnees que les 16
    emplacements (enfant de action_grid), position/taille par defaut 2x2
    cases en haut a gauche (repositionnee par le PC des connexion, comme
    les emplacements)."""
    size = 2 * CELL + GAP
    widgets = ", ".join(_sub_widgets())
    return (
        f'- button: {{id: weather_card_btn, x: 0, y: 0, align: top_left, '
        f'width: {size}, height: {size}, bg_color: 0x0F2942, border_color: 0x1A3A52, '
        f'border_width: 1, radius: 12, hidden: true, clickable: false, '
        f'widgets: [{widgets}]}}'
    )


def build_interval_lambda() -> str:
    lines: list[str] = []
    lines.append("id(weather_tick) += 1;")
    lines.append("int t = id(weather_tick);")
    lines.append("std::string style = id(weather_style);")
    lines.append("int w = id(weather_w);")
    lines.append("int h = id(weather_h);")
    lines.append("bool show_rain = (style == \"pluie\");")
    lines.append("bool show_snow = (style == \"neige\");")
    lines.append("bool show_cloud = (style == \"nuage\");")
    lines.append("bool show_star = (style == \"nuit\");")
    lines.append("bool show_sun = (style == \"soleil\");")
    lines.append("")

    rain_ids = ", ".join(f"id(weather_rain{i})" for i in range(1, RAIN_COUNT + 1))
    lines.append(f"lv_obj_t *rain[{RAIN_COUNT}] = {{{rain_ids}}};")
    lines.append(f"for (int i = 0; i < {RAIN_COUNT}; i++) {{")
    lines.append("  if (show_rain) lv_obj_clear_flag(rain[i], LV_OBJ_FLAG_HIDDEN); else lv_obj_add_flag(rain[i], LV_OBJ_FLAG_HIDDEN);")
    lines.append("  if (show_rain) {")
    lines.append("    int span = h + 20;")
    lines.append("    int y = ((t * 4 + i * (span / 3)) % span) - 20;")
    lines.append("    int x = (i * w) / 5;")
    lines.append("    lv_obj_set_pos(rain[i], x, y);")
    lines.append("  }")
    lines.append("}")
    lines.append("")

    snow_ids = ", ".join(f"id(weather_snow{i})" for i in range(1, SNOW_COUNT + 1))
    lines.append(f"lv_obj_t *snow[{SNOW_COUNT}] = {{{snow_ids}}};")
    lines.append(f"for (int i = 0; i < {SNOW_COUNT}; i++) {{")
    lines.append("  if (show_snow) lv_obj_clear_flag(snow[i], LV_OBJ_FLAG_HIDDEN); else lv_obj_add_flag(snow[i], LV_OBJ_FLAG_HIDDEN);")
    lines.append("  if (show_snow) {")
    lines.append("    int span = h + 20;")
    lines.append("    int y = ((t * 2 + i * (span / 3)) % span) - 20;")
    lines.append("    int drift = ((t + i * 30) % 40) - 20;")
    lines.append("    int x = (i * w) / 5 + drift / 4;")
    lines.append("    lv_obj_set_pos(snow[i], x, y);")
    lines.append("  }")
    lines.append("}")
    lines.append("")

    cloud_ids = ", ".join(f"id(weather_cloud{i})" for i in range(1, CLOUD_COUNT + 1))
    lines.append(f"lv_obj_t *cloud[{CLOUD_COUNT}] = {{{cloud_ids}}};")
    lines.append(f"for (int i = 0; i < {CLOUD_COUNT}; i++) {{")
    lines.append("  if (show_cloud) lv_obj_clear_flag(cloud[i], LV_OBJ_FLAG_HIDDEN); else lv_obj_add_flag(cloud[i], LV_OBJ_FLAG_HIDDEN);")
    lines.append("  if (show_cloud) {")
    lines.append("    int span = w + 60;")
    lines.append("    int x = ((t + i * (span / 2)) % span) - 50;")
    lines.append("    int y = 15 + i * 20;")
    lines.append("    lv_obj_set_pos(cloud[i], x, y);")
    lines.append("  }")
    lines.append("}")
    lines.append("")

    star_ids = ", ".join(f"id(weather_star{i})" for i in range(1, STAR_COUNT + 1))
    lines.append(f"lv_obj_t *star[{STAR_COUNT}] = {{{star_ids}}};")
    lines.append(f"const int star_x[{STAR_COUNT}] = {{15, w - 20, w / 2}};")
    lines.append(f"const int star_y[{STAR_COUNT}] = {{15, 25, h - 25}};")
    lines.append(f"for (int i = 0; i < {STAR_COUNT}; i++) {{")
    lines.append("  if (show_star) lv_obj_clear_flag(star[i], LV_OBJ_FLAG_HIDDEN); else lv_obj_add_flag(star[i], LV_OBJ_FLAG_HIDDEN);")
    lines.append("  if (show_star) {")
    lines.append("    lv_obj_set_pos(star[i], star_x[i], star_y[i]);")
    lines.append("    int phase = (t * 3 + i * 40) % 120;")
    lines.append("    int opa = phase < 60 ? phase * 4 : (120 - phase) * 4;")
    lines.append("    lv_obj_set_style_bg_opa(star[i], opa, 0);")
    lines.append("  }")
    lines.append("}")
    lines.append("")

    # Halo circulaire de points (pas de barres orientees vers l'exterieur -
    # tourner un objet demanderait lv_obj_set_style_transform_angle, une API
    # non encore utilisee/eprouvee ailleurs dans ce firmware, voir le
    # raisonnement "pas de lv_anim_t" en tete de fichier) centre sur l'icone
    # (align center, y=-2 - voir _sub_widgets) : 5 points repartis tous les
    # 72 degres sur un cercle de rayon fixe (22px), decalages en x/y fixes
    # ajoutes a (w/2, h/2) pour suivre le CENTRE de la carte quelle que soit
    # sa taille (meme logique de "groupe ancre au centre" que l'icone/la
    # temperature/la condition).
    ray_ids = ", ".join(f"id(weather_ray{i})" for i in range(1, RAY_COUNT + 1))
    lines.append(f"lv_obj_t *ray[{RAY_COUNT}] = {{{ray_ids}}};")
    lines.append(f"const int ray_dx[{RAY_COUNT}] = {{0, 21, 13, -13, -21}};")
    lines.append(f"const int ray_dy[{RAY_COUNT}] = {{-24, -9, 16, 16, -9}};")
    lines.append(f"for (int i = 0; i < {RAY_COUNT}; i++) {{")
    lines.append("  if (show_sun) lv_obj_clear_flag(ray[i], LV_OBJ_FLAG_HIDDEN); else lv_obj_add_flag(ray[i], LV_OBJ_FLAG_HIDDEN);")
    lines.append("  if (show_sun) {")
    lines.append("    lv_obj_set_pos(ray[i], w / 2 + ray_dx[i], h / 2 - 2 + ray_dy[i]);")
    lines.append("    int phase = (t * 3 + i * 30) % 150;")
    lines.append("    int opa = phase < 75 ? 80 + phase * 2 : 80 + (150 - phase) * 2;")
    lines.append("    lv_obj_set_style_bg_opa(ray[i], opa, 0);")
    lines.append("  }")
    lines.append("}")

    return "\n".join(("          " + l) if l else "" for l in lines)


def main() -> None:
    interval_body = build_interval_lambda()
    size = 2 * CELL + GAP

    content = f"""{HEADER}

globals:
  - id: weather_tick
    type: int
    restore_value: false
    initial_value: '0'
  - id: weather_style
    type: std::string
    restore_value: false
    initial_value: '"aucune"'
  - id: weather_w
    type: int
    restore_value: false
    initial_value: '{size}'
  - id: weather_h
    type: int
    restore_value: false
    initial_value: '{size}'

switch:
  - platform: template
    id: weather_visible_switch
    name: "Meteo - visible"
    optimistic: true
    restore_mode: ALWAYS_OFF
    on_turn_on:
      - lvgl.widget.update: {{id: weather_card_btn, hidden: false}}
    on_turn_off:
      - lvgl.widget.update: {{id: weather_card_btn, hidden: true}}

# Illustration meteo amCharts pre-convertie (voir weather.py,
# scripts/convert_weather_icons.py, icon_server.py) - meme mecanisme que
# slot_icons.yaml (online_image + rappel lvgl.image.update une fois les
# pixels reellement prets), pas de version/hash dans l'URL contrairement
# aux icones d'appli : le jeu d'icones meteo est fixe, seule la CLE (donc
# l'URL) change d'une condition a l'autre, ce qui suffit a declencher un
# nouveau telechargement.
online_image:
  - {{id: weather_icon_img, url: "http://0.0.0.0/x.png", format: PNG, type: RGB565, byte_order: LITTLE_ENDIAN, resize: 56x56, buffer_size: 12288, update_interval: never, http_request_id: http_client, on_download_finished: [{{lvgl.image.update: {{id: weather_icon_widget, src: weather_icon_img}}}}, {{lambda: "lv_obj_invalidate(id(weather_icon_widget));"}}]}}

text:
  - platform: template
    id: weather_grid_text
    name: "Meteo - grille"
    mode: text
    optimistic: true
    initial_value: "0,0,2,2"
    max_length: 16
    on_value:
      - lambda: |-
          int col=0,row=0,cs=1,rs=1;
          sscanf(x.c_str(), "%d,%d,%d,%d", &col, &row, &cs, &rs);
          const int cell={CELL}, gap={GAP}, pitch={PITCH};
          int px = col*pitch, py = row*pitch;
          int pw = cs*cell + (cs-1)*gap;
          int ph = rs*cell + (rs-1)*gap;
          lv_obj_set_pos(id(weather_card_btn), px, py);
          lv_obj_set_size(id(weather_card_btn), pw, ph);
          id(weather_w) = pw;
          id(weather_h) = ph;
  - platform: template
    id: weather_icon_text
    name: "Meteo - icone"
    mode: text
    optimistic: true
    initial_value: ""
    max_length: 12
    on_value: [{{if: {{condition: {{lambda: 'return x.rfind("REAL:", 0) == 0;'}}, then: [{{lambda: "lv_obj_add_flag(id(weather_icon_lbl), LV_OBJ_FLAG_HIDDEN); lv_obj_clear_flag(id(weather_icon_widget), LV_OBJ_FLAG_HIDDEN);"}}, {{online_image.set_url: {{id: weather_icon_img, url: !lambda 'return id(pc_base_url_text).state + "/weather-icon/" + x.substr(5) + ".png";'}}}}], else: [{{lambda: "lv_obj_clear_flag(id(weather_icon_lbl), LV_OBJ_FLAG_HIDDEN); lv_obj_add_flag(id(weather_icon_widget), LV_OBJ_FLAG_HIDDEN);"}}, {{lvgl.label.update: {{id: weather_icon_lbl, text: !lambda "return x;"}}}}]}}}}]
  - platform: template
    id: weather_temperature_text
    name: "Meteo - temperature"
    mode: text
    optimistic: true
    initial_value: ""
    max_length: 16
    on_value:
      - lvgl.label.update: {{id: weather_temp_lbl, text: !lambda "return x;"}}
  - platform: template
    id: weather_condition_text
    name: "Meteo - condition"
    mode: text
    optimistic: true
    initial_value: ""
    max_length: 20
    on_value:
      - lvgl.label.update: {{id: weather_condition_lbl, text: !lambda "return x;"}}
  - platform: template
    id: weather_animation_text
    name: "Meteo - animation"
    mode: text
    optimistic: true
    initial_value: "aucune"
    max_length: 16
    on_value:
      - lambda: |-
          id(weather_style) = x;

interval:
  - interval: 90ms
    then:
      - lambda: |-
{interval_body}
"""
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
