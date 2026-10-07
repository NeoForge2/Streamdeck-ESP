from __future__ import annotations

import unittest

from streamdeck_companion.core.protocol import MessageType, ProtocolMessage
from streamdeck_companion.esphome_port_runtime import (
    RuntimePayloadError,
    build_esphome_device_port,
)


class FakeRuntime:
    connected = True

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def schedule_set_active_profile(self, name: str, timeout: float = 5.0) -> None:
        self.calls.append(("profile", name, timeout))

    def schedule_push(self, timeout: float = 5.0) -> None:
        self.calls.append(("sync", timeout))

    def schedule_navigation(
        self,
        command: str,
        target: str | None = None,
        timeout: float = 5.0,
    ) -> str:
        self.calls.append(("navigation", command, target, timeout))
        return target or command

    def schedule_slot_payload(self, kind: str, payload: dict, timeout: float = 5.0) -> None:
        self.calls.append(("slot", kind, dict(payload), timeout))

    def schedule_protocol_request(self, message_id: str, timeout: float = 5.0) -> None:
        self.calls.append(("ack_request", message_id, timeout))


class ESPHomePortRuntimeTests(unittest.TestCase):
    def test_set_profile_routes_to_thread_safe_runtime_then_ack_channel(self) -> None:
        runtime = FakeRuntime()
        port = build_esphome_device_port(runtime)
        message = ProtocolMessage(MessageType.SET_PROFILE, {"profile_name": "Gaming"})
        port.send(message)
        self.assertEqual(
            runtime.calls,
            [("profile", "Gaming", 5.0), ("ack_request", message.message_id, 5.0)],
        )

    def test_set_profile_accepts_profile_id_for_progressive_compatibility(self) -> None:
        runtime = FakeRuntime()
        port = build_esphome_device_port(runtime)
        message = ProtocolMessage(MessageType.SET_PROFILE, {"profile_id": "Bureau"})
        port.send(message)
        self.assertEqual(runtime.calls[0][:2], ("profile", "Bureau"))
        self.assertEqual(runtime.calls[1][0], "ack_request")

    def test_set_page_routes_to_v2_navigation_then_ack(self) -> None:
        runtime = FakeRuntime()
        port = build_esphome_device_port(runtime)
        message = ProtocolMessage(MessageType.SET_PAGE, {"page_id": "media"})
        port.send(message)
        self.assertEqual(runtime.calls[0], ("navigation", "go_to", "media", 5.0))
        self.assertEqual(runtime.calls[1], ("ack_request", message.message_id, 5.0))

    def test_set_button_routes_to_slot_runtime_then_ack(self) -> None:
        runtime = FakeRuntime()
        port = build_esphome_device_port(runtime)
        payload = {"slot_index": 2, "label": "OBS", "visible": True}
        message = ProtocolMessage(MessageType.SET_BUTTON, payload)
        port.send(message)
        self.assertEqual(runtime.calls[0], ("slot", "button", payload, 5.0))
        self.assertEqual(runtime.calls[1], ("ack_request", message.message_id, 5.0))

    def test_set_widget_routes_to_slot_runtime_then_ack(self) -> None:
        runtime = FakeRuntime()
        port = build_esphome_device_port(runtime)
        payload = {"slot_index": 3, "type": "barre", "value": "50"}
        message = ProtocolMessage(MessageType.SET_WIDGET, payload)
        port.send(message)
        self.assertEqual(runtime.calls[0], ("slot", "widget", payload, 5.0))
        self.assertEqual(runtime.calls[1], ("ack_request", message.message_id, 5.0))

    def test_sync_reuses_existing_full_push_then_ack(self) -> None:
        runtime = FakeRuntime()
        port = build_esphome_device_port(runtime)
        message = ProtocolMessage(MessageType.SYNC, {})
        port.send(message)
        self.assertEqual(runtime.calls[0], ("sync", 5.0))
        self.assertEqual(runtime.calls[1], ("ack_request", message.message_id, 5.0))

    def test_ping_uses_only_ack_roundtrip(self) -> None:
        runtime = FakeRuntime()
        port = build_esphome_device_port(runtime)
        message = ProtocolMessage(MessageType.PING)
        port.send(message)
        self.assertEqual(runtime.calls, [("ack_request", message.message_id, 5.0)])

    def test_invalid_runtime_payload_fails_before_ack(self) -> None:
        runtime = FakeRuntime()
        port = build_esphome_device_port(runtime)
        with self.assertRaises(RuntimePayloadError):
            port.send(ProtocolMessage(MessageType.SET_PAGE, {}))
        self.assertEqual(runtime.calls, [])


if __name__ == "__main__":
    unittest.main()
