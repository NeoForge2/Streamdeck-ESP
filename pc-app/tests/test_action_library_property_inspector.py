from __future__ import annotations

import unittest

from streamdeck_companion.core.action_library import ActionLibrary
from streamdeck_companion.core.actions import ActionDefinition
from streamdeck_companion.core.property_inspector import FieldType, PropertyInspector
from streamdeck_companion.core.registry import ActionRegistry


class ActionLibraryAndInspectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ActionRegistry()
        self.registry.register(
            ActionDefinition(
                id="windows.hotkey",
                name="Hotkey",
                description="Send a keyboard shortcut",
                category="Windows",
                parameters={
                    "keys": {"type": "hotkey", "label": "Keys", "required": True},
                },
            )
        )
        self.registry.register(
            ActionDefinition(
                id="ha.service",
                name="Home Assistant Service",
                category="Home Assistant",
                parameters={
                    "entity": {"type": "entity", "label": "Entity", "required": True},
                    "service": {
                        "type": "select",
                        "label": "Service",
                        "options": ["toggle", "turn_on", "turn_off"],
                    },
                },
            )
        )

    def test_library_searches_metadata_and_category(self) -> None:
        library = ActionLibrary(self.registry)
        self.assertEqual(library.categories(), ("Home Assistant", "Windows"))
        self.assertEqual([item.id for item in library.search("keyboard")], ["windows.hotkey"])
        self.assertEqual([item.id for item in library.search(category="Home Assistant")], ["ha.service"])

    def test_property_inspector_is_derived_from_action_parameters(self) -> None:
        schema = PropertyInspector(self.registry).schema("ha.service")
        self.assertEqual(schema.action_id, "ha.service")
        self.assertEqual([field.key for field in schema.fields], ["entity", "service"])
        self.assertEqual(schema.fields[0].field_type, FieldType.ENTITY)
        self.assertTrue(schema.fields[0].required)
        self.assertEqual(schema.fields[1].field_type, FieldType.SELECT)
        self.assertEqual(schema.fields[1].options, ("toggle", "turn_on", "turn_off"))

    def test_ui_config_fields_override_parameter_projection(self) -> None:
        registry = ActionRegistry()
        registry.register(
            ActionDefinition(
                id="custom",
                name="Custom",
                parameters={"raw": {"type": "text"}},
                ui_config={
                    "fields": [
                        {"key": "enabled", "label": "Enabled", "type": "boolean", "default": True}
                    ]
                },
            )
        )
        schema = PropertyInspector(registry).schema("custom")
        self.assertEqual(len(schema.fields), 1)
        self.assertEqual(schema.fields[0].key, "enabled")
        self.assertEqual(schema.fields[0].field_type, FieldType.BOOLEAN)
        self.assertTrue(schema.fields[0].default)


if __name__ == "__main__":
    unittest.main()
