"""Tests for Core runtime objects -> protocol adapters."""

import unittest

from streamdeck_companion.core import ActionState, InputEvent, InputKind, MessageType, StateValue, Trigger
from streamdeck_companion.device_protocol import input_event_to_protocol, state_value_to_protocol


class DeviceProtocolAdapterTests(unittest.TestCase):
    def test_button_press_maps_to_button_press_message(self):
        event = InputEvent("button:2", InputKind.BUTTON, Trigger.PRESS, {"slot_index": 1})
        message = input_event_to_protocol(event)
        self.assertEqual(message.type, MessageType.BUTTON_PRESS)
        self.assertEqual(message.payload["source_id"], "button:2")
        self.assertEqual(message.payload["slot_index"], 1)

    def test_button_hold_maps_to_button_hold_message(self):
        event = InputEvent("button:1", InputKind.BUTTON, Trigger.HOLD)
        self.assertEqual(input_event_to_protocol(event).type, MessageType.BUTTON_HOLD)

    def test_encoder_rotation_includes_direction(self):
        event = InputEvent("encoder:3", InputKind.ENCODER, Trigger.ROTATE_CCW, {"encoder_index": 2})
        message = input_event_to_protocol(event)
        self.assertEqual(message.type, MessageType.ENCODER_ROTATE)
        self.assertEqual(message.payload["direction"], "ccw")
        self.assertEqual(message.payload["encoder_index"], 2)

    def test_encoder_press_maps_to_press_message(self):
        event = InputEvent("encoder:1", InputKind.ENCODER, Trigger.PRESS)
        self.assertEqual(input_event_to_protocol(event).type, MessageType.ENCODER_PRESS)

    def test_touch_maps_to_touch_message(self):
        event = InputEvent("touch:main", InputKind.TOUCH, Trigger.PRESS, {"x": 100, "y": 200})
        message = input_event_to_protocol(event)
        self.assertEqual(message.type, MessageType.TOUCH)
        self.assertEqual(message.payload["x"], 100)
        self.assertEqual(message.payload["y"], 200)

    def test_state_value_maps_to_update_state_message(self):
        state = StateValue(
            key="ha:light.bureau",
            status=ActionState.ON,
            value="on",
            attributes={"brightness": 200},
            updated_at=123.5,
        )
        message = state_value_to_protocol(state)

        self.assertEqual(message.type, MessageType.UPDATE_STATE)
        self.assertEqual(message.payload["key"], "ha:light.bureau")
        self.assertEqual(message.payload["status"], "on")
        self.assertEqual(message.payload["value"], "on")
        self.assertEqual(message.payload["attributes"], {"brightness": 200})
        self.assertEqual(message.payload["updated_at"], 123.5)


if __name__ == "__main__":
    unittest.main()
