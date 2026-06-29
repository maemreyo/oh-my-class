from __future__ import annotations

from scripts.verify_frontend_api_contracts import main


def test_teaching_pack_frontend_api_contracts_match_backend() -> None:
    assert main() == 0
