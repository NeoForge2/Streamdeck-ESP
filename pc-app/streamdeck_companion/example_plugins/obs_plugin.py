from __future__ import annotations

from collections.abc import Callable

from ..core.actions import ActionCommand, ActionDefinition
from ..core.plugins import PluginContribution, PluginManifest, PluginPermission
from ..core.widgets import WidgetDefinition, WidgetType


def build_obs_plugin(
    *,
    switch_scene: Callable[[str], None],
    toggle_recording: Callable[[], None],
) -> tuple[PluginManifest, PluginContribution]:
    manifest = PluginManifest(
        id="example.obs",
        name="OBS Example",
        version="1.0.0",
        permissions=frozenset({PluginPermission.NETWORK}),
    )
    switch = ActionDefinition(
        id="example.obs.switch_scene",
        name="Switch OBS Scene",
        category="OBS",
        parameters={"scene": {"type": "text", "required": True}},
    )
    record = ActionDefinition(
        id="example.obs.toggle_recording",
        name="Toggle OBS Recording",
        category="OBS",
    )

    def execute_switch(command: ActionCommand) -> None:
        switch_scene(str(command.parameters.get("scene") or ""))

    def execute_record(_command: ActionCommand) -> None:
        toggle_recording()

    return manifest, PluginContribution(
        actions=(switch, record),
        action_executors={switch.id: execute_switch, record.id: execute_record},
        widgets=(
            WidgetDefinition(
                id="example.obs.recording-status",
                widget_type=WidgetType.STATUS,
                state_key="obs:recording",
            ),
        ),
        events=("example.obs.recording_changed", "example.obs.scene_changed"),
        settings={"websocket_url": {"type": "text", "required": True}},
        assets={"icon": "assets/obs.svg"},
    )
