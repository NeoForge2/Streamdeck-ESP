from __future__ import annotations

import unittest

from streamdeck_companion import actions as action_runner
from streamdeck_companion.v2_runtime_actions import register_navigation_action


class FakeNavigationRuntime:
    def __init__(self) -> None:
        self.calls = []

    def navigate(self, command: str, target: str | None = None) -> str:
        self.calls.append(("navigate", command, target))
        return target or command

    def open_folder(self, folder_id: str) -> str:
        self.calls.append(("folder", folder_id))
        return folder_id


class V2NavigationActionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = FakeNavigationRuntime()
        register_navigation_action(self.runtime)

    def tearDown(self) -> None:
        if "navigation" in action_runner._ENGINE.registry:
            action_runner._ENGINE.unregister("navigation")

    def test_page_commands_use_existing_legacy_action_path(self) -> None:
        action_runner.run({"type": "navigation", "target": "next"})
        action_runner.run({"type": "navigation", "target": "go_to:media"})
        self.assertEqual(
            self.runtime.calls,
            [("navigate", "next", None), ("navigate", "go_to", "media")],
        )

    def test_open_folder_routes_to_runtime(self) -> None:
        action_runner.run({"type": "navigation", "target": "open_folder:games"})
        self.assertEqual(self.runtime.calls, [("folder", "games")])

    def test_missing_target_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            action_runner.run({"type": "navigation", "target": ""})


if __name__ == "__main__":
    unittest.main()
