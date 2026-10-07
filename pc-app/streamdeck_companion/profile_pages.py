"""Backward-compatible multi-page helpers for legacy profile dictionaries.

The historical root ``slots`` remain the profile home page. Extra pages are
stored under ``pages`` and reference the same action library by ``library_id``.
This lets V2 add pages without changing what legacy code sees at the root.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from . import profiles as profile_utils

HOME_PAGE_ID = "home"
HOME_PAGE_NAME = "Accueil"


class ProfilePageError(ValueError):
    """Invalid or unknown page in the backward-compatible profile format."""


def stable_page_id(name: str, fallback_index: int) -> str:
    fragment = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return fragment or f"page-{fallback_index + 1}"


def page_descriptors(profile: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return home + extra page descriptors without mutating the profile."""
    configured_home_id = str(profile.get("home_page_id") or HOME_PAGE_ID)
    result: list[dict[str, Any]] = [
        {"id": configured_home_id, "name": str(profile.get("home_page_name") or HOME_PAGE_NAME), "home": True}
    ]
    seen = {configured_home_id}
    for index, raw_page in enumerate(profile.get("pages") or []):
        name = str(raw_page.get("name") or f"Page {index + 2}")
        page_id = str(raw_page.get("id") or stable_page_id(name, index + 1))
        if page_id in seen:
            raise ProfilePageError(f"duplicate page id: {page_id!r}")
        seen.add(page_id)
        result.append({"id": page_id, "name": name, "home": False})
    return tuple(result)


def page_slots(profile: Mapping[str, Any], page_id: str) -> list[dict[str, Any]]:
    """Return physical slot assignments for one page.

    The home page always maps to the historical root ``slots``. Extra pages
    carry their own slot assignments while sharing the profile library.
    """
    home_id = str(profile.get("home_page_id") or HOME_PAGE_ID)
    if page_id == home_id:
        return list(profile.get("slots") or [])
    for raw_page in profile.get("pages") or []:
        name = str(raw_page.get("name") or "")
        candidate_id = str(raw_page.get("id") or stable_page_id(name, 0))
        if candidate_id == page_id:
            return list(raw_page.get("slots") or [])
    raise ProfilePageError(f"unknown page: {page_id!r}")


def resolve_page_slot(profile: dict[str, Any], page_id: str, idx: int) -> dict[str, Any]:
    """Resolve a slot using the existing shared action library semantics."""
    if not (0 <= idx < profile_utils.SLOT_COUNT):
        raise IndexError(idx)
    home_id = str(profile.get("home_page_id") or HOME_PAGE_ID)
    if page_id == home_id:
        return profile_utils.resolve_slot(profile, idx)

    slots = page_slots(profile, page_id)
    physical = slots[idx] if idx < len(slots) else {}
    grid = physical.get("grid") or profile_utils.default_grid(idx)
    entry = profile_utils.find_library_entry(profile.get("library"), physical.get("library_id"))
    if entry is None:
        return {
            "label": f"Slot {idx + 1}",
            "icon": "",
            "icon_char": "",
            "type": "bouton",
            "visible": False,
            "action": {"type": "none", "target": ""},
            "ha_entity": "",
            "show_light_color": False,
            "grid": grid,
            "library_id": None,
        }
    return {**entry, "visible": True, "grid": grid, "library_id": physical.get("library_id")}


def new_page(name: str, *, page_id: str | None = None) -> dict[str, Any]:
    """Create an empty extra page using the existing physical-grid format."""
    normalized_name = name.strip()
    if not normalized_name:
        raise ProfilePageError("page name cannot be empty")
    return {
        "id": page_id or stable_page_id(normalized_name, 0),
        "name": normalized_name,
        "slots": profile_utils.default_slots(),
    }
