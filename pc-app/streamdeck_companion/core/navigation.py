"""Profile, page, folder and layout domain model for Streamdeck-ESP V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class GridRect:
    col: int
    row: int
    colspan: int = 1
    rowspan: int = 1

    def __post_init__(self) -> None:
        if self.col < 0 or self.row < 0:
            raise ValueError("grid coordinates must be non-negative")
        if self.colspan < 1 or self.rowspan < 1:
            raise ValueError("grid span must be at least 1x1")


@dataclass(frozen=True, slots=True)
class Placement:
    """Places one logical control/library item on a page."""

    id: str
    content_id: str
    grid: GridRect
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("placement id cannot be empty")
        if not self.content_id:
            raise ValueError("content_id cannot be empty")


@dataclass(frozen=True, slots=True)
class Page:
    id: str
    name: str
    placements: tuple[Placement, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("page id cannot be empty")
        if not self.name:
            raise ValueError("page name cannot be empty")
        placement_ids = [item.id for item in self.placements]
        if len(placement_ids) != len(set(placement_ids)):
            raise ValueError("placement ids must be unique inside a page")


@dataclass(frozen=True, slots=True)
class Folder:
    """Logical navigation folder pointing to one page.

    `parent_id` allows nesting without making the page model recursive.
    """

    id: str
    name: str
    page_id: str
    parent_id: str | None = None
    icon: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("folder id cannot be empty")
        if not self.name:
            raise ValueError("folder name cannot be empty")
        if not self.page_id:
            raise ValueError("folder page_id cannot be empty")
        if self.parent_id == self.id:
            raise ValueError("folder cannot be its own parent")


@dataclass(frozen=True, slots=True)
class Profile:
    id: str
    name: str
    pages: tuple[Page, ...]
    home_page_id: str
    folders: tuple[Folder, ...] = ()
    trigger: Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("profile id cannot be empty")
        if not self.name:
            raise ValueError("profile name cannot be empty")
        if not self.pages:
            raise ValueError("profile must contain at least one page")

        page_ids = [page.id for page in self.pages]
        if len(page_ids) != len(set(page_ids)):
            raise ValueError("page ids must be unique inside a profile")
        if self.home_page_id not in set(page_ids):
            raise ValueError("home_page_id must reference a page in the profile")

        folder_ids = [folder.id for folder in self.folders]
        if len(folder_ids) != len(set(folder_ids)):
            raise ValueError("folder ids must be unique inside a profile")

        known_pages = set(page_ids)
        known_folders = set(folder_ids)
        for folder in self.folders:
            if folder.page_id not in known_pages:
                raise ValueError(f"folder {folder.id!r} references an unknown page")
            if folder.parent_id is not None and folder.parent_id not in known_folders:
                raise ValueError(f"folder {folder.id!r} references an unknown parent")

    def page(self, page_id: str) -> Page | None:
        return next((page for page in self.pages if page.id == page_id), None)

    def folder(self, folder_id: str) -> Folder | None:
        return next((folder for folder in self.folders if folder.id == folder_id), None)
