"""Generic input events and trigger bindings for Streamdeck-ESP V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

from .actions import ActionCommand
from .triggers import Trigger


class InputKind(str, Enum):
    BUTTON = "button"
    ENCODER = "encoder"
    TOUCH = "touch"


@dataclass(frozen=True, slots=True)
class InputEvent:
    source_id: str
    kind: InputKind
    trigger: Trigger
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id:
            raise ValueError("source_id cannot be empty")


class TriggerBindings:
    """Maps one physical/logical input source and trigger to an action."""

    def __init__(self) -> None:
        self._bindings: dict[tuple[str, Trigger], ActionCommand] = {}

    def bind(self, source_id: str, trigger: Trigger, command: ActionCommand) -> None:
        if not source_id:
            raise ValueError("source_id cannot be empty")
        self._bindings[(source_id, trigger)] = command

    def unbind(self, source_id: str, trigger: Trigger) -> None:
        self._bindings.pop((source_id, trigger), None)

    def resolve(self, event: InputEvent) -> ActionCommand | None:
        return self._bindings.get((event.source_id, event.trigger))

    def bindings_for(self, source_id: str) -> dict[Trigger, ActionCommand]:
        return {
            trigger: command
            for (bound_source, trigger), command in self._bindings.items()
            if bound_source == source_id
        }
