from __future__ import annotations

import unittest

from streamdeck_companion.core.actions import ActionCommand, ActionDefinition
from streamdeck_companion.core.engine import ActionEngine
from streamdeck_companion.core.plugins import PluginContribution, PluginManifest, PluginRegistry
from streamdeck_companion.core.registry import ActionRegistry


class PluginExecutorTests(unittest.TestCase):
    def test_plugin_action_executes_through_shared_engine(self) -> None:
        registry = ActionRegistry()
        engine = ActionEngine(registry)
        plugins = PluginRegistry(registry, engine=engine)
        calls: list[str] = []
        plugins.register(
            PluginManifest(id="example", name="Example", version="1"),
            PluginContribution(
                actions=(ActionDefinition(id="example.echo", name="Echo", category="Plugins"),),
                action_executors={
                    "example.echo": lambda command: calls.append(str(command.parameters.get("value")))
                },
            ),
        )

        engine.execute(ActionCommand("example.echo", {"value": "hello"}))
        self.assertEqual(calls, ["hello"])

    def test_executor_without_engine_is_rejected(self) -> None:
        registry = ActionRegistry()
        plugins = PluginRegistry(registry)
        with self.assertRaises(ValueError):
            plugins.register(
                PluginManifest(id="example", name="Example", version="1"),
                PluginContribution(
                    actions=(ActionDefinition(id="example.echo", name="Echo"),),
                    action_executors={"example.echo": lambda command: None},
                ),
            )


if __name__ == "__main__":
    unittest.main()
