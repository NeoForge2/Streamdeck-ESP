from __future__ import annotations

from dataclasses import dataclass

from .navigation import Folder, Profile


@dataclass(frozen=True, slots=True)
class NavigationSnapshot:
    page_id: str
    folder_id: str | None
    history: tuple[str, ...]


class NavigationSession:
    """Runtime navigation for pages and arbitrarily nested folders."""

    def __init__(self, profile: Profile) -> None:
        self.profile = profile
        self._page_id = profile.home_page_id
        self._folder_id: str | None = None
        self._history: list[tuple[str, str | None]] = []

    @property
    def page_id(self) -> str:
        return self._page_id

    @property
    def folder_id(self) -> str | None:
        return self._folder_id

    def snapshot(self) -> NavigationSnapshot:
        return NavigationSnapshot(self._page_id, self._folder_id, tuple(page for page, _ in self._history))

    def go_to(self, page_id: str, *, folder_id: str | None = None, remember: bool = True) -> NavigationSnapshot:
        if self.profile.page(page_id) is None:
            raise KeyError(page_id)
        if folder_id is not None:
            folder = self.profile.folder(folder_id)
            if folder is None or folder.page_id != page_id:
                raise KeyError(folder_id)
        if remember and (page_id != self._page_id or folder_id != self._folder_id):
            self._history.append((self._page_id, self._folder_id))
        self._page_id, self._folder_id = page_id, folder_id
        return self.snapshot()

    def open_folder(self, folder_id: str) -> NavigationSnapshot:
        folder = self._require_folder(folder_id)
        if folder.parent_id != self._folder_id:
            raise ValueError(f"folder {folder_id!r} is not a child of current folder")
        return self.go_to(folder.page_id, folder_id=folder.id)

    def back(self) -> NavigationSnapshot:
        if not self._history:
            return self.snapshot()
        self._page_id, self._folder_id = self._history.pop()
        return self.snapshot()

    def home(self) -> NavigationSnapshot:
        self._history.clear()
        self._page_id, self._folder_id = self.profile.home_page_id, None
        return self.snapshot()

    def next_page(self) -> NavigationSnapshot:
        return self._relative_page(1)

    def previous_page(self) -> NavigationSnapshot:
        return self._relative_page(-1)

    def _relative_page(self, delta: int) -> NavigationSnapshot:
        page_ids = [page.id for page in self.profile.pages]
        index = page_ids.index(self._page_id)
        return self.go_to(page_ids[(index + delta) % len(page_ids)], folder_id=None)

    def _require_folder(self, folder_id: str) -> Folder:
        folder = self.profile.folder(folder_id)
        if folder is None:
            raise KeyError(folder_id)
        return folder
