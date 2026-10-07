"""Carte meteo (widget dedie, distinct des emplacements generiques) -
lit une entite `weather.*` Home Assistant et en deduit une icone + un
"style d'animation" pour l'ecran (voir firmware/weather_card.yaml, qui
affiche/anime en consequence). La correspondance condition -> (icone,
style) vit ici plutot que dans le lambda firmware pour rester facile a
etendre/corriger sans reflasher pour le mapping lui-meme (seul le
firmware a besoin d'un reflash si un NOUVEAU style d'animation apparait).

Conditions standard Home Assistant (`weather.Weather.condition`) :
clear-night, cloudy, exceptional, fog, hail, lightning, lightning-rainy,
partlycloudy, pouring, rainy, snowy, snowy-rainy, sunny, windy,
windy-variant.

Icones : illustrations amCharts (https://www.amcharts.com/free-animated-svg-weather-icons/,
CC-BY 4.0, voir pc-app/README.md) converties une fois en PNG (voir
scripts/convert_weather_icons.py) et servies par icon_server.py, plutot
que le glyphe Material Icons utilise ailleurs - memes SVG que ceux
empaquetes par bramkragten/weather-card, dont l'utilisateur voulait le
rendu. Les animations SMIL/CSS de ces SVG ne sont pas utilisables sur cet
ecran (LVGL/ESP32 ne rend pas de SVG anime, voir weather_card.yaml) -
seule l'illustration statique est recuperee, notre propre animation
LVGL (pluie/neige/rayons) tourne autour comme avant. Meme convention
"REAL:<cle>" que les icones d'appli/jeu (voir slots_*.yaml) pour
basculer entre image et glyphe de repli cote firmware - toutes les
conditions n'ont pas d'illustration dediee dans ce pack (windy,
exceptional), auquel cas on retombe sur le glyphe Material Icons.
"""

from __future__ import annotations

from . import icons

# Styles d'animation geres cote firmware (voir weather_card.yaml) - un
# style regroupe plusieurs conditions proches visuellement, pour rester
# a un nombre de familles d'animation gerable (chacune est un pool
# d'objets LVGL pre-declares, pas de creation dynamique possible).
# 3e valeur : cle de l'icone amCharts pre-convertie (voir WEATHER_ICON_KEYS
# et icon_server.py), None si aucune illustration dediee dans ce pack -
# repli sur le glyphe Material Icons (icon_key) dans ce cas. 4e valeur :
# libelle en clair affiche au-dessus de l'icone (facon breezy-weather).
_CONDITION_MAP: dict[str, tuple[str, str, str | None, str]] = {
    "sunny": ("wb_sunny", "soleil", "soleil", "Ensoleille"),
    "clear-night": ("nightlight_round", "nuit", "nuit", "Ciel degage"),
    "partlycloudy": ("wb_cloudy", "nuage", "nuage", "Eclaircies"),
    "cloudy": ("cloud", "nuage", "nuage", "Nuageux"),
    "fog": ("cloud_off", "nuage", "nuage", "Brouillard"),
    "windy": ("air", "aucune", None, "Venteux"),
    "windy-variant": ("air", "aucune", None, "Venteux"),
    "rainy": ("water_drop", "pluie", "pluie", "Pluie"),
    "pouring": ("water_drop", "pluie", "pluie", "Forte pluie"),
    "hail": ("grain", "pluie", "pluie", "Grele"),
    "lightning": ("thunderstorm", "pluie", "orage", "Orage"),
    "lightning-rainy": ("thunderstorm", "pluie", "orage", "Orage et pluie"),
    "snowy": ("ac_unit", "neige", "neige", "Neige"),
    "snowy-rainy": ("ac_unit", "neige", "neige", "Neige et pluie"),
    "exceptional": ("warning", "aucune", None, "Alerte meteo"),
}
_DEFAULT_ICON, _DEFAULT_STYLE, _DEFAULT_REAL, _DEFAULT_LABEL = "wb_cloudy", "aucune", None, ""

# Liste blanche des cles d'icone meteo valides (voir icon_server.py) - les
# fichiers PNG correspondants vivent dans static/weather_icons/.
WEATHER_ICON_KEYS = frozenset(key for _, _, key, _label in _CONDITION_MAP.values() if key is not None)


def condition_icon_value(condition: str) -> str:
    """Valeur a pousser dans 'Meteo - icone' : 'REAL:<cle>' si une
    illustration amCharts existe pour cette condition (voir
    WEATHER_ICON_KEYS), sinon le glyphe Material Icons de repli - meme
    convention que les icones d'appli/jeu (voir slots_*.yaml)."""
    icon_key, _, real_key, _label = _CONDITION_MAP.get(
        condition, (_DEFAULT_ICON, _DEFAULT_STYLE, _DEFAULT_REAL, _DEFAULT_LABEL)
    )
    if real_key:
        return f"REAL:{real_key}"
    return icons.icon_char(icon_key)


def condition_animation_style(condition: str) -> str:
    """Style d'animation (voir firmware/weather_card.yaml) pour une
    condition meteo HA - 'aucune' (icone statique) si inconnue."""
    _, style, _, _label = _CONDITION_MAP.get(condition, (_DEFAULT_ICON, _DEFAULT_STYLE, _DEFAULT_REAL, _DEFAULT_LABEL))
    return style


def condition_label(condition: str) -> str:
    """Libelle en clair (francais) affiche au-dessus de l'icone (voir
    weather_card.yaml) - chaine vide si condition inconnue."""
    _, _, _real, label = _CONDITION_MAP.get(condition, (_DEFAULT_ICON, _DEFAULT_STYLE, _DEFAULT_REAL, _DEFAULT_LABEL))
    return label


def format_temperature(state: dict) -> str:
    """'21.5°C' a partir de l'etat brut d'une entite weather.* - la
    temperature est un ATTRIBUT (pas l'etat lui-meme, qui est la
    condition textuelle 'sunny'/'rainy'/...), contrairement a un simple
    capteur numerique."""
    attrs = state.get("attributes") or {}
    temp = attrs.get("temperature")
    if temp is None:
        return ""
    unit = attrs.get("temperature_unit", "°C")
    try:
        return f"{float(temp):g}{unit}"
    except (TypeError, ValueError):
        return f"{temp}{unit}"


def read_weather(client, entity_id: str) -> dict | None:
    """{icon_char, animation_style, temperature, condition_label} pour
    `entity_id`, ou None si l'entite est introuvable/non configuree - voir
    ha_poller.py, qui pousse ces 4 valeurs vers l'ecran (Meteo -
    icone/animation/temperature/condition)."""
    if not entity_id:
        return None
    state = client.get_state(entity_id)
    if state is None:
        return None
    condition = state.get("state", "")
    return {
        "icon_char": condition_icon_value(condition),
        "animation_style": condition_animation_style(condition),
        "temperature": format_temperature(state),
        "condition_label": condition_label(condition),
    }
