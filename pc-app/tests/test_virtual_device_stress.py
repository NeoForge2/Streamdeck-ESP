from __future__ import annotations

import random
import unittest

from streamdeck_companion.core.protocol import MessageType, ProtocolMessage
from streamdeck_companion.core.session import ProtocolSession
from streamdeck_companion.virtual_device import VirtualStreamdeckDevice


class VirtualDeviceStressTests(unittest.TestCase):
    def test_ten_thousand_mixed_control_messages_leave_consistent_state(self) -> None:
        rng = random.Random(2211)
        device = VirtualStreamdeckDevice()
        session = ProtocolSession(device)
        device.set_receiver(session.receive)

        expected_buttons: dict[int, str] = {}
        expected_states: dict[str, int] = {}
        for index in range(10_000):
            if rng.random() < 0.55:
                slot = rng.randrange(36)
                label = f"action-{index}"
                expected_buttons[slot] = label
                session.send(
                    ProtocolMessage(
                        MessageType.SET_BUTTON,
                        {"slot_index": slot, "label": label},
                    )
                )
            else:
                state_index = rng.randrange(64)
                key = f"stress:{state_index}"
                expected_states[key] = index
                session.send(
                    ProtocolMessage(
                        MessageType.UPDATE_STATE,
                        {"key": key, "value": index},
                    )
                )

        self.assertEqual(session.pending(), ())
        self.assertEqual(len(device.sent_messages), 10_000)
        for slot, label in expected_buttons.items():
            self.assertEqual(device.buttons[slot]["label"], label)
        for key, value in expected_states.items():
            self.assertEqual(device.states[key]["value"], value)

    def test_twenty_thousand_input_events_preserve_order(self) -> None:
        device = VirtualStreamdeckDevice()
        received: list[ProtocolMessage] = []
        device.set_receiver(received.append)

        for index in range(20_000):
            if index % 3 == 0:
                device.emit_button(index % 36)
            elif index % 3 == 1:
                device.emit_encoder((index % 3) + 1, direction="cw")
            else:
                device.emit_touch(index % 1024, index % 600)

        self.assertEqual(len(received), 20_000)
        self.assertEqual(received[0].type, MessageType.BUTTON_PRESS)
        self.assertEqual(received[-1].type, MessageType.ENCODER_ROTATE)


if __name__ == "__main__":
    unittest.main()
