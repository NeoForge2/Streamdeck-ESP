from __future__ import annotations

import random
import string
import unittest

from streamdeck_companion.core.protocol import PROTOCOL_VERSION, ProtocolError, ProtocolMessage


class ProtocolFuzzTests(unittest.TestCase):
    def test_random_malformed_messages_never_escape_unexpected_exceptions(self) -> None:
        rng = random.Random(5601)
        alphabet = string.ascii_letters + string.digits + "_-"

        for _ in range(5_000):
            payload = {
                "protocol_version": rng.choice([None, -1, 0, 2, "1", PROTOCOL_VERSION]),
                "message_id": "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 20))),
                "type": rng.choice([None, "", "unknown", "ping", "ack", "error", 42]),
                "payload": rng.choice([None, {}, [], "bad", {"value": rng.randrange(1000)}]),
                "reply_to": rng.choice([None, "", "parent"]),
            }
            try:
                ProtocolMessage.from_dict(payload)
            except ProtocolError:
                continue
            except Exception as exc:  # pragma: no cover - this is the property under test
                self.fail(f"unexpected exception type {type(exc).__name__}: {exc}")

    def test_random_valid_ping_roundtrips(self) -> None:
        rng = random.Random(850)
        for _ in range(2_000):
            message_id = f"msg-{rng.getrandbits(64):016x}"
            message = ProtocolMessage.from_dict(
                {
                    "protocol_version": PROTOCOL_VERSION,
                    "message_id": message_id,
                    "type": "ping",
                    "payload": {"nonce": rng.getrandbits(32)},
                }
            )
            self.assertEqual(ProtocolMessage.from_dict(message.to_dict()), message)


if __name__ == "__main__":
    unittest.main()
