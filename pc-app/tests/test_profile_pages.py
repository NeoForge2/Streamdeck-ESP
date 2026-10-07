from __future__ import annotations

import unittest

from streamdeck_companion import profile_pages, profiles


class ProfilePagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = profiles.default_profile()
        self.profile["library"] = [
            {
                "id": "lib-light",
                "label": "Light",
                "icon": "",
                "icon_char": "",
                "type": "bouton",
                "action": {"type": "home_assistant", "target": {"domain": "light", "service": "toggle"}},
                "ha_entity": "light.office",
                "show_light_color": False,
            }
        ]
        self.profile["slots"][0]["library_id"] = "lib-light"

    def test_legacy_profile_exposes_home_without_mutation(self) -> None:
        descriptors = profile_pages.page_descriptors(self.profile)
        self.assertEqual(descriptors, ({"id": "home", "name": "Accueil", "home": True},))
        self.assertNotIn("pages", self.profile)

    def test_extra_page_shares_library_and_has_independent_slots(self) -> None:
        page = profile_pages.new_page("Media", page_id="media")
        page["slots"][1]["library_id"] = "lib-light"
        self.profile["pages"] = [page]

        descriptors = profile_pages.page_descriptors(self.profile)
        self.assertEqual([item["id"] for item in descriptors], ["home", "media"])
        self.assertTrue(profile_pages.resolve_page_slot(self.profile, "home", 0)["visible"])
        media_slot = profile_pages.resolve_page_slot(self.profile, "media", 1)
        self.assertTrue(media_slot["visible"])
        self.assertEqual(media_slot["library_id"], "lib-light")
        self.assertFalse(profile_pages.resolve_page_slot(self.profile, "media", 0)["visible"])

    def test_duplicate_page_id_is_rejected(self) -> None:
        self.profile["home_page_id"] = "main"
        self.profile["pages"] = [{"id": "main", "name": "Duplicate", "slots": []}]
        with self.assertRaises(profile_pages.ProfilePageError):
            profile_pages.page_descriptors(self.profile)

    def test_unknown_page_and_empty_name_fail(self) -> None:
        with self.assertRaises(profile_pages.ProfilePageError):
            profile_pages.page_slots(self.profile, "missing")
        with self.assertRaises(profile_pages.ProfilePageError):
            profile_pages.new_page("   ")


if __name__ == "__main__":
    unittest.main()
