from __future__ import annotations

import unittest

from streamdeck_companion.core.device import DeviceCapability
from streamdeck_companion.core.protocol import MessageType, ProtocolMessage
from streamdeck_companion.esphome_device_port import (
    ESPHomeDevicePort,
    STREAMDECK_ESP_DESCRIPTOR,
    UnsupportedDeviceMessageError,
)


class FakeClient:
    connected = True


class ESPHomeDevicePortTests(unittest.TestCase):
    def test_descriptor_matches_current_hardware(self) -> None:
        descriptor = STREAMDECK_ESP_DESCRIPTOR
        self.assertEqual(descriptor.display.width, 1024)
        self.assertEqual(descriptor.display.height, 600)
        self.assertEqual(descriptor.encoder_count, 3)
        self.assertTrue(descriptor.supports(DeviceCapability.TOUCH))
        self.assertTrue(descriptor.supports(DeviceCapability.ENCODERS))

    def test_connected_tracks_wrapped_client(self) -> None:
        client = FakeClient()
        port = ESPHomeDevicePort(client)
        self.assertTrue(port.connected)
        client.connected = False
        self.assertFalse(port.connected)

    def test_update_state_uses_injected_sender_without_ack_traffic(self) -> None:
        sent: list[dict[str, object]] = []
        acks: list[str] = []
        port = ESPHomeDevicePort(FakeClient(), state_sender=sent.append, ack_sender=acks.append)
        message = ProtocolMessage(
            MessageType.UPDATE_STATE,
            {"state_id": "device:streamdeck", "value": True},
        )
        port.send(message)
        self.assertEqual(sent, [{"state_id": "device:streamdeck", "value": True}])
        self.assertEqual(acks, [])

    def test_sync_acknowledges_only_after_sender_succeeds(self) -> None:
        calls: list[str] = []
        acks: list[str] = []
        message = ProtocolMessage(MessageType.SYNC, {})
        port = ESPHomeDevicePort(
            FakeClient(),
            sync_sender=lambda: calls.append("sync"),
            ack_sender=acks.append,
        )
        port.send(message)
        self.assertEqual(calls, ["sync"])
        self.assertEqual(acks, [message.message_id])

    def test_ping_is_device_roundtrip_marker(self) -> None:
        acks: list[str] = []
        message = ProtocolMessage(MessageType.PING)
        port = ESPHomeDevicePort(FakeClient(), ack_sender=acks.append)
        port.send(message)
        self.assertEqual(acks, [message.message_id])

    def test_ping_without_ack_channel_fails_explicitly(self) -> None:
        port = ESPHomeDevicePort(FakeClient())
        with self.assertRaises(UnsupportedDeviceMessageError):
            port.send(ProtocolMessage(MessageType.PING))

    def test_unsupported_message_fails_explicitly(self) -> None:
        port = ESPHomeDevicePort(FakeClient())
        with self.assertRaises(UnsupportedDeviceMessageError):
            port.send(ProtocolMessage(MessageType.SET_PAGE, {"page_id": "main"}))


if __name__ == "__main__":
    unittest.main()
