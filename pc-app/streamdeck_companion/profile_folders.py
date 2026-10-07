"""Backward-compatible helpers for nested navigation folders in profiles."""

from __future__ import annotations

import re
from typing import Any, Mapping

from . import profile_pages


class ProfileFolderError(ValueError):
    pass


def stable_folder_id(name: str, fallback_index: int) -> str:
    fragment = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return fragment or f"folder-{fallback_index + 1}"


def folder_descriptors(profile: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    pages = {str(page["id"]) for page in profile_pages.page_descriptors(profile)}
    raw_folders = profile.get("folders") or []
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_folders):
        name = str(raw.get("name") or f"Dossier {index + 1}").strip()
        folder_id = str(raw.get("id") or stable_folder_id(name, index))
        page_id = str(raw.get("page_id") or "")
        parent_id = str(raw.get("parent_id")) if raw.get("parent_id") else None
        if not name:
            raise ProfileFolderError("folder name cannot be empty")
        if folder_id in seen:
            raise ProfileFolderError(f"duplicate folder id: {folder_id!r}")
        if page_id not in pages:
            raise ProfileFolderError(f"folder {folder_id!r} references unknown page {page_id!r}")
        seen.add(folder_id)
        result.append(
            {
                "id": folder_id,
                "name": name,
                "page_id": page_id,
                "parent_id": parent_id,
                "icon": str(raw.get("icon") or ""),
                "theme": str(raw.get("theme") or ""),
                "show_back": bool(raw.get("show_back", True)),
            }
        )
    for folder in result:
        parent_id = folder["parent_id"]
        if parent_id is not None and parent_id not in seen:
            raise ProfileFolderError(
                f"folder {folder['id']!r} references unknown parent {parent_id!r}"
            )
        if parent_id == folder["id"]:
            raise ProfileFolderError("folder cannot be its own parent")
    _validate_no_cycles(result)
    return tuple(result)


def new_folder(
    name: str,
    page_id: str,
    *,
    folder_id: str | None = None,
    parent_id: str | None = None,
    icon: str = "",
    theme: str = "",
    show_back: bool = True,
) -> dict[str, Any]:
    normalized_name = name.strip()
    if not normalized_name:
        raise ProfileFolderError("folder name cannot be empty")
    if not page_id:
        raise ProfileFolderError("folder page_id cannot be empty")
    return {
        "id": folder_id or stable_folder_id(normalized_name, 0),
        "name": normalized_name,
        "page_id": page_id,
        "parent_id": parent_id,
        "icon": icon,
        "theme": theme,
        "show_back": show_back,
    }


def _validate_no_cycles(folders: list[dict[str, Any]]) -> None:
    parents = {str(item["id"]): item.get("parent_id") for item in folders}
    for folder_id in parents:
        visited: set[str] = set()
        current: str | None = folder_id
        while current is not None:
            if current in visited:
                raise ProfileFolderError(f"folder cycle detected at {current!r}")
            visited.add(current)
            parent = parents.get(current)
            current = str(parent) if parent is not None else None
