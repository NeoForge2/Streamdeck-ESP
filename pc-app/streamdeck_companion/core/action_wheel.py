from __future__ import annotations

from dataclasses import dataclass

from .actions import ActionCommand


@dataclass(frozen=True, slots=True)
class ActionWheelItem:
    id: str
    label: str
    action: ActionCommand
    icon: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("wheel item id cannot be empty")
        if not self.label:
            raise ValueError("wheel item label cannot be empty")


@dataclass(frozen=True, slots=True)
class ActionWheelSnapshot:
    selected_index: int
    selected: ActionWheelItem
    items: tuple[ActionWheelItem, ...]


class ActionWheel:
    """Renderer-independent rotary selection model for an encoder/touch wheel."""

    def __init__(self, items: tuple[ActionWheelItem, ...], *, selected_index: int = 0) -> None:
        if not items:
            raise ValueError("action wheel requires at least one item")
        ids = [item.id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("action wheel item ids must be unique")
        if not 0 <= selected_index < len(items):
            raise ValueError("selected_index is out of range")
        self.items = items
        self._selected_index = selected_index

    @property
    def selected_index(self) -> int:
        return self._selected_index

    @property
    def selected(self) -> ActionWheelItem:
        return self.items[self._selected_index]

    def rotate(self, delta: int) -> ActionWheelSnapshot:
        if delta:
            self._selected_index = (self._selected_index + delta) % len(self.items)
        return self.snapshot()

    def select(self, item_id: str) -> ActionWheelSnapshot:
        for index, item in enumerate(self.items):
            if item.id == item_id:
                self._selected_index = index
                return self.snapshot()
        raise KeyError(item_id)

    def activate(self) -> ActionCommand:
        return self.selected.action

    def snapshot(self) -> ActionWheelSnapshot:
        return ActionWheelSnapshot(self._selected_index, self.selected, self.items)
