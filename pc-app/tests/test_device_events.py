"""Tests for the ESPHome-to-Core input event adapter."""

import unittest

from streamdeck_companion.core import InputKind, Trigger
from streamdeck_companion.device_events import legacy_encoder_direction, translate_esphome_event


ACTION_ENTITY = "Bouton d'action ecran"
ENCODERS = ["Encodeur 1 - evenement", "Encodeur 2 - evenement", "Encodeur 3 - evenement"]


class DeviceEventAdapterTests(unittest.TestCase):
    def test_button_press_is_translated_to_generic_input_event(self):
        event = translate_esphome_event(
            ACTION_ENTITY,
            "action_12",
            action_entity_name=ACTION_ENTITY,
            encoder_entity_names=ENCODERS,
        )
        self.assertEqual(event.source_id, "button:12")
        self.assertEqual(event.kind, InputKind.BUTTON)
        self.assertEqual(event.trigger, Trigger.PRESS)
        self.assertEqual(event.metadata["slot_index"], 11)

    def test_button_hold_is_translated_without_changing_firmware_vocabulary(self):
        event = translate_esphome_event(
            ACTION_ENTITY,
            "hold_2",
            action_entity_name=ACTION_ENTITY,
            encoder_entity_names=ENCODERS,
        )
        self.assertEqual(event.source_id, "button:2")
        self.assertEqual(event.trigger, Trigger.HOLD)

    def test_encoder_rotation_is_translated(self):
        event = translate_esphome_event(
            ENCODERS[1],
            "clockwise",
            action_entity_name=ACTION_ENTITY,
            encoder_entity_names=ENCODERS,
        )
        self.assertEqual(event.source_id, "encoder:2")
        self.assertEqual(event.kind, InputKind.ENCODER)
        self.assertEqual(event.trigger, Trigger.ROTATE_CW)
        self.assertEqual(legacy_encoder_direction(event.trigger), "clockwise")

    def test_special_display_event_is_left_to_existing_device_handler(self):
        event = translate_esphome_event(
            ACTION_ENTITY,
            "close_ha_popup",
            action_entity_name=ACTION_ENTITY,
            encoder_entity_names=ENCODERS,
        )
        self.assertIsNone(event)


if __name__ == "__main__":
    unittest.main()
