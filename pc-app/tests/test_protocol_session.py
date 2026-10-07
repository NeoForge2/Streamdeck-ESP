"""Tests for transport-neutral protocol reliability tracking."""

import unittest

from streamdeck_companion.core.protocol import MessageType, ProtocolMessage
from streamdeck_companion.core.protocol_session import (
    RequestTimeoutError,
    RequestTracker,
    RetryPolicy,
)


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class RequestTrackerTests(unittest.TestCase):
    def test_ack_resolves_pending_request(self):
        clock = FakeClock()
        tracker = RequestTracker(clock=clock)
        request = ProtocolMessage(MessageType.PING, message_id="ping-1")
        tracker.track(request)

        resolved = tracker.resolve(request.ack())

        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.message, request)
        self.assertEqual(tracker.pending(), ())

    def test_request_is_retried_after_timeout(self):
        clock = FakeClock()
        tracker = RequestTracker(RetryPolicy(timeout_seconds=1.0, max_retries=2), clock=clock)
        request = ProtocolMessage(MessageType.SYNC, message_id="sync-1")
        tracker.track(request)

        clock.advance(1.1)
        self.assertEqual(tracker.due_retries(), (request,))
        self.assertEqual(tracker.pending()[0].retries, 1)

    def test_retry_budget_exhaustion_raises_timeout(self):
        clock = FakeClock()
        tracker = RequestTracker(RetryPolicy(timeout_seconds=1.0, max_retries=1), clock=clock)
        request = ProtocolMessage(MessageType.PING, message_id="ping-timeout")
        tracker.track(request)

        clock.advance(1.1)
        self.assertEqual(tracker.due_retries(), (request,))
        clock.advance(1.1)
        with self.assertRaises(RequestTimeoutError):
            tracker.due_retries()
        self.assertEqual(tracker.pending(), ())

    def test_non_control_message_does_not_resolve_pending(self):
        tracker = RequestTracker()
        request = ProtocolMessage(MessageType.PING, message_id="ping-2")
        tracker.track(request)
        self.assertIsNone(tracker.resolve(ProtocolMessage(MessageType.DEVICE_STATUS)))
        self.assertEqual(len(tracker.pending()), 1)

    def test_control_response_cannot_be_tracked(self):
        tracker = RequestTracker()
        request = ProtocolMessage(MessageType.PING, message_id="ping-3")
        with self.assertRaises(ValueError):
            tracker.track(request.ack())


if __name__ == "__main__":
    unittest.main()
