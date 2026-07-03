from __future__ import annotations

from pathlib import Path

from packages.agents.testing import INVARIANT_REGISTRY


ROOT = Path(__file__).resolve().parents[1]


def test_registered_invariants_have_existing_test_files() -> None:
    missing = [
        invariant
        for invariant in INVARIANT_REGISTRY
        if not (ROOT / invariant.test_path).exists()
    ]

    assert missing == []


def test_registered_invariant_tests_are_not_skipped_or_xfailed() -> None:
    offenders: list[str] = []
    for invariant in INVARIANT_REGISTRY:
        source = (ROOT / invariant.test_path).read_text(encoding="utf-8")
        if "skip(" in source or "skipif(" in source or "xfail(" in source:
            offenders.append(invariant.test_path)

    assert offenders == []


def test_registry_has_unique_invariant_ids() -> None:
    invariant_ids = [invariant.invariant_id for invariant in INVARIANT_REGISTRY]

    assert len(invariant_ids) == len(set(invariant_ids))


def test_registry_covers_all_documented_hard_invariants() -> None:
    invariant_ids = {invariant.invariant_id for invariant in INVARIANT_REGISTRY}

    assert invariant_ids == {f"INVARIANT-{index:02d}" for index in range(1, 11)}
