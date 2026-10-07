from __future__ import annotations

from collections.abc import Callable

from ..core.actions import ActionCommand, ActionDefinition
from ..core.plugins import PluginContribution, PluginManifest, PluginPermission


def build_system_plugin(
    *,
    launch: Callable[[str], None],
    hotkey: Callable[[str], None],
) -> tuple[PluginManifest, PluginContribution]:
    manifest = PluginManifest(
        id="example.system",
        name="System Example",
        version="1.0.0",
        description="Reference local system integration.",
        permissions=frozenset({PluginPermission.PROCESS}),
    )
    actions = (
        ActionDefinition(
            id="example.system.launch",
            name="Launch Application",
            category="Windows",
            parameters={"target": {"type": "text", "label": "Application", "required": True}},
        ),
        ActionDefinition(
            id="example.system.hotkey",
            name="Hotkey",
            category="Windows",
            parameters={"keys": {"type": "hotkey", "label": "Keys", "required": True}},
        ),
    )

    def execute_launch(command: ActionCommand) -> None:
        launch(str(command.parameters.get("target") or ""))

    def execute_hotkey(command: ActionCommand) -> None:
        hotkey(str(command.parameters.get("keys") or ""))

    return manifest, PluginContribution(
        actions=actions,
        action_executors={
            "example.system.launch": execute_launch,
            "example.system.hotkey": execute_hotkey,
        },
        settings={},
        assets={"icon": "assets/system.svg"},
    )
