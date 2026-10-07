from __future__ import annotations

import unittest

from streamdeck_companion.navigation_legacy import profile_from_legacy
from streamdeck_companion.profile_folders import ProfileFolderError, folder_descriptors, new_folder
from streamdeck_companion.profile_pages import new_page


class ProfileFolderTests(unittest.TestCase):
    def _profile(self):
        return {
            "name": "Gaming",
            "slots": [],
            "library": [],
            "pages": [new_page("Games", page_id="games"), new_page("Racing", page_id="racing")],
            "folders": [
                new_folder("Games", "games", folder_id="games-folder", icon="gamepad", theme="dark"),
                new_folder(
                    "Racing",
                    "racing",
                    folder_id="racing-folder",
                    parent_id="games-folder",
                    show_back=True,
                ),
            ],
        }

    def test_nested_folders_are_projected_without_mutation(self) -> None:
        profile = self._profile()
        core = profile_from_legacy(profile)
        child = core.folder("racing-folder")
        self.assertEqual(child.parent_id, "games-folder")
        self.assertEqual(child.page_id, f"{core.id}:racing")
        self.assertTrue(child.metadata["show_back"])
        self.assertEqual(core.folder("games-folder").metadata["theme"], "dark")
        self.assertEqual(profile["folders"][1]["parent_id"], "games-folder")

    def test_unknown_page_is_rejected(self) -> None:
        profile = self._profile()
        profile["folders"].append(new_folder("Broken", "missing", folder_id="broken"))
        with self.assertRaises(ProfileFolderError):
            folder_descriptors(profile)

    def test_cycles_are_rejected(self) -> None:
        profile = self._profile()
        profile["folders"][0]["parent_id"] = "racing-folder"
        with self.assertRaises(ProfileFolderError):
            folder_descriptors(profile)


if __name__ == "__main__":
    unittest.main()
