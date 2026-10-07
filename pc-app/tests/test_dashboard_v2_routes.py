from __future__ import annotations

import unittest

from streamdeck_companion.dashboard_v2_routes import ENDPOINT, ROUTE, register_dashboard_v2_routes


class FakeApp:
    def __init__(self) -> None:
        self.view_functions: dict[str, object] = {}
        self.rules: list[tuple[str, str, tuple[str, ...]]] = []

    def add_url_rule(self, rule, endpoint, view_func, **options):
        self.view_functions[endpoint] = view_func
        self.rules.append((rule, endpoint, tuple(options.get("methods") or ())))


class DashboardV2RoutesTests(unittest.TestCase):
    def test_registers_catalog_route_once(self) -> None:
        app = FakeApp()
        register_dashboard_v2_routes(app)
        register_dashboard_v2_routes(app)

        self.assertEqual(app.rules, [(ROUTE, ENDPOINT, ("GET",))])
        payload = app.view_functions[ENDPOINT]()
        self.assertIn("actions", payload)
        self.assertIn("choices", payload)


if __name__ == "__main__":
    unittest.main()
