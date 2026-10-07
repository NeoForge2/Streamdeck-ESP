from __future__ import annotations

from .actions import ActionDefinition
from .registry import ActionRegistry


class ActionLibrary:
    def __init__(self, registry: ActionRegistry) -> None:
        self.registry = registry

    def categories(self) -> tuple[str, ...]:
        return tuple(sorted({item.category for item in self.registry.list()}))

    def search(self, query: str = "", category: str | None = None) -> tuple[ActionDefinition, ...]:
        items = self.registry.list(category)
        needle = query.strip().casefold()
        if not needle:
            return items
        return tuple(
            item
            for item in items
            if needle in f"{item.id} {item.name} {item.description} {item.category}".casefold()
        )
