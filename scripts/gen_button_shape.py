#!/usr/bin/env python3
"""Regenere firmware/button_shape.yaml (select "Forme des boutons" - carre
ou rond, applique le rayon de coin LVGL a tous les emplacements physiques
ET a la carte meteo) - a relancer si SLOT_COUNT change. Extrait de
package.yaml (qui approchait la limite de 500 lignes une fois les 36
emplacements ajoutes) plutot que garde en dur, pour eviter une regression
comme celle du 16->36 emplacements (le switch etait fige a 16 cases et la
carte meteo n'y avait jamais ete incluse).

Usage: python3 scripts/gen_button_shape.py
"""

from __future__ import annotations

from pathlib import Path

SLOT_COUNT = 36

OUTPUT = Path(__file__).resolve().parent.parent / "firmware" / "button_shape.yaml"

HEADER = """# Forme des boutons - modifiable a chaud (carre ou rond) depuis Home
# Assistant ou l'appli PC. radius 12 = coins arrondis, radius 999 = LVGL
# plafonne au max -> cercle. S'applique a tous les emplacements physiques
# (inoffensif sur les widgets, qui n'utilisent que le style de coin du
# conteneur) ET a la carte meteo (weather_card_btn, voir
# firmware/slot_widgets.yaml/gen_weather_card.py).
#
# Genere par scripts/gen_button_shape.py, ne pas editer a la main.
select:
  - platform: template
    id: button_shape
    name: "Forme des boutons"
    optimistic: true
    options: ["carre", "rond"]
    initial_option: "carre"
    on_value:
      - lambda: |-
          int r = (x == "rond") ? 999 : 12;
          lv_obj_set_style_radius(id(weather_card_btn), r, 0);
          for (int i = 1; i <= {slot_count}; i++) {{
            lv_obj_t *btn = nullptr;
            switch (i) {{
{cases}
            }}
            lv_obj_set_style_radius(btn, r, 0);
          }}"""


def main() -> None:
    cases = "\n".join(f"              case {i}: btn = id(slot{i}_btn); break;" for i in range(1, SLOT_COUNT + 1))
    content = HEADER.format(slot_count=SLOT_COUNT, cases=cases)
    OUTPUT.write_text(content + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT} ({content.count(chr(10)) + 1} lines)")


if __name__ == "__main__":
    main()
