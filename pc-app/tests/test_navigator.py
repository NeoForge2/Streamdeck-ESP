from __future__ import annotations

import unittest

from streamdeck_companion.core.navigation import Folder, Page, Profile
from streamdeck_companion.core.navigator import NavigationError, Navigator


class NavigatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = Profile(
            id="default",
            name="Default",
            pages=(
                Page(id="home", name="Home"),
                Page(id="media", name="Media"),
                Page(id="lights", name="Lights"),
            ),
            home_page_id="home",
            folders=(
                Folder(id="controls", name="Controls", page_id="media"),
                Folder(id="room", name="Room", page_id="lights", parent_id="controls"),
            ),
        )

    def test_starts_on_home_page(self) -> None:
        navigator = Navigator(self.profile)
        self.assertEqual(navigator.current_page.id, "home")
        self.assertFalse(navigator.can_go_back)

    def test_next_previous_and_wrap(self) -> None:
        navigator = Navigator(self.profile)
        self.assertEqual(navigator.next().id, "media")
        self.assertEqual(navigator.next().id, "lights")
        self.assertEqual(navigator.next().id, "home")
        self.assertEqual(navigator.previous().id, "lights")

    def test_go_to_back_and_home(self) -> None:
        navigator = Navigator(self.profile)
        navigator.go_to("media")
        navigator.go_to("lights")
        self.assertTrue(navigator.can_go_back)
        self.assertEqual(navigator.back().id, "media")
        self.assertEqual(navigator.home().id, "home")

    def test_open_nested_folder_and_path(self) -> None:
        navigator = Navigator(self.profile)
        self.assertEqual(navigator.open_folder("room").id, "lights")
        self.assertEqual([folder.id for folder in navigator.folder_path("room")], ["controls", "room"])

    def test_unknown_targets_fail_explicitly(self) -> None:
        navigator = Navigator(self.profile)
        with self.assertRaises(NavigationError):
            navigator.go_to("missing")
        with self.assertRaises(NavigationError):
            navigator.open_folder("missing")

    def test_reset_profile_clears_history(self) -> None:
        navigator = Navigator(self.profile)
        navigator.go_to("media")
        replacement = Profile(
            id="gaming",
            name="Gaming",
            pages=(Page(id="game-home", name="Game Home"),),
            home_page_id="game-home",
        )
        self.assertEqual(navigator.reset_profile(replacement).id, "game-home")
        self.assertFalse(navigator.can_go_back)


if __name__ == "__main__":
    unittest.main()
