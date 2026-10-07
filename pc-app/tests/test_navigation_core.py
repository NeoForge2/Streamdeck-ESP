"""Tests for the V2 profile/page/folder domain model."""

import unittest

from streamdeck_companion.core import Folder, GridRect, Page, Placement, Profile


class NavigationModelTests(unittest.TestCase):
    def test_profile_supports_pages_and_nested_folders(self):
        home = Page(
            id="page-home",
            name="Accueil",
            placements=(Placement("slot-1", "lib-1", GridRect(0, 0, 2, 1)),),
        )
        media = Page(id="page-media", name="Media")
        profile = Profile(
            id="profile-default",
            name="Defaut",
            pages=(home, media),
            home_page_id="page-home",
            folders=(
                Folder(id="folder-media", name="Media", page_id="page-media"),
                Folder(
                    id="folder-music",
                    name="Musique",
                    page_id="page-media",
                    parent_id="folder-media",
                ),
            ),
        )

        self.assertEqual(profile.page("page-home"), home)
        self.assertEqual(profile.folder("folder-music").parent_id, "folder-media")
        self.assertEqual(home.placements[0].grid.colspan, 2)

    def test_home_page_must_exist(self):
        with self.assertRaisesRegex(ValueError, "home_page_id"):
            Profile(
                id="profile-default",
                name="Defaut",
                pages=(Page(id="page-home", name="Accueil"),),
                home_page_id="missing",
            )

    def test_folder_must_reference_existing_page(self):
        with self.assertRaisesRegex(ValueError, "unknown page"):
            Profile(
                id="profile-default",
                name="Defaut",
                pages=(Page(id="page-home", name="Accueil"),),
                home_page_id="page-home",
                folders=(Folder(id="folder-1", name="Invalide", page_id="missing"),),
            )

    def test_grid_rejects_invalid_span(self):
        with self.assertRaisesRegex(ValueError, "span"):
            GridRect(0, 0, 0, 1)


if __name__ == "__main__":
    unittest.main()
