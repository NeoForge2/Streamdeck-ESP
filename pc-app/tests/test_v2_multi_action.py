from __future__ import annotations

import unittest

from streamdeck_companion import actions as action_runner
from streamdeck_companion.v2_runtime_actions import register_multi_action


class FakeMultiActionRuntime:
    def __init__(self) -> None:
        self.calls = []

    def submit(self, definition_id: str, *, context=None):
        self.calls.append((definition_id, context))
        return {"definition_id": definition_id}


class V2MultiActionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = FakeMultiActionRuntime()
        register_multi_action(self.runtime)

    def tearDown(self) -> None:
        if "multi_action" in action_runner._ENGINE.registry:
            action_runner._ENGINE.unregister("multi_action")

    def test_legacy_multi_action_routes_to_runtime_submitter(self) -> None:
        action_runner.run({"type": "multi_action", "target": "morning"})
        self.assertEqual(self.runtime.calls, [("morning", None)])

    def test_missing_multi_action_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            action_runner.run({"type": "multi_action", "target": ""})


if __name__ == "__main__":
    unittest.main()
