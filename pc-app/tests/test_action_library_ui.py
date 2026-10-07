from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ActionLibraryUiTests(unittest.TestCase):
    def test_base_template_loads_action_library(self) -> None:
        template = (ROOT / "streamdeck_companion" / "templates" / "base.html").read_text(encoding="utf-8")
        self.assertIn("action-library.js", template)

    def test_library_uses_v2_catalog_with_search_filter_and_drag_drop(self) -> None:
        script = (ROOT / "streamdeck_companion" / "static" / "action-library.js").read_text(encoding="utf-8")
        self.assertIn('/api/v2/action-catalog', script)
        self.assertIn('dataset.actionLibrarySearch', script)
        self.assertIn('dataset.actionLibraryCategory', script)
        self.assertIn('application/x-streamdeck-action', script)
        self.assertIn('dragstart', script)
        self.assertIn('drop', script)
        self.assertIn('modal-action-type', script)


if __name__ == "__main__":
    unittest.main()
