from __future__ import annotations

import unittest

from streamdeck_companion.esphome_slot_projection import (
    SlotProjectionError,
    project_button_payload,
    project_widget_payload,
)


class ESPHomeSlotProjectionTests(unittest.TestCase):
    def test_button_projection_forces_button_type_and_maps_optional_fields(self) -> None:
        projection = project_button_payload(
            {
                "slot_index": 4,
                "label": "OBS",
                "icon": "videocam",
                "visible": True,
                "grid": {"col": 2, "row": 1, "colspan": 2, "rowspan": 1},
                "color": "#112233",
            }
        )
        self.assertEqual(projection.slot_index, 4)
        self.assertEqual(projection.slot_type, "bouton")
        self.assertEqual(projection.grid, "2,1,2,1")
        self.assertEqual(projection.color, "#112233")

    def test_widget_projection_accepts_bar_and_text(self) -> None:
        self.assertEqual(project_widget_payload({"slot_index": 0, "type": "barre", "value": "42"}).slot_type, "barre")
        self.assertEqual(project_widget_payload({"slot_index": 1, "type": "texte", "value": "CPU"}).slot_type, "texte")

    def test_invalid_slot_and_widget_type_fail_explicitly(self) -> None:
        with self.assertRaises(SlotProjectionError):
            project_button_payload({"slot_index": 36})
        with self.assertRaises(SlotProjectionError):
            project_widget_payload({"slot_index": 0, "type": "bouton"})

    def test_grid_and_visibility_are_validated(self) -> None:
        with self.assertRaises(SlotProjectionError):
            project_widget_payload({"slot_index": 0, "type": "texte", "visible": "yes"})
        with self.assertRaises(SlotProjectionError):
            project_widget_payload({"slot_index": 0, "type": "texte", "grid": {"colspan": 0}})


if __name__ == "__main__":
    unittest.main()
