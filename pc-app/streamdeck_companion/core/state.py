"""Centralized synchronized state model for Streamdeck-ESP V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any, Callable, Mapping

from .triggers import ActionState


@dataclass(frozen=True, slots=True)
class StateValue:
    key: str
    status: ActionState = ActionState.INACTIVE
    value: Any = None
    attributes: Mapping[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=time)

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("state key cannot be empty")


StateListener = Callable[[StateValue], None]


class StateStore:
    """Single source of truth for dynamic state consumed by the Core/UI."""

    def __init__(self) -> None:
        self._values: dict[str, StateValue] = {}
        self._listeners: list[StateListener] = []

    def get(self, key: str) -> StateValue | None:
        return self._values.get(key)

    def set(self, state: StateValue) -> StateValue:
        self._values[state.key] = state
        for listener in tuple(self._listeners):
            listener(state)
        return state

    def update(
        self,
        key: str,
        *,
        status: ActionState,
        value: Any = None,
        attributes: Mapping[str, Any] | None = None,
    ) -> StateValue:
        return self.set(
            StateValue(
                key=key,
                status=status,
                value=value,
                attributes=attributes or {},
            )
        )

    def subscribe(self, listener: StateListener) -> Callable[[], None]:
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def snapshot(self) -> dict[str, StateValue]:
        return dict(self._values)
