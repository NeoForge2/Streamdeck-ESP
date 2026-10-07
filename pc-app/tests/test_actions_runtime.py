"""Compatibility tests for local actions routed through the V2 Core."""

import unittest
from unittest.mock import patch

from streamdeck_companion import actions


class LocalActionRuntimeTests(unittest.TestCase):
    def test_legacy_keys_action_is_dispatched_through_core(self):
        with patch.object(actions, "_send_keys") as send_keys:
            actions.run({"type": "keys", "target": ["ctrl", "s"]})
        send_keys.assert_called_once_with(["ctrl", "s"])

    def test_none_action_remains_a_noop(self):
        with patch.object(actions, "_send_keys") as send_keys:
            actions.run({"type": "none", "target": ""})
        send_keys.assert_not_called()

    def test_unknown_action_keeps_legacy_value_error_contract(self):
        with self.assertRaisesRegex(ValueError, "Type d'action inconnu"):
            actions.run({"type": "does_not_exist", "target": "x"})

    def test_missing_target_is_rejected_before_executor(self):
        with patch.object(actions, "_send_keys") as send_keys:
            with self.assertRaises(ValueError):
                actions.run({"type": "keys", "target": []})
        send_keys.assert_not_called()


if __name__ == "__main__":
    unittest.main()
