from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from streamdeck_companion.profile_archive import ProfileArchiveError, export_profile, import_profile, migrate_profile


class ProfileArchiveTests(unittest.TestCase):
    def test_round_trip_profile_pages_folders_widgets_actions_and_assets(self) -> None:
        profile = {
            "name": "Gaming",
            "settings": {"theme": "dark"},
            "library": [{"id": "launch", "action": {"type": "launch", "target": "game.exe"}}],
            "slots": [{"library_id": "launch", "grid": {"col": 0, "row": 0, "colspan": 1, "rowspan": 1}}],
            "pages": [{"id": "media", "name": "Media", "slots": []}],
            "folders": [{"id": "tools", "name": "Tools", "page_id": "media"}],
            "widgets": [{"id": "fps", "type": "text", "state_key": "system:fps"}],
        }
        assets = {"icons/game.png": b"png-bytes"}
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "gaming.streamdeck"
            exported = export_profile(profile, destination, assets=assets)
            imported, imported_assets = import_profile(exported)
        self.assertEqual(imported, migrate_profile(profile))
        self.assertEqual(imported_assets, assets)

    def test_extension_is_added_automatically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = export_profile({"name": "Default"}, Path(tmp) / "backup")
            self.assertEqual(result.suffix, ".streamdeck")
            self.assertTrue(result.exists())

    def test_rejects_unsupported_archive_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.streamdeck"
            with ZipFile(path, "w") as archive:
                archive.writestr(
                    "manifest.json",
                    json.dumps({"format": "streamdeck-esp-profile", "version": 999}),
                )
                archive.writestr("profile.json", "{}")
            with self.assertRaises(ProfileArchiveError):
                import_profile(path)

    def test_rejects_unsafe_asset_path_on_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ProfileArchiveError):
                export_profile({"name": "Default"}, Path(tmp) / "bad.streamdeck", assets={"../secret": b"x"})


if __name__ == "__main__":
    unittest.main()
