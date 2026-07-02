from __future__ import annotations

from services.gateway.main import app
from services.gateway.routers import unit_runs


def test_unit_routes_are_registered_with_adr017_unit_runtime() -> None:
    included_unit_prefixes = {
        route.include_context.prefix
        for route in app.routes
        if getattr(route, "original_router", None) is unit_runs.router
    }
    unit_route_paths = {route.path for route in unit_runs.router.routes if hasattr(route, "path")}

    assert unit_runs.router.routes != []
    assert included_unit_prefixes == {"/teaching-packs"}
    assert "/units/{parent_run_id}" in unit_route_paths
    assert "/units/{parent_run_id}/status" in unit_route_paths
