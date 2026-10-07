from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .actions import ActionCommand
from .events import InputEvent, InputKind, TriggerBindings
from .state import StateStore, StateValue
from .triggers import Trigger


@dataclass(frozen=True, slots=True)
class ControlDefinition:
    id: str
    kind: InputKind
    actions: Mapping[Trigger, ActionCommand] = field(default_factory=dict)
    state_key: str | None = None
    context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("control id cannot be empty")
        if self.kind == InputKind.TOUCH and any(
            trigger in {Trigger.ROTATE_CW, Trigger.ROTATE_CCW} for trigger in self.actions
        ):
            raise ValueError("touch controls cannot use encoder rotation triggers")


@dataclass(frozen=True, slots=True)
class ControlSnapshot:
    definition: ControlDefinition
    state: StateValue | None


class ControlRouter:
    """Routes generic input events using the shared TriggerBindings primitive."""

    def __init__(self, controls: tuple[ControlDefinition, ...] = ()) -> None:
        self._controls: dict[str, ControlDefinition] = {}
        self._bindings = TriggerBindings()
        for control in controls:
            self.register(control)

    def register(self, control: ControlDefinition) -> None:
        if control.id in self._controls:
            raise ValueError(f"control already registered: {control.id!r}")
        self._controls[control.id] = control
        for trigger, command in control.actions.items():
            self._bindings.bind(control.id, trigger, command)

    def unregister(self, control_id: str) -> None:
        control = self._controls.pop(control_id, None)
        if control is None:
            return
        for trigger in control.actions:
            self._bindings.unbind(control_id, trigger)

    def resolve(self, event: InputEvent) -> ActionCommand | None:
        control = self._controls.get(event.source_id)
        if control is None or control.kind != event.kind:
            return None
        return self._bindings.resolve(event)

    def get(self, control_id: str) -> ControlDefinition | None:
        return self._controls.get(control_id)


class ControlStateResolver:
    def __init__(self, store: StateStore) -> None:
        self.store = store

    def resolve(self, control: ControlDefinition) -> ControlSnapshot:
        state = self.store.get(control.state_key) if control.state_key else None
        return ControlSnapshot(definition=control, state=state)
