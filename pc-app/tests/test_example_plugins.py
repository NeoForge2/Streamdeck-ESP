from __future__ import annotations

import unittest

from streamdeck_companion.core.actions import ActionCommand
from streamdeck_companion.core.engine import ActionEngine
from streamdeck_companion.core.plugins import PluginPermission, PluginRegistry
from streamdeck_companion.core.providers import ProviderManager
from streamdeck_companion.core.registry import ActionRegistry
from streamdeck_companion.core.state import StateStore, StateValue
from streamdeck_companion.core.triggers import ActionState
from streamdeck_companion.example_plugins.home_assistant_plugin import build_home_assistant_plugin
from streamdeck_companion.example_plugins.obs_plugin import build_obs_plugin
from streamdeck_companion.example_plugins.system_plugin import build_system_plugin


class ExamplePluginTests(unittest.TestCase):
    def test_three_reference_plugins_register_and_execute_without_core_changes(self) -> None:
        actions = ActionRegistry()
        engine = ActionEngine(actions)
        providers = ProviderManager(StateStore())
        plugins = PluginRegistry(
            actions,
            engine=engine,
            providers=providers,
            granted_permissions=frozenset(
                {
                    PluginPermission.PROCESS,
                    PluginPermission.NETWORK,
                    PluginPermission.HOME_ASSISTANT,
                }
            ),
        )
        calls: list[tuple] = []

        system = build_system_plugin(
            launch=lambda target: calls.append(("launch", target)),
            hotkey=lambda keys: calls.append(("hotkey", keys)),
        )
        ha = build_home_assistant_plugin(
            call_service=lambda domain, service, entity_id, data: calls.append(
                ("ha", domain, service, entity_id, data)
            ),
            read_states=lambda: (
                StateValue("ha:light.office", status=ActionState.ON, value=True),
            ),
        )
        obs = build_obs_plugin(
            switch_scene=lambda scene: calls.append(("obs_scene", scene)),
            toggle_recording=lambda: calls.append(("obs_record",)),
        )

        for manifest, contribution in (system, ha, obs):
            plugins.register(manifest, contribution)

        engine.execute(ActionCommand("example.system.launch", {"target": "calc.exe"}))
        engine.execute(
            ActionCommand(
                "example.ha.service",
                {"domain": "light", "service": "toggle", "entity_id": "light.office"},
            )
        )
        engine.execute(ActionCommand("example.obs.switch_scene", {"scene": "Starting Soon"}))

        self.assertIn(("launch", "calc.exe"), calls)
        self.assertIn(("ha", "light", "toggle", "light.office", {}), calls)
        self.assertIn(("obs_scene", "Starting Soon"), calls)
        self.assertEqual(providers.refresh("example.home_assistant")[0].value, True)
        self.assertEqual(len(plugins.list()), 3)


if __name__ == "__main__":
    unittest.main()
