from __future__ import annotations

from tests.security.promptfoo_runner import majority_vote_by_scenario


def _case(description: str, success: bool) -> dict:
    return {"testCase": {"description": description}, "success": success}


def test_majority_vote_by_scenario_passes_on_strict_majority() -> None:
    report = {
        "results": {
            "results": [
                _case("scenario-a", True),
                _case("scenario-a", True),
                _case("scenario-a", False),
                _case("scenario-b", False),
                _case("scenario-b", False),
                _case("scenario-b", True),
            ],
        },
    }

    assert majority_vote_by_scenario(report) == {"scenario-a": True, "scenario-b": False}


def test_majority_vote_by_scenario_ties_fail_closed() -> None:
    report = {
        "results": {
            "results": [
                _case("scenario-a", True),
                _case("scenario-a", False),
            ],
        },
    }

    assert majority_vote_by_scenario(report) == {"scenario-a": False}
