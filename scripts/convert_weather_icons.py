#!/usr/bin/env python3
"""Convertit les illustrations meteo amCharts (scripts/weather_icons_src/,
SVG, CC-BY 4.0 - voir LICENSE dans ce dossier et
https://www.amcharts.com/free-animated-svg-weather-icons/) en PNG aplatis
sur le fond de la carte meteo, servis ensuite par icon_server.py (voir
weather.py::WEATHER_ICON_KEYS/condition_icon_value).

Seule l'illustration STATIQUE est recuperee - les animations SMIL/CSS de
ces SVG ne peuvent pas s'executer sur l'ecran (LVGL/ESP32 ne rend pas de
SVG anime) ; notre propre animation LVGL (pluie/neige/rayons, voir
firmware/weather_card.yaml) tourne autour de cette image statique.

Aplati sur BUTTON_BG (meme couleur que le fond de la carte, voir
icon_extract.py) plutot que garde en PNG avec canal alpha - le decodeur
PNG cote firmware (online_image, deja utilise pour les icones d'appli)
n'a besoin de composer qu'une seule fois, ici, jamais sur l'ESP32.

Necessite cairosvg (pip install cairosvg) - PAS une dependance de
l'appli PC elle-meme (pas dans requirements.txt), seulement de ce script
de conversion ponctuel. Les PNG generes sont commit dans le repo
(static/weather_icons/), ce script n'a besoin d'etre relance que pour
changer le jeu d'icones.

Usage: pip install cairosvg && python3 scripts/convert_weather_icons.py
"""

from __future__ import annotations

import io
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "weather_icons_src"
OUT_DIR = Path(__file__).resolve().parent.parent / "pc-app" / "streamdeck_companion" / "static" / "weather_icons"

# Meme couleur que weather_card_btn/slotN_btn (voir icon_extract.py::BUTTON_BG).
BUTTON_BG = (0x0F, 0x29, 0x42)
SIZE = 64

# cle (voir weather.py::WEATHER_ICON_KEYS) -> fichier source SVG.
ICON_MAP = {
    "soleil": "day.svg",
    "nuit": "night.svg",
    "nuage": "cloudy.svg",
    "pluie": "rainy-5.svg",
    "neige": "snowy-4.svg",
    "orage": "thunder.svg",
}


def main() -> None:
    import cairosvg
    from PIL import Image

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for key, svg_name in ICON_MAP.items():
        png_bytes = cairosvg.svg2png(url=str(SRC_DIR / svg_name), output_width=SIZE, output_height=SIZE)
        icon = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        background = Image.new("RGB", icon.size, BUTTON_BG)
        background.paste(icon, mask=icon.split()[-1])
        out_path = OUT_DIR / f"{key}.png"
        background.save(out_path)
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
