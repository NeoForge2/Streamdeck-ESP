from __future__ import annotations

import unittest

from streamdeck_companion.core.action_library import ActionLibrary
from streamdeck_companion.core.property_inspector import FieldType, PropertyInspector
from streamdeck_companion.core.triggers import Trigger
from streamdeck_companion.runtime_action_catalog import build_runtime_action_registry


class RuntimeActionCatalogTests(unittest.TestCase):
    def test_catalog_contains_current_runtime_action_types(self) -> None:
        registry = build_runtime_action_registry()
        self.assertEqual(
            {item.id for item in registry.list()},
            {
                "keys",
                "launch",
                "url",
                "media",
                "audio_output",
                "app_volume",
                "app_mute",
                "home_assistant",
                "ha_adjust",
                "navigation",
                "multi_action",
            },
        )

    def test_action_library_and_property_inspector_are_derived_from_same_registry(self) -> None:
        registry = build_runtime_action_registry()
        library = ActionLibrary(registry)
        inspector = PropertyInspector(registry)
        self.assertTrue(any(item.id == "home_assistant" for item in library.search("Home Assistant")))
        schema = inspector.schema("launch")
        self.assertEqual(schema.fields[0].key, "target")
        self.assertEqual(schema.fields[0].field_type, FieldType.TEXT)

    def test_encoder_only_actions_declare_encoder_triggers(self) -> None:
        registry = build_runtime_action_registry()
        app_volume = registry.get("app_volume")
        self.assertIn(Trigger.ROTATE_CW, app_volume.supported_triggers)
        self.assertNotIn(Trigger.DOUBLE_PRESS, app_volume.supported_triggers)


if __name__ == "__main__":
    unittest.main()
