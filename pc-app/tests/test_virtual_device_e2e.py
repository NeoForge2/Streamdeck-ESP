from __future__ import annotations

import unittest

from streamdeck_companion.core.protocol import MessageType, ProtocolMessage
from streamdeck_companion.core.protocol_session import RetryPolicy
from streamdeck_companion.core.session import ProtocolSession
from streamdeck_companion.virtual_device import VirtualDeviceFaults, VirtualStreamdeckDevice


class VirtualDeviceE2ETests(unittest.TestCase):
    def test_control_messages_update_virtual_device_and_ack(self) -> None:
        device = VirtualStreamdeckDevice()
        session = ProtocolSession(device)
        device.set_receiver(session.receive)

        session.send(ProtocolMessage(MessageType.SET_PROFILE, {"profile_id": "gaming"}))
        session.send(ProtocolMessage(MessageType.SET_PAGE, {"page_id": "media"}))
        session.send(ProtocolMessage(MessageType.SET_BUTTON, {"slot_index": 4, "label": "OBS"}))
        session.send(ProtocolMessage(MessageType.SET_WIDGET, {"slot_index": 5, "type": "text"}))
        session.send(ProtocolMessage(MessageType.UPDATE_STATE, {"key": "ha:light.office", "value": "on"}))

        self.assertEqual(device.profile_id, "gaming")
        self.assertEqual(device.page_id, "media")
        self.assertEqual(device.buttons[4]["label"], "OBS")
        self.assertEqual(device.widgets[5]["type"], "text")
        self.assertEqual(device.states["ha:light.office"]["value"], "on")
        self.assertEqual(session.pending(), ())

    def test_virtual_device_can_emit_real_input_vocabulary(self) -> None:
        device = VirtualStreamdeckDevice()
        received = []
        device.set_receiver(received.append)

        device.emit_button(2)
        device.emit_button(3, hold=True)
        device.emit_encoder(1, direction="cw")
        device.emit_encoder(2, direction="ccw")
        device.emit_encoder(3)
        device.emit_touch(512, 300)

        self.assertEqual(
            [message.type for message in received],
            [
                MessageType.BUTTON_PRESS,
                MessageType.BUTTON_HOLD,
                MessageType.ENCODER_ROTATE,
                MessageType.ENCODER_ROTATE,
                MessageType.ENCODER_PRESS,
                MessageType.TOUCH,
            ],
        )

    def test_injected_device_error_resolves_pending_request(self) -> None:
        device = VirtualStreamdeckDevice(
            faults=VirtualDeviceFaults(error_responses_for={MessageType.SET_PAGE})
        )
        session = ProtocolSession(device)
        device.set_receiver(session.receive)
        session.send(ProtocolMessage(MessageType.SET_PAGE, {"page_id": "broken"}))
        self.assertEqual(session.pending(), ())

    def test_lost_ack_is_retried_and_then_resolved(self) -> None:
        now = [0.0]
        device = VirtualStreamdeckDevice(
            faults=VirtualDeviceFaults(drop_responses_for={MessageType.PING})
        )
        session = ProtocolSession(
            device,
            retry_policy=RetryPolicy(timeout_seconds=1.0, max_retries=1),
        )
        session.tracker._clock = lambda: now[0]
        device.set_receiver(session.receive)
        message = ProtocolMessage(MessageType.PING)

        session.send(message)
        self.assertEqual(len(session.pending()), 1)
        device.faults.drop_responses_for.clear()
        now[0] = 1.1
        self.assertEqual(session.retry_due(), (message,))
        self.assertEqual(session.pending(), ())
        self.assertEqual(device.sent_messages, [message, message])

    def test_disconnected_device_rejects_send_and_recovers(self) -> None:
        device = VirtualStreamdeckDevice()
        device.disconnect()
        with self.assertRaises(ConnectionError):
            device.send(ProtocolMessage(MessageType.PING))
        device.connect()
        device.send(ProtocolMessage(MessageType.PING))
        self.assertEqual(device.sent_messages[-1].type, MessageType.PING)

    def test_rejects_invalid_slot_payload(self) -> None:
        device = VirtualStreamdeckDevice()
        with self.assertRaises(ValueError):
            device.send(ProtocolMessage(MessageType.SET_BUTTON, {"slot_index": 99}))


if __name__ == "__main__":
    unittest.main()
