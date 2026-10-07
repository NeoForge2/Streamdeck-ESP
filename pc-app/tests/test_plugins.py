from __future__ import annotations

import unittest

from streamdeck_companion.core.actions import ActionDefinition
from streamdeck_companion.core.plugins import (
    PluginContribution,
    PluginManifest,
    PluginPermission,
    PluginRegistrationError,
    PluginRegistry,
)
from streamdeck_companion.core.providers import ProviderManager
from streamdeck_companion.core.registry import ActionRegistry
from streamdeck_companion.core.state import StateStore, StateValue
from streamdeck_companion.core.triggers import ActionState
from streamdeck_companion.core.widgets import WidgetDefinition, WidgetType


class FakeProvider:
    provider_id = "example.provider"

    def refresh(self):
        return (StateValue("example:value", status=ActionState.ACTIVE, value=1),)


class PluginTests(unittest.TestCase):
    def test_plugin_contributes_actions_widgets_provider_events_settings_and_assets(self) -> None:
        actions = ActionRegistry()
        providers = ProviderManager(StateStore())
        registry = PluginRegistry(
            actions,
            providers=providers,
            granted_permissions=frozenset({PluginPermission.NETWORK}),
        )
        manifest = PluginManifest(
            id="example",
            name="Example",
            version="1.0.0",
            permissions=frozenset({PluginPermission.NETWORK}),
        )
        contribution = PluginContribution(
            actions=(ActionDefinition(id="example.do", name="Do", category="Plugins"),),
            widgets=(WidgetDefinition("example.widget", WidgetType.STATUS, state_key="example:value"),),
            providers=(FakeProvider(),),
            events=("example.changed",),
            settings={"host": {"type": "text"}},
            assets={"icon": "assets/icon.svg"},
        )

        registered = registry.register(manifest, contribution)

        self.assertEqual(registered.manifest.id, "example")
        self.assertIsNotNone(actions.get("example.do"))
        self.assertEqual(registry.widgets("example")[0].id, "example.widget")
        self.assertEqual(registry.event_owner("example.changed"), "example")
        self.assertEqual(providers.refresh("example.provider")[0].value, 1)

    def test_permission_must_be_granted(self) -> None:
        registry = PluginRegistry(ActionRegistry())
        manifest = PluginManifest(
            id="network-plugin",
            name="Network",
            version="1",
            permissions=frozenset({PluginPermission.NETWORK}),
        )
        with self.assertRaises(PluginRegistrationError):
            registry.register(manifest, PluginContribution())

    def test_api_version_is_validated(self) -> None:
        with self.assertRaises(ValueError):
            PluginManifest(id="future", name="Future", version="1", api_version=999)

    def test_unregister_removes_contributions(self) -> None:
        actions = ActionRegistry()
        registry = PluginRegistry(actions)
        manifest = PluginManifest(id="simple", name="Simple", version="1")
        contribution = PluginContribution(
            actions=(ActionDefinition(id="simple.action", name="Simple action"),),
            widgets=(WidgetDefinition("simple.widget", WidgetType.TEXT),),
            events=("simple.event",),
        )
        registry.register(manifest, contribution)
        registry.unregister("simple")
        self.assertNotIn("simple.action", actions)
        self.assertEqual(registry.widgets(), ())
        self.assertIsNone(registry.event_owner("simple.event"))

    def test_failed_registration_rolls_back_previous_contributions(self) -> None:
        actions = ActionRegistry()
        actions.register(ActionDefinition(id="collision", name="Existing"))
        registry = PluginRegistry(actions)
        manifest = PluginManifest(id="broken", name="Broken", version="1")
        contribution = PluginContribution(
            actions=(
                ActionDefinition(id="new-action", name="New"),
                ActionDefinition(id="collision", name="Collision"),
            )
        )
        with self.assertRaises(Exception):
            registry.register(manifest, contribution)
        self.assertNotIn("new-action", actions)
        self.assertIsNone(registry.get("broken"))


if __name__ == "__main__":
    unittest.main()
