from __future__ import annotations

from pathlib import Path

ROUTERS_DIR = Path(__file__).resolve().parents[1] / "routers"


def test_unit_routes_are_not_registered_before_adr017_unit_runtime_exists() -> None:
    unit_route_files = sorted(ROUTERS_DIR.glob("*unit*.py"))

    assert unit_route_files == []
