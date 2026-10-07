"""Read-only adapter from current profile dictionaries to the V2 Core model."""

from __future__ import annotations

import re
from typing import Any, Mapping

from . import profile_folders, profile_pages
from .core import Folder, GridRect, Page, Placement, Profile


def profile_from_legacy(profile: Mapping[str, Any], *, fallback_index: int = 0) -> Profile:
    """Project one current/backward-compatible profile into the V2 model.

    Historical root slots become the home page. Optional extra pages use the
    backward-compatible ``pages`` collection while sharing the same library.
    Optional nested folders point at those pages. The source mapping is never
    mutated.
    """
    name = str(profile.get("name") or f"Profil {fallback_index + 1}")
    profile_id = str(profile.get("id") or f"profile-{_stable_fragment(name, fallback_index)}")
    descriptors = profile_pages.page_descriptors(profile)
    source_library = profile.get("library") or []

    pages: list[Page] = []
    for descriptor in descriptors:
        page_id = str(descriptor["id"])
        core_page_id = f"{profile_id}:{page_id}"
        source_slots = profile_pages.page_slots(profile, page_id)
        placements: list[Placement] = []
        for index, slot in enumerate(source_slots):
            library_id = slot.get("library_id")
            if not library_id:
                continue
            grid = slot.get("grid") or {}
            placements.append(
                Placement(
                    id=f"{core_page_id}:slot-{index + 1}",
                    content_id=str(library_id),
                    grid=GridRect(
                        col=int(grid.get("col", 0)),
                        row=int(grid.get("row", 0)),
                        colspan=int(grid.get("colspan", 1)),
                        rowspan=int(grid.get("rowspan", 1)),
                    ),
                    metadata={"legacy_slot_index": index},
                )
            )
        pages.append(
            Page(
                id=core_page_id,
                name=str(descriptor["name"]),
                placements=tuple(placements),
                metadata={
                    "legacy_single_page": len(descriptors) == 1,
                    "legacy_page_id": page_id,
                    "shared_library_size": len(source_library),
                },
            )
        )

    folders = tuple(
        Folder(
            id=str(raw["id"]),
            name=str(raw["name"]),
            page_id=f"{profile_id}:{raw['page_id']}",
            parent_id=str(raw["parent_id"]) if raw.get("parent_id") else None,
            icon=str(raw.get("icon") or ""),
            metadata={
                "theme": raw.get("theme") or "",
                "show_back": bool(raw.get("show_back", True)),
            },
        )
        for raw in profile_folders.folder_descriptors(profile)
    )

    home_page_id = f"{profile_id}:{descriptors[0]['id']}"
    return Profile(
        id=profile_id,
        name=name,
        pages=tuple(pages),
        home_page_id=home_page_id,
        folders=folders,
        trigger=profile.get("trigger"),
        metadata={"legacy_adapter": True},
    )


def _stable_fragment(name: str, fallback_index: int) -> str:
    fragment = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return fragment or str(fallback_index + 1)
