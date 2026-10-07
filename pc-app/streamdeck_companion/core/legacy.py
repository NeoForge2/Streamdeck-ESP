"""Compatibility adapter for the existing ``{type, target}`` configuration."""

from __future__ import annotations

from typing import Any, Mapping

from .actions import ActionCommand


LEGACY_NONE = "none"


def from_legacy(action: Mapping[str, Any] | None) -> ActionCommand | None:
    """Convert the current config representation without mutating it.

    Existing action types become action ids unchanged. The historical
    ``target`` value is wrapped as a parameter so integrations can migrate
    progressively while dashboard_config.yaml remains backward compatible.
    """
    if not action:
        return None
    action_type = str(action.get("type") or LEGACY_NONE)
    if action_type == LEGACY_NONE:
        return None
    return ActionCommand(action_id=action_type, parameters={"target": action.get("target")})


def to_legacy(command: ActionCommand | None) -> dict[str, Any]:
    """Convert a Core command back to the current on-disk representation."""
    if command is None:
        return {"type": LEGACY_NONE, "target": ""}
    return {
        "type": command.action_id,
        "target": command.parameters.get("target", ""),
    }
