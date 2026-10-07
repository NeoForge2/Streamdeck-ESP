from __future__ import annotations

from pathlib import Path
import unittest


class V2ProtocolWiringTests(unittest.TestCase):
    def test_v2_device_client_owns_live_port_session_and_retry_runtime(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "streamdeck_companion"
            / "v2_device_client.py"
        ).read_text(encoding="utf-8")

        self.assertIn("self.device_port = build_esphome_device_port(self)", source)
        self.assertIn("self.protocol_session = ProtocolSession(self.device_port)", source)
        self.assertIn("ProtocolRetryRuntime(self.protocol_session)", source)
        self.assertIn("self._protocol_retry_runtime.start()", source)
        self.assertIn("expect_response: bool | None = None", source)

    def test_v2_device_client_discovers_and_receives_firmware_ack(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "streamdeck_companion"
            / "v2_device_client.py"
        ).read_text(encoding="utf-8")

        self.assertIn("PROTOCOL_REQUEST_ENTITY_NAME", source)
        self.assertIn("PROTOCOL_ACK_ENTITY_NAME", source)
        self.assertIn("def schedule_protocol_request", source)
        self.assertIn("MessageType.ACK", source)
        self.assertIn("self.protocol_session.receive", source)

    def test_firmware_defines_ack_roundtrip_entities(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "firmware"
            / "protocol_v2.yaml"
        ).read_text(encoding="utf-8")

        self.assertIn('name: "Protocole V2 - requete"', source)
        self.assertIn('name: "Protocole V2 - acquittement"', source)
        self.assertIn("- text.set:", source)
        self.assertIn("value: !lambda 'return x;'", source)


if __name__ == "__main__":
    unittest.main()
