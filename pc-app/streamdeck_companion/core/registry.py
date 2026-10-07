"""Registry of action definitions for the framework-independent Core."""

from __future__ import annotations

from .actions import ActionCommand, ActionDefinition


class DuplicateActionError(ValueError):
    """An action id is already registered."""


class UnknownActionError(KeyError):
    """An action id is not registered."""


class ActionRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ActionDefinition] = {}

    def register(self, definition: ActionDefinition) -> None:
        if not definition.id:
            raise ValueError("Action definition id cannot be empty")
        if definition.id in self._definitions:
            raise DuplicateActionError(definition.id)
        self._definitions[definition.id] = definition

    def unregister(self, action_id: str) -> None:
        if action_id not in self._definitions:
            raise UnknownActionError(action_id)
        del self._definitions[action_id]

    def get(self, action_id: str) -> ActionDefinition:
        if action_id not in self._definitions:
            raise UnknownActionError(action_id)
        return self._definitions[action_id]

    def validate(self, command: ActionCommand) -> ActionDefinition:
        definition = self.get(command.action_id)
        definition.validate(command.parameters)
        return definition

    def list(self, category: str | None = None) -> tuple[ActionDefinition, ...]:
        values = tuple(self._definitions.values())
        if category is None:
            return values
        return tuple(item for item in values if item.category == category)

    def __contains__(self, action_id: object) -> bool:
        return action_id in self._definitions

    def __len__(self) -> int:
        return len(self._definitions)
