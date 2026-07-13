from scripts.certify_content_factory_v2 import REQUIRED_STEPS


def test_certification_contains_every_required_release_plane() -> None:
    assert tuple(step.name for step in REQUIRED_STEPS) == (
        "architecture", "content_intelligence", "specialist_registry", "content_factory_v2",
        "runtime_resilience", "benchmark_release", "effectiveness", "load_release", "schemas",
    )


def test_certification_release_steps_use_public_make_targets() -> None:
    assert all(step.command[0] == "make" and len(step.command) == 2 for step in REQUIRED_STEPS)
