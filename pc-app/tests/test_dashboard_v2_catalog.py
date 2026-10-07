from __future__ import annotations

import unittest

from streamdeck_companion.dashboard_v2_catalog import build_dashboard_action_catalog


class DashboardV2CatalogTests(unittest.TestCase):
    def test_catalog_exposes_library_and_property_inspector_metadata(self) -> None:
        catalog = build_dashboard_action_catalog()
        by_id = {item["id"]: item for item in catalog["actions"]}

        self.assertIn("Windows", catalog["categories"])
        self.assertIn("Streamdeck", catalog["categories"])
        self.assertIn("home_assistant", by_id)
        self.assertIn("multi_action", by_id)
        self.assertIn("navigation", by_id)
        self.assertEqual(by_id["launch"]["fields"][0]["key"], "target")
        self.assertIn("press", by_id["navigation"]["triggers"])
        self.assertEqual(by_id["multi_action"]["inputs"], ("button",))
        self.assertEqual(by_id["app_volume"]["inputs"], ("encoder",))
        self.assertIn("encoder", by_id["keys"]["inputs"])


if __name__ == "__main__":
    unittest.main()
