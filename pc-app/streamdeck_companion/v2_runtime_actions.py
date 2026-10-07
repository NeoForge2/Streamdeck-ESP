"""Runtime-only V2 actions executed through the existing legacy action path."""

from __future__ import annotations

from typing import Protocol

from . import actions as action_runner
from .core.actions import ActionCommand, ActionDefinition


class NavigationRuntime(Protocol):
    def navigate(self, command: str, target: str | None = None) -> str: ...

    def open_folder(self, folder_id: str) -> str: ...


class MultiActionSubmitter(Protocol):
    def submit(self, definition_id: str, *, context: dict | None = None): ...


def register_navigation_action(runtime: NavigationRuntime) -> None:
    """Install/replace the navigation executor on the shared application engine."""
    action_id = "navigation"
    if action_id in action_runner._ENGINE.registry:
        action_runner._ENGINE.unregister(action_id)
    action_runner._ENGINE.register(
        ActionDefinition(
            id=action_id,
            name="Navigation Streamdeck",
            category="Streamdeck",
            parameters={"target": {"type": "text", "required": True}},
        ),
        lambda command: execute_navigation_target(runtime, str(command.parameters.get("target") or "")),
    )


def register_multi_action(runtime: MultiActionSubmitter) -> None:
    """Expose configured Multi Actions through the existing legacy action path."""
    action_id = "multi_action"
    if action_id in action_runner._ENGINE.registry:
        action_runner._ENGINE.unregister(action_id)
    action_runner._ENGINE.register(
        ActionDefinition(
            id=action_id,
            name="Multi Action",
            category="Streamdeck",
            parameters={"target": {"type": "text", "required": True}},
        ),
        lambda command: _submit_multi_action(runtime, command),
    )


def execute_navigation_target(runtime: NavigationRuntime, raw_target: str) -> str:
    raw = raw_target.strip()
    if not raw:
        raise ValueError("navigation target cannot be empty")
    verb, separator, target = raw.partition(":")
    normalized = verb.strip().lower().replace("-", "_")
    if normalized == "open_folder":
        if not separator or not target:
            raise ValueError("open_folder requires a folder id")
        return runtime.open_folder(target)
    if normalized in {"go_to", "goto"}:
        if not separator or not target:
            raise ValueError("go_to requires a page id")
        return runtime.navigate("go_to", target)
    if separator:
        raise ValueError(f"navigation command {normalized!r} does not accept a target")
    return runtime.navigate(normalized)


def _submit_multi_action(runtime: MultiActionSubmitter, command: ActionCommand):
    definition_id = str(command.parameters.get("target") or "").strip()
    if not definition_id:
        raise ValueError("multi_action target cannot be empty")
    return runtime.submit(definition_id)
