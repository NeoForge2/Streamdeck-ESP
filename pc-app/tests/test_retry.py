from __future__ import annotations

import unittest

from streamdeck_companion.retry import BackoffPolicy, RetryGate


class RetryGateTests(unittest.TestCase):
    def test_backoff_grows_and_caps(self) -> None:
        now = [10.0]
        gate = RetryGate(
            BackoffPolicy(initial_seconds=1, maximum_seconds=4, multiplier=2),
            clock=lambda: now[0],
        )
        self.assertEqual(gate.record_failure(), 1)
        self.assertFalse(gate.ready())
        now[0] = 11
        self.assertTrue(gate.ready())
        self.assertEqual(gate.record_failure(), 2)
        now[0] = 13
        self.assertEqual(gate.record_failure(), 4)
        now[0] = 17
        self.assertEqual(gate.record_failure(), 4)

    def test_success_resets_retry_budget(self) -> None:
        now = [0.0]
        gate = RetryGate(clock=lambda: now[0])
        gate.record_failure()
        self.assertEqual(gate.failures, 1)
        gate.record_success()
        self.assertEqual(gate.failures, 0)
        self.assertTrue(gate.ready())

    def test_invalid_policy_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            BackoffPolicy(initial_seconds=0)
        with self.assertRaises(ValueError):
            BackoffPolicy(initial_seconds=5, maximum_seconds=1)
        with self.assertRaises(ValueError):
            BackoffPolicy(multiplier=0.5)


if __name__ == "__main__":
    unittest.main()
