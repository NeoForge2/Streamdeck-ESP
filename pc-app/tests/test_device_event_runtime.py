"""Tests for generic input event resolution against current profile data."""

import unittest

from streamdeck_companion.core import InputEvent, InputKind, Trigger
from streamdeck_companion.device_event_runtime import resolve_esphome_action, resolve_legacy_action


ACTION_ENTITY = "Bouton d'action ecran"
ENCODER_ENTITIES = ["Encodeur 1 - evenement", "Encodeur 2 - evenement", "Encodeur 3 - evenement"]


class DeviceEventRuntimeTests(unittest.TestCase):
    def _profile(self):
        return {
            "slots": [
                {"library_id": "lib-1", "grid": {"col": 0, "row": 0, "colspan": 1, "rowspan": 1}},
            ],
            "library": [
                {"id": "lib-1", "type": "bouton", "action": {"type": "url", "target": "https://example.test"}},
            ],
            "encoders": [
                {
                    "clockwise": {"type": "media", "target": "vol_up"},
                    "anticlockwise": {"type": "media", "target": "vol_down"},
                    "press": {"type": "media", "target": "mute"},
                }
            ],
        }

    def test_button_event_resolves_slot_action(self):
        event = InputEvent("button:1", InputKind.BUTTON, Trigger.PRESS, {"slot_index": 0})
        action = resolve_legacy_action(self._profile(), event)
        self.assertEqual(action, {"type": "url", "target": "https://example.test"})

    def test_encoder_rotation_resolves_current_direction_key(self):
        event = InputEvent("encoder:1", InputKind.ENCODER, Trigger.ROTATE_CW, {"encoder_index": 0})
        self.assertEqual(resolve_legacy_action(self._profile(), event), {"type": "media", "target": "vol_up"})

    def test_encoder_press_resolves_press_action(self):
        event = InputEvent("encoder:1", InputKind.ENCODER, Trigger.PRESS, {"encoder_index": 0})
        self.assertEqual(resolve_legacy_action(self._profile(), event), {"type": "media", "target": "mute"})

    def test_invalid_metadata_is_ignored(self):
        event = InputEvent("button:x", InputKind.BUTTON, Trigger.PRESS, {"slot_index": "bad"})
        self.assertIsNone(resolve_legacy_action(self._profile(), event))

    def test_touch_event_has_no_legacy_action_mapping(self):
        event = InputEvent("touch:main", InputKind.TOUCH, Trigger.PRESS, {"x": 1, "y": 2})
        self.assertIsNone(resolve_legacy_action(self._profile(), event))

    def test_esphome_button_bridge_resolves_same_action(self):
        action = resolve_esphome_action(
            self._profile(),
            ACTION_ENTITY,
            "action_1",
            action_entity_name=ACTION_ENTITY,
            encoder_entity_names=ENCODER_ENTITIES,
        )
        self.assertEqual(action, {"type": "url", "target": "https://example.test"})

    def test_esphome_encoder_bridge_resolves_same_action(self):
        action = resolve_esphome_action(
            self._profile(),
            ENCODER_ENTITIES[0],
            "clockwise",
            action_entity_name=ACTION_ENTITY,
            encoder_entity_names=ENCODER_ENTITIES,
        )
        self.assertEqual(action, {"type": "media", "target": "vol_up"})

    def test_special_ui_event_does_not_enter_generic_action_path(self):
        action = resolve_esphome_action(
            self._profile(),
            ACTION_ENTITY,
            "close_ha_popup",
            action_entity_name=ACTION_ENTITY,
            encoder_entity_names=ENCODER_ENTITIES,
        )
        self.assertIsNone(action)


if __name__ == "__main__":
    unittest.main()
