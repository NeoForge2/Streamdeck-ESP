"""Integration-style tests across the V2 compatibility adapters.

These tests intentionally exercise several layers together while the runtime
still uses the historical ESPHome transport and dashboard profile format.
"""

import unittest

from streamdeck_companion.core import MessageType
from streamdeck_companion.device_event_runtime import resolve_esphome_action
from streamdeck_companion.device_events import translate_esphome_event
from streamdeck_companion.device_protocol import input_event_to_protocol


ACTION_ENTITY = "Bouton d'action ecran"
ENCODER_ENTITIES = ["Encodeur 1 - evenement", "Encodeur 2 - evenement", "Encodeur 3 - evenement"]


def _profile():
    return {
        "slots": [
            {"library_id": "launch-browser", "grid": {"col": 0, "row": 0, "colspan": 1, "rowspan": 1}},
        ],
        "library": [
            {
                "id": "launch-browser",
                "type": "bouton",
                "action": {"type": "url", "target": "https://example.test"},
            },
        ],
        "encoders": [
            {
                "clockwise": {"type": "media", "target": "vol_up"},
                "anticlockwise": {"type": "media", "target": "vol_down"},
                "press": {"type": "media", "target": "mute"},
            }
        ],
    }


class V2CompatibilityFlowTests(unittest.TestCase):
    def test_button_event_keeps_action_and_gains_protocol_message(self):
        event = translate_esphome_event(
            ACTION_ENTITY,
            "action_1",
            action_entity_name=ACTION_ENTITY,
            encoder_entity_names=ENCODER_ENTITIES,
        )
        self.assertIsNotNone(event)

        protocol_message = input_event_to_protocol(event)
        action = resolve_esphome_action(
            _profile(),
            ACTION_ENTITY,
            "action_1",
            action_entity_name=ACTION_ENTITY,
            encoder_entity_names=ENCODER_ENTITIES,
        )

        self.assertEqual(protocol_message.type, MessageType.BUTTON_PRESS)
        self.assertEqual(protocol_message.payload["slot_index"], 0)
        self.assertEqual(action, {"type": "url", "target": "https://example.test"})

    def test_encoder_rotation_keeps_action_and_gains_directional_message(self):
        event = translate_esphome_event(
            ENCODER_ENTITIES[0],
            "clockwise",
            action_entity_name=ACTION_ENTITY,
            encoder_entity_names=ENCODER_ENTITIES,
        )
        self.assertIsNotNone(event)

        protocol_message = input_event_to_protocol(event)
        action = resolve_esphome_action(
            _profile(),
            ENCODER_ENTITIES[0],
            "clockwise",
            action_entity_name=ACTION_ENTITY,
            encoder_entity_names=ENCODER_ENTITIES,
        )

        self.assertEqual(protocol_message.type, MessageType.ENCODER_ROTATE)
        self.assertEqual(protocol_message.payload["direction"], "cw")
        self.assertEqual(action, {"type": "media", "target": "vol_up"})

    def test_special_ui_event_stays_outside_generic_pipeline(self):
        event = translate_esphome_event(
            ACTION_ENTITY,
            "close_color_mode",
            action_entity_name=ACTION_ENTITY,
            encoder_entity_names=ENCODER_ENTITIES,
        )
        action = resolve_esphome_action(
            _profile(),
            ACTION_ENTITY,
            "close_color_mode",
            action_entity_name=ACTION_ENTITY,
            encoder_entity_names=ENCODER_ENTITIES,
        )

        self.assertIsNone(event)
        self.assertIsNone(action)


if __name__ == "__main__":
    unittest.main()
