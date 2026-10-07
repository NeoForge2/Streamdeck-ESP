from __future__ import annotations

import unittest

from streamdeck_companion.navigation_legacy import profile_from_legacy


class MultiPageProjectionTests(unittest.TestCase):
    def test_backward_compatible_extra_pages_are_projected(self) -> None:
        legacy = {
            "name": "Default",
            "library": [{"id": "lib-a"}, {"id": "lib-b"}],
            "slots": [
                {
                    "library_id": "lib-a",
                    "grid": {"col": 0, "row": 0, "colspan": 1, "rowspan": 1},
                }
            ],
            "pages": [
                {
                    "id": "media",
                    "name": "Media",
                    "slots": [
                        {
                            "library_id": "lib-b",
                            "grid": {"col": 3, "row": 1, "colspan": 2, "rowspan": 1},
                        }
                    ],
                }
            ],
        }

        profile = profile_from_legacy(legacy)

        self.assertEqual(len(profile.pages), 2)
        self.assertEqual([page.name for page in profile.pages], ["Accueil", "Media"])
        self.assertEqual(profile.pages[1].metadata["legacy_page_id"], "media")
        self.assertEqual(profile.pages[1].placements[0].content_id, "lib-b")
        self.assertEqual(profile.pages[1].placements[0].grid.col, 3)
        self.assertEqual(legacy["pages"][0]["slots"][0]["library_id"], "lib-b")


if __name__ == "__main__":
    unittest.main()
