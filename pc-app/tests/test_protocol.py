"""Tests for the transport-neutral PC <-> device protocol contract."""

import unittest

from streamdeck_companion.core.protocol import (
    MessageType,
    PROTOCOL_VERSION,
    ProtocolError,
    ProtocolMessage,
    ping,
    sync,
)


class ProtocolMessageTests(unittest.TestCase):
    def test_round_trip_preserves_envelope(self):
        original = ProtocolMessage(
            MessageType.SET_PAGE,
            {"profile_id": "gaming", "page_id": "main"},
            message_id="msg-123",
        )
        restored = ProtocolMessage.from_dict(original.to_dict())
        self.assertEqual(restored, original)

    def test_ack_references_original_message(self):
        request = ProtocolMessage(MessageType.PING, message_id="ping-1")
        response = request.ack({"device_time": 42})
        self.assertEqual(response.type, MessageType.ACK)
        self.assertEqual(response.reply_to, "ping-1")
        self.assertEqual(response.protocol_version, PROTOCOL_VERSION)

    def test_error_response_contains_code_and_reply(self):
        request = ProtocolMessage(MessageType.SYNC, message_id="sync-1")
        response = request.error("invalid_state", "State payload is invalid")
        self.assertEqual(response.type, MessageType.ERROR)
        self.assertEqual(response.reply_to, "sync-1")
        self.assertEqual(response.payload["code"], "invalid_state")

    def test_control_response_requires_reply_to(self):
        with self.assertRaises(ProtocolError):
            ProtocolMessage(MessageType.ACK)

    def test_unknown_protocol_version_is_rejected(self):
        with self.assertRaises(ProtocolError):
            ProtocolMessage.from_dict({
                "protocol_version": PROTOCOL_VERSION + 1,
                "message_id": "future",
                "type": "ping",
                "payload": {},
            })

    def test_unknown_message_type_is_rejected(self):
        with self.assertRaises(ProtocolError):
            ProtocolMessage.from_dict({
                "protocol_version": PROTOCOL_VERSION,
                "message_id": "bad-type",
                "type": "teleport",
                "payload": {},
            })

    def test_helpers_build_expected_messages(self):
        self.assertEqual(ping().type, MessageType.PING)
        message = sync({"revision": 5})
        self.assertEqual(message.type, MessageType.SYNC)
        self.assertEqual(message.payload["revision"], 5)


if __name__ == "__main__":
    unittest.main()
