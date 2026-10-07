from __future__ import annotations

import unittest

from streamdeck_companion.controls_legacy import controls_from_legacy_profile
from streamdeck_companion.core.events import InputKind
from streamdeck_companion.core.triggers import Trigger


class LegacyControlAdapterTests(unittest.TestCase):
    def test_button_keeps_primary_action_and_adds_optional_triggers(self) -> None:
        profile = {
            "slots": [
                {"library_id": "lib-1", "grid": {"col": 0, "row": 0, "colspan": 1, "rowspan": 1}}
            ],
            "library": [
                {
                    "id": "lib-1",
                    "action": {"type": "media", "target": "play_pause"},
                    "trigger_actions": {
                        "double_press": {"type": "media", "target": "next"},
                        "hold": {"type": "url", "target": "https://example.test"},
                    },
                    "ha_entity": "light.salon",
                }
            ],
            "encoders": [],
        }
        controls = controls_from_legacy_profile(profile)
        button = controls[0]
        self.assertEqual(button.kind, InputKind.BUTTON)
        self.assertEqual(button.actions[Trigger.PRESS].action_id, "media")
        self.assertEqual(button.actions[Trigger.DOUBLE_PRESS].parameters["target"], "next")
        self.assertEqual(button.actions[Trigger.HOLD].action_id, "url")
        self.assertEqual(button.state_key, "ha:light.salon")

    def test_encoder_maps_all_supported_legacy_trigger_keys(self) -> None:
        profile = {
            "slots": [],
            "library": [],
            "encoders": [
                {
                    "clockwise": {"type": "media", "target": "vol_up"},
                    "anticlockwise": {"type": "media", "target": "vol_down"},
                    "press": {"type": "media", "target": "mute"},
                    "hold": {"type": "url", "target": "https://example.test/device"},
                    "release": {"type": "media", "target": "play_pause"},
                    "state_key": "audio:master-volume",
                    "display": {"kind": "bar"},
                }
            ],
        }
        controls = controls_from_legacy_profile(profile)
        encoder = next(control for control in controls if control.kind == InputKind.ENCODER)
        self.assertEqual(encoder.actions[Trigger.ROTATE_CW].parameters["target"], "vol_up")
        self.assertEqual(encoder.actions[Trigger.ROTATE_CCW].parameters["target"], "vol_down")
        self.assertEqual(encoder.actions[Trigger.PRESS].parameters["target"], "mute")
        self.assertEqual(encoder.actions[Trigger.HOLD].action_id, "url")
        self.assertEqual(encoder.actions[Trigger.RELEASE].parameters["target"], "play_pause")
        self.assertEqual(encoder.state_key, "audio:master-volume")
        self.assertEqual(encoder.context["display"], {"kind": "bar"})


if __name__ == "__main__":
    unittest.main()
