from __future__ import annotations

import unittest

from streamdeck_companion.device_event_runtime import resolve_esphome_action


ACTION_ENTITY = "Bouton d'action ecran"
ENCODER_ENTITIES = ["Encodeur 1 - evenement", "Encodeur 2 - evenement", "Encodeur 3 - evenement"]


class DeviceEventRuntimePageTests(unittest.TestCase):
    def test_same_button_resolves_action_from_selected_page(self) -> None:
        profile = {
            "slots": [{"library_id": "home-action", "grid": {"col": 0, "row": 0, "colspan": 1, "rowspan": 1}}],
            "pages": [
                {
                    "id": "media",
                    "name": "Media",
                    "slots": [
                        {"library_id": "media-action", "grid": {"col": 0, "row": 0, "colspan": 1, "rowspan": 1}}
                    ],
                }
            ],
            "library": [
                {"id": "home-action", "action": {"type": "hotkey", "target": "ctrl+h"}},
                {"id": "media-action", "action": {"type": "media", "target": "play_pause"}},
            ],
            "encoders": [],
        }

        home_action = resolve_esphome_action(
            profile,
            ACTION_ENTITY,
            "action_1",
            action_entity_name=ACTION_ENTITY,
            encoder_entity_names=ENCODER_ENTITIES,
            page_id="home",
        )
        media_action = resolve_esphome_action(
            profile,
            ACTION_ENTITY,
            "action_1",
            action_entity_name=ACTION_ENTITY,
            encoder_entity_names=ENCODER_ENTITIES,
            page_id="media",
        )

        self.assertEqual(home_action, {"type": "hotkey", "target": "ctrl+h"})
        self.assertEqual(media_action, {"type": "media", "target": "play_pause"})


if __name__ == "__main__":
    unittest.main()
