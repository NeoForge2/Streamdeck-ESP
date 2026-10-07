"""V2 dashboard API helpers independent from the legacy Flask view logic."""

from __future__ import annotations

from typing import Any

from .dashboard_action_choices import action_choices, choice_ids, choice_labels
from .dashboard_v2_catalog import build_dashboard_action_catalog


def _catalog() -> dict[str, Any]:
    """Build from the live runtime registry so plugin changes are visible."""
    return build_dashboard_action_catalog()


def dashboard_action_context() -> dict[str, Any]:
    """Return template-compatible action choices derived from the V2 registry."""
    catalog = _catalog()
    return {
        "action_types": choice_ids(catalog, "button"),
        "encoder_action_types": choice_ids(catalog, "encoder"),
        "action_type_labels": choice_labels(catalog),
    }


def dashboard_action_catalog_payload() -> dict[str, Any]:
    """Return a JSON-serializable V2 catalog for the dynamic Property Inspector."""
    catalog = _catalog()
    return {
        "categories": tuple(catalog.get("categories") or ()),
        "actions": tuple(catalog.get("actions") or ()),
        "choices": {
            "button": action_choices(catalog, "button"),
            "encoder": action_choices(catalog, "encoder"),
        },
    }
