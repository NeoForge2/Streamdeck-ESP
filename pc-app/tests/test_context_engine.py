from __future__ import annotations

import unittest

from streamdeck_companion.core.context import ContextEngine, ContextRule, ContextSnapshot


class ContextEngineTests(unittest.TestCase):
    def test_highest_priority_matching_rule_wins(self) -> None:
        engine = ContextEngine(
            "default",
            (
                ContextRule("development", process="code.exe", priority=10),
                ContextRule("debug", process="code.exe", window_title_contains="debug", priority=50),
            ),
        )
        selected = engine.resolve(ContextSnapshot(process="CODE.EXE", window_title="Matrix - Debug Console"))
        self.assertEqual(selected, "debug")
        self.assertEqual(engine.previous_automatic_profile_id, "default")

    def test_default_profile_is_used_when_nothing_matches(self) -> None:
        engine = ContextEngine("default", (ContextRule("obs", process="obs64.exe"),))
        self.assertEqual(engine.resolve(ContextSnapshot(process="explorer.exe")), "default")

    def test_manual_override_locks_profile_until_cleared(self) -> None:
        engine = ContextEngine("default", (ContextRule("obs", process="obs64.exe"),))
        engine.set_manual_override("manual")
        self.assertEqual(engine.resolve(ContextSnapshot(process="obs64.exe")), "manual")
        self.assertEqual(engine.clear_manual_override(), "obs")

    def test_restore_previous_automatic_profile(self) -> None:
        engine = ContextEngine(
            "default",
            (
                ContextRule("obs", process="obs64.exe", priority=10),
                ContextRule("game", game="my-game", priority=20),
            ),
        )
        engine.resolve(ContextSnapshot(process="obs64.exe"))
        engine.resolve(ContextSnapshot(game="my-game"))
        self.assertEqual(engine.restore_previous_automatic(), "obs")

    def test_window_title_match_is_case_insensitive(self) -> None:
        engine = ContextEngine(
            "default",
            (ContextRule("meeting", window_title_contains="meeting", priority=5),),
        )
        self.assertEqual(engine.resolve(ContextSnapshot(window_title="Weekly MEETING - Team")), "meeting")

    def test_rule_requires_at_least_one_matcher(self) -> None:
        with self.assertRaises(ValueError):
            ContextRule("invalid")


if __name__ == "__main__":
    unittest.main()
