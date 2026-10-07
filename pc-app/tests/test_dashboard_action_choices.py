from __future__ import annotations

import unittest

from streamdeck_companion.dashboard_action_choices import action_choices, choice_ids, choice_labels
from streamdeck_companion.dashboard_v2_catalog import build_dashboard_action_catalog


class DashboardActionChoicesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = build_dashboard_action_catalog()

    def test_button_choices_are_derived_from_catalog(self) -> None:
        ids = choice_ids(self.catalog, "button")
        self.assertEqual(ids[0], "none")
        self.assertIn("keys", ids)
        self.assertIn("multi_action", ids)
        self.assertIn("navigation", ids)
        self.assertNotIn("app_volume", ids)
        self.assertNotIn("ha_adjust", ids)

    def test_encoder_choices_preserve_legacy_capabilities(self) -> None:
        ids = choice_ids(self.catalog, "encoder")
        self.assertEqual(ids[0], "none")
        self.assertIn("keys", ids)
        self.assertIn("launch", ids)
        self.assertIn("home_assistant", ids)
        self.assertIn("app_volume", ids)
        self.assertIn("ha_adjust", ids)
        self.assertNotIn("multi_action", ids)

    def test_labels_come_from_action_library(self) -> None:
        labels = choice_labels(self.catalog)
        self.assertEqual(labels["none"], "Aucune")
        self.assertEqual(labels["launch"], "Lancer une application")
        self.assertEqual(labels["navigation"], "Navigation Streamdeck")

    def test_invalid_input_kind_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            action_choices(self.catalog, "touch")


if __name__ == "__main__":
    unittest.main()
