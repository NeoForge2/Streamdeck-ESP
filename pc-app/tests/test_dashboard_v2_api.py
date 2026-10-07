from __future__ import annotations

import unittest

from streamdeck_companion.core.actions import ActionDefinition
from streamdeck_companion.core.plugins import PluginContribution, PluginManifest, PluginRegistry
from streamdeck_companion.core.triggers import Trigger
from streamdeck_companion.dashboard_v2_api import (
    dashboard_action_catalog_payload,
    dashboard_action_context,
)
from streamdeck_companion.runtime_action_catalog import RUNTIME_ACTION_REGISTRY


class DashboardV2ApiTests(unittest.TestCase):
    def test_context_is_derived_from_v2_catalog(self) -> None:
        context = dashboard_action_context()
        self.assertIn("navigation", context["action_types"])
        self.assertIn("multi_action", context["action_types"])
        self.assertIn("ha_adjust", context["encoder_action_types"])
        self.assertEqual(context["action_type_labels"]["none"], "Aucune")

    def test_payload_exposes_property_inspector_and_context_choices(self) -> None:
        payload = dashboard_action_catalog_payload()
        actions = {action["id"]: action for action in payload["actions"]}
        self.assertIn("navigation", actions)
        self.assertIn("multi_action", actions)
        self.assertIn("fields", actions["navigation"])
        self.assertTrue(payload["choices"]["button"])
        self.assertTrue(payload["choices"]["encoder"])

    def test_plugin_action_appears_and_disappears_without_catalog_rebuild(self) -> None:
        plugin_registry = PluginRegistry(RUNTIME_ACTION_REGISTRY)
        action = ActionDefinition(
            id="test_plugin_action",
            name="Action plugin test",
            category="Plugins",
            parameters={"target": {"type": "text", "label": "Cible"}},
            supported_triggers=frozenset({Trigger.PRESS}),
            ui_config={
                "inputs": ("button",),
                "fields": ({"key": "target", "type": "text", "label": "Cible"},),
            },
        )
        manifest = PluginManifest(id="test.dashboard", name="Dashboard test", version="1.0.0")
        plugin_registry.register(manifest, PluginContribution(actions=(action,)))
        try:
            payload = dashboard_action_catalog_payload()
            actions = {item["id"]: item for item in payload["actions"]}
            self.assertIn("test_plugin_action", actions)
            self.assertIn("Plugins", payload["categories"])
            self.assertIn(
                "test_plugin_action",
                {item["id"] for item in payload["choices"]["button"]},
            )
        finally:
            plugin_registry.unregister(manifest.id)

        payload = dashboard_action_catalog_payload()
        self.assertNotIn("test_plugin_action", {item["id"] for item in payload["actions"]})


if __name__ == "__main__":
    unittest.main()
