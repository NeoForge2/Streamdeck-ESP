"""Tests for projecting current profiles into the V2 navigation model."""

import unittest

from streamdeck_companion.navigation_legacy import profile_from_legacy


class LegacyNavigationAdapterTests(unittest.TestCase):
    def test_current_grid_becomes_home_page_without_mutation(self):
        legacy = {
            "name": "OBS",
            "trigger": {"process": "obs64.exe"},
            "slots": [
                {"library_id": "lib-scene", "grid": {"col": 2, "row": 1, "colspan": 2, "rowspan": 1}},
                {"library_id": None, "grid": {"col": 0, "row": 0, "colspan": 1, "rowspan": 1}},
            ],
        }

        profile = profile_from_legacy(legacy)

        self.assertEqual(profile.name, "OBS")
        self.assertEqual(profile.trigger, {"process": "obs64.exe"})
        self.assertEqual(len(profile.pages), 1)
        self.assertEqual(profile.home_page_id, profile.pages[0].id)
        self.assertEqual(len(profile.pages[0].placements), 1)
        placement = profile.pages[0].placements[0]
        self.assertEqual(placement.content_id, "lib-scene")
        self.assertEqual(placement.grid.col, 2)
        self.assertEqual(placement.grid.colspan, 2)
        self.assertEqual(legacy["slots"][0]["library_id"], "lib-scene")

    def test_profile_id_is_deterministic_from_current_name(self):
        first = profile_from_legacy({"name": "Default Profile", "slots": []})
        second = profile_from_legacy({"name": "Default Profile", "slots": []})
        self.assertEqual(first.id, second.id)


if __name__ == "__main__":
    unittest.main()
