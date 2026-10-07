from __future__ import annotations

import unittest

from streamdeck_companion.core.protocol_session import RequestTimeoutError
from streamdeck_companion.protocol_retry_runtime import ProtocolRetryRuntime


class FakeSession:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls = 0
        self.error = error

    def retry_due(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return ()


class ProtocolRetryRuntimeTests(unittest.TestCase):
    def test_tick_checks_session_for_due_retries(self) -> None:
        session = FakeSession()
        runtime = ProtocolRetryRuntime(session, interval_seconds=0.1)  # type: ignore[arg-type]
        runtime.tick()
        self.assertEqual(session.calls, 1)

    def test_timeout_is_reported_without_killing_caller(self) -> None:
        seen: list[str] = []
        session = FakeSession(RequestTimeoutError("expired"))
        runtime = ProtocolRetryRuntime(
            session,  # type: ignore[arg-type]
            interval_seconds=0.1,
            on_timeout=lambda exc: seen.append(str(exc)),
        )
        runtime.tick()
        self.assertEqual(seen, ["expired"])

    def test_invalid_interval_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ProtocolRetryRuntime(FakeSession(), interval_seconds=0)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
