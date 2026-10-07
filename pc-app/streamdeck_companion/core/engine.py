"""Generic action execution engine.

The engine owns orchestration only. Concrete integrations provide executors
as callables, keeping the Core independent from operating systems, Home
Assistant, ESPHome and UI frameworks.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .actions import ActionCommand, ActionDefinition
from .registry import ActionRegistry, UnknownActionError


ActionExecutor = Callable[[ActionCommand], Any]


class MissingExecutorError(RuntimeError):
    """Raised when an action is known but has no runtime executor."""


class ActionEngine:
    """Coordinates action definition lookup, validation and execution."""

    def __init__(self, registry: ActionRegistry | None = None) -> None:
        self.registry = registry if registry is not None else ActionRegistry()
        self._executors: dict[str, ActionExecutor] = {}

    def register(self, definition: ActionDefinition, executor: ActionExecutor) -> None:
        self.registry.register(definition)
        self._executors[definition.id] = executor

    def execute(self, command: ActionCommand) -> Any:
        self.registry.validate(command)
        executor = self._executors.get(command.action_id)
        if executor is None:
            raise MissingExecutorError(command.action_id)
        return executor(command)

    def unregister(self, action_id: str) -> None:
        if action_id not in self.registry:
            raise UnknownActionError(action_id)
        self.registry.unregister(action_id)
        self._executors.pop(action_id, None)
