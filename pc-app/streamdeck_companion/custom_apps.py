"""Applications "personnalisees" ajoutees a la bibliotheque via la tuile
"+ Ajouter" du picker (popup d'emplacement, type d'action 'launch') -
persistees dans dashboard_config.yaml (cle 'custom_apps') pour venir
enrichir la liste detectee automatiquement (menu Demarrer) au fil du temps
- utile pour les jeux portables ou applications sans raccourci Demarrer."""

from __future__ import annotations

from pathlib import Path

from .device_client import load_config, save_config


def list_custom_apps(config_path: Path) -> list[dict[str, str]]:
    return load_config(config_path).get("custom_apps") or []


def add_custom_app(config_path: Path, name: str, target: str) -> list[dict[str, str]]:
    config = load_config(config_path)
    apps = [a for a in (config.get("custom_apps") or []) if a.get("target") != target]
    apps.append({"name": name, "target": target})
    config["custom_apps"] = apps
    save_config(config_path, config)
    return apps


def remove_custom_app(config_path: Path, target: str) -> list[dict[str, str]]:
    config = load_config(config_path)
    apps = [a for a in (config.get("custom_apps") or []) if a.get("target") != target]
    config["custom_apps"] = apps
    save_config(config_path, config)
    return apps
