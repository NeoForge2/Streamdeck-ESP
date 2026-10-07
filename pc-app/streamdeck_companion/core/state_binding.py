from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .state import StateStore, StateValue
from .triggers import ActionState


@dataclass(frozen=True, slots=True)
class StateAppearance:
    label: str | None = None
    icon: str | None = None
    value: Any = None
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StateBinding:
    state_key: str
    appearances: Mapping[ActionState, StateAppearance] = field(default_factory=dict)
    fallback: StateAppearance = field(default_factory=StateAppearance)

    def __post_init__(self) -> None:
        if not self.state_key:
            raise ValueError("state_key cannot be empty")


@dataclass(frozen=True, slots=True)
class ResolvedState:
    source: StateValue | None
    status: ActionState
    appearance: StateAppearance


class StateBindingResolver:
    """Maps synchronized source state to generic UI/control presentation."""

    def __init__(self, store: StateStore) -> None:
        self.store = store

    def resolve(self, binding: StateBinding) -> ResolvedState:
        source = self.store.get(binding.state_key)
        status = source.status if source is not None else ActionState.DISCONNECTED
        appearance = binding.appearances.get(status, binding.fallback)
        return ResolvedState(source=source, status=status, appearance=appearance)
