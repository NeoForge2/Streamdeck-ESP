from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from .state import StateStore, StateValue


class WidgetType(str, Enum):
    BUTTON = "button"
    TEXT = "text"
    ICON = "icon"
    BAR = "bar"
    GAUGE = "gauge"
    GRAPH = "graph"
    IMAGE = "image"
    ANIMATION = "animation"
    STATUS = "status"


@dataclass(frozen=True, slots=True)
class WidgetDefinition:
    id: str
    widget_type: WidgetType
    state_key: str | None = None
    config: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("widget id cannot be empty")


@dataclass(frozen=True, slots=True)
class WidgetSnapshot:
    definition: WidgetDefinition
    state: StateValue | None


class WidgetResolver:
    """Resolves widget data strictly from StateStore, never from providers."""

    def __init__(self, store: StateStore) -> None:
        self.store = store

    def resolve(self, definition: WidgetDefinition) -> WidgetSnapshot:
        state = self.store.get(definition.state_key) if definition.state_key else None
        return WidgetSnapshot(definition=definition, state=state)

    def resolve_many(self, definitions: tuple[WidgetDefinition, ...]) -> tuple[WidgetSnapshot, ...]:
        return tuple(self.resolve(definition) for definition in definitions)
