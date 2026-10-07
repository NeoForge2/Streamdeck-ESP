"""Register V2 dashboard API routes on the existing Flask application."""

from __future__ import annotations

from typing import Any, Protocol

from .dashboard_v2_api import dashboard_action_catalog_payload


class FlaskLike(Protocol):
    def add_url_rule(self, rule: str, endpoint: str, view_func: Any, **options: Any) -> Any: ...


ENDPOINT = "v2_action_catalog"
ROUTE = "/api/v2/action-catalog"


def register_dashboard_v2_routes(app: FlaskLike) -> None:
    """Register V2 routes exactly once on the historical Flask app."""
    view_functions = getattr(app, "view_functions", {})
    if ENDPOINT in view_functions:
        return
    app.add_url_rule(ROUTE, ENDPOINT, dashboard_action_catalog_payload, methods=["GET"])
