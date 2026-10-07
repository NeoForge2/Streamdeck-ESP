"""Generic action model independent from integrations and UI frameworks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from .triggers import ActionState, Trigger


class ActionValidationError(ValueError):
    """Raised when an action command does not satisfy its definition."""


ActionValidator = Callable[[Mapping[str, Any]], None]


@dataclass(frozen=True, slots=True)
class ActionDefinition:
    """Describes one action type exposed by the Core registry.

    Concrete execution lives outside the Core. This object only describes
    metadata, supported triggers/states, validation rules and declarative UI
    hints so the same definition can be consumed by the dashboard, plugins
    and runtime adapters.
    """

    id: str
    name: str
    description: str = ""
    category: str = "general"
    icon: str = ""
    parameters: Mapping[str, Any] = field(default_factory=dict)
    supported_triggers: frozenset[Trigger] = field(default_factory=frozenset)
    supported_states: frozenset[ActionState] = field(default_factory=frozenset)
    ui_config: Mapping[str, Any] = field(default_factory=dict)
    validator: ActionValidator | None = field(default=None, compare=False, repr=False)

    def validate(self, values: Mapping[str, Any]) -> None:
        if not isinstance(values, Mapping):
            raise ActionValidationError("Action parameters must be a mapping")
        if self.validator is not None:
            try:
                self.validator(values)
            except ActionValidationError:
                raise
            except (TypeError, ValueError) as exc:
                raise ActionValidationError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class ActionCommand:
    """Configured instance of an action ready to be resolved/executed."""

    action_id: str
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.action_id:
            raise ActionValidationError("action_id cannot be empty")
        if not isinstance(self.parameters, Mapping):
            raise ActionValidationError("parameters must be a mapping")
