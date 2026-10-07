from __future__ import annotations

import unittest

from streamdeck_companion.core.action_wheel import ActionWheel, ActionWheelItem
from streamdeck_companion.core.actions import ActionCommand


class ActionWheelTests(unittest.TestCase):
    def _wheel(self) -> ActionWheel:
        return ActionWheel(
            (
                ActionWheelItem("play", "Play/Pause", ActionCommand("media.play_pause")),
                ActionWheelItem("next", "Next", ActionCommand("media.next")),
                ActionWheelItem("mute", "Mute", ActionCommand("media.mute")),
            )
        )

    def test_rotation_wraps_in_both_directions(self) -> None:
        wheel = self._wheel()
        self.assertEqual(wheel.rotate(-1).selected.id, "mute")
        self.assertEqual(wheel.rotate(1).selected.id, "play")
        self.assertEqual(wheel.rotate(4).selected.id, "next")

    def test_touch_selection_and_activation(self) -> None:
        wheel = self._wheel()
        wheel.select("mute")
        self.assertEqual(wheel.activate().action_id, "media.mute")

    def test_empty_wheel_is_invalid(self) -> None:
        with self.assertRaises(ValueError):
            ActionWheel(())


if __name__ == "__main__":
    unittest.main()
