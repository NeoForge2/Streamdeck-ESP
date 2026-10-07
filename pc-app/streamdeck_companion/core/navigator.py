"""Runtime navigation state for profiles, pages and nested folders."""

from __future__ import annotations

from dataclasses import dataclass, field

from .navigation import Folder, Page, Profile


class NavigationError(ValueError):
    """Raised when a navigation target cannot be resolved."""


@dataclass(slots=True)
class Navigator:
    """Pure Core navigation controller independent from UI and hardware."""

    profile: Profile
    current_page_id: str | None = None
    _history: list[str] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.current_page_id is None:
            self.current_page_id = self.profile.home_page_id
        elif self.profile.page(self.current_page_id) is None:
            raise NavigationError(f"unknown initial page: {self.current_page_id!r}")

    @property
    def current_page(self) -> Page:
        page = self.profile.page(self.current_page_id or "")
        if page is None:  # pragma: no cover - protected by navigation methods
            raise NavigationError("current page no longer exists in profile")
        return page

    @property
    def can_go_back(self) -> bool:
        return bool(self._history)

    def go_to(self, page_id: str, *, remember: bool = True) -> Page:
        page = self.profile.page(page_id)
        if page is None:
            raise NavigationError(f"unknown page: {page_id!r}")
        if page.id == self.current_page_id:
            return page
        if remember and self.current_page_id is not None:
            self._history.append(self.current_page_id)
        self.current_page_id = page.id
        return page

    def home(self) -> Page:
        return self.go_to(self.profile.home_page_id)

    def next(self) -> Page:
        pages = self.profile.pages
        index = self._page_index(self.current_page_id)
        return self.go_to(pages[(index + 1) % len(pages)].id)

    def previous(self) -> Page:
        pages = self.profile.pages
        index = self._page_index(self.current_page_id)
        return self.go_to(pages[(index - 1) % len(pages)].id)

    def back(self) -> Page:
        if not self._history:
            return self.current_page
        page_id = self._history.pop()
        page = self.profile.page(page_id)
        if page is None:  # pragma: no cover - immutable Profile guarantees this
            raise NavigationError(f"history references unknown page: {page_id!r}")
        self.current_page_id = page.id
        return page

    def open_folder(self, folder_id: str) -> Page:
        folder = self.profile.folder(folder_id)
        if folder is None:
            raise NavigationError(f"unknown folder: {folder_id!r}")
        return self.go_to(folder.page_id)

    def folder_path(self, folder_id: str) -> tuple[Folder, ...]:
        folder = self.profile.folder(folder_id)
        if folder is None:
            raise NavigationError(f"unknown folder: {folder_id!r}")

        result: list[Folder] = []
        seen: set[str] = set()
        current: Folder | None = folder
        while current is not None:
            if current.id in seen:
                raise NavigationError("folder hierarchy contains a cycle")
            seen.add(current.id)
            result.append(current)
            current = self.profile.folder(current.parent_id) if current.parent_id else None
        result.reverse()
        return tuple(result)

    def reset_profile(self, profile: Profile) -> Page:
        self.profile = profile
        self._history.clear()
        self.current_page_id = profile.home_page_id
        return self.current_page

    def _page_index(self, page_id: str | None) -> int:
        for index, page in enumerate(self.profile.pages):
            if page.id == page_id:
                return index
        raise NavigationError(f"unknown current page: {page_id!r}")
