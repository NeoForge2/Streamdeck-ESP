import unittest

from streamdeck_companion.core.navigation import Folder, Page, Profile
from streamdeck_companion.core.navigation_session import NavigationSession


class NavigationSessionTests(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(
            id="main", name="Main",
            pages=(Page("home", "Home"), Page("apps", "Apps"), Page("games", "Games")),
            home_page_id="home",
            folders=(Folder("apps-folder", "Apps", "apps"), Folder("games-folder", "Games", "games", parent_id="apps-folder")),
        )

    def test_nested_folder_and_back(self):
        nav = NavigationSession(self.profile)
        nav.open_folder("apps-folder")
        self.assertEqual(nav.page_id, "apps")
        nav.open_folder("games-folder")
        self.assertEqual(nav.folder_id, "games-folder")
        nav.back()
        self.assertEqual(nav.folder_id, "apps-folder")
        nav.back()
        self.assertEqual(nav.page_id, "home")

    def test_rejects_folder_outside_current_parent(self):
        nav = NavigationSession(self.profile)
        with self.assertRaises(ValueError):
            nav.open_folder("games-folder")

    def test_page_navigation_and_home(self):
        nav = NavigationSession(self.profile)
        self.assertEqual(nav.next_page().page_id, "apps")
        self.assertEqual(nav.previous_page().page_id, "home")
        nav.go_to("games")
        self.assertEqual(nav.home().page_id, "home")
        self.assertEqual(nav.snapshot().history, ())


if __name__ == "__main__":
    unittest.main()
