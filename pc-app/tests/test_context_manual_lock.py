from __future__ import annotations

import unittest

from streamdeck_companion.core.context import ContextEngine, ContextRule, ContextSnapshot


class ContextManualLockTests(unittest.TestCase):
    def test_locked_manual_override_survives_clear_until_forced(self) -> None:
        engine = ContextEngine("default", (ContextRule("obs", process="obs64.exe"),))
        engine.set_manual_override("manual", locked=True)
        engine.resolve(ContextSnapshot(process="obs64.exe"))
        self.assertEqual(engine.clear_manual_override(), "manual")
        self.assertTrue(engine.manual_locked)
        self.assertEqual(engine.clear_manual_override(force=True), "obs")
        self.assertFalse(engine.manual_locked)

    def test_lock_requires_existing_manual_override(self) -> None:
        engine = ContextEngine("default")
        engine.set_manual_lock(True)
        self.assertFalse(engine.manual_locked)

    def test_restore_previous_respects_lock(self) -> None:
        engine = ContextEngine("default", (ContextRule("obs", process="obs64.exe"),))
        engine.resolve(ContextSnapshot(process="obs64.exe"))
        engine.set_manual_override("manual", locked=True)
        self.assertEqual(engine.restore_previous_automatic(), "manual")
        self.assertEqual(engine.restore_previous_automatic(force=True), "default")


if __name__ == "__main__":
    unittest.main()
