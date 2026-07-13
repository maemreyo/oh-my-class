from pathlib import Path


def _make_recipe(target: str) -> str:
    lines = Path("Makefile").read_text(encoding="utf-8").splitlines()
    marker = f"{target}:"
    start = next(index for index, line in enumerate(lines) if line.startswith(marker))
    recipe: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("	") or (recipe and not line.strip()):
            recipe.append(line)
            continue
        break
    return "\n".join(recipe)


def test_runtime_resilience_gate_validates_migrations_before_database_work() -> None:
    recipe = _make_recipe("check-runtime-resilience")
    contract_position = recipe.index("uv run pytest tests/test_alembic_revision_contract.py -q")
    compose_position = recipe.index("$(COMPOSE) up -d --wait db")
    migrate_position = recipe.index("$(MAKE) migrate")
    runtime_test_position = recipe.index("services/gateway/tests/test_run_event_outbox.py")
    assert "$${OMC_RUNTIME_DB_READY:-0}" in recipe
    assert contract_position < compose_position < migrate_position < runtime_test_position


def test_python_ci_checks_revision_contract_before_migration() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    test_job = workflow.split("  test-python:", 1)[1].split("  test-typescript:", 1)[0]
    service_position = test_job.index("postgres:")
    contract_position = test_job.index("pytest tests/test_alembic_revision_contract.py -q")
    migration_position = test_job.index("alembic upgrade head")
    gate_position = test_job.index("make check-runtime-resilience")
    assert 'OMC_RUNTIME_DB_READY: "1"' in test_job
    assert "postgres:16-alpine" in test_job
    assert service_position < contract_position < migration_position < gate_position
