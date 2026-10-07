from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from ..core.actions import ActionCommand, ActionDefinition
from ..core.plugins import PluginContribution, PluginManifest, PluginPermission
from ..core.state import StateValue
from ..core.widgets import WidgetDefinition, WidgetType


class HomeAssistantExampleProvider:
    provider_id = "example.home_assistant"

    def __init__(self, read_states: Callable[[], Iterable[StateValue]]) -> None:
        self._read_states = read_states

    def refresh(self) -> Iterable[StateValue]:
        return self._read_states()


def build_home_assistant_plugin(
    *,
    call_service: Callable[[str, str, str | None, dict[str, Any]], None],
    read_states: Callable[[], Iterable[StateValue]],
) -> tuple[PluginManifest, PluginContribution]:
    manifest = PluginManifest(
        id="example.home_assistant",
        name="Home Assistant Example",
        version="1.0.0",
        permissions=frozenset({PluginPermission.NETWORK, PluginPermission.HOME_ASSISTANT}),
    )
    action = ActionDefinition(
        id="example.ha.service",
        name="Home Assistant Service",
        category="Home Assistant",
        parameters={
            "domain": {"type": "text", "required": True},
            "service": {"type": "text", "required": True},
            "entity_id": {"type": "entity"},
        },
    )

    def execute(command: ActionCommand) -> None:
        params = command.parameters
        domain = str(params.get("domain") or "")
        service = str(params.get("service") or "")
        entity_id = params.get("entity_id")
        data = params.get("data")
        call_service(
            domain,
            service,
            str(entity_id) if entity_id else None,
            dict(data) if isinstance(data, dict) else {},
        )

    return manifest, PluginContribution(
        actions=(action,),
        action_executors={action.id: execute},
        widgets=(
            WidgetDefinition(
                id="example.ha.entity-status",
                widget_type=WidgetType.STATUS,
                state_key="ha:entity",
                config={"entity_parameter": "entity_id"},
            ),
        ),
        providers=(HomeAssistantExampleProvider(read_states),),
        events=("example.ha.state_changed",),
        settings={
            "url": {"type": "text", "required": True},
            "token": {"type": "secret", "required": True},
        },
        assets={"icon": "assets/home-assistant.svg"},
    )
