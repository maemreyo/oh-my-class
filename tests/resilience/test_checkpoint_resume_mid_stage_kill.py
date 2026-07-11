"""#123 (OPS-10): checkpoint-resume semantics, against the real local Postgres
and a real LangGraph `AsyncPostgresSaver` -- no mocks.

The last unverified acceptance item on #123: "a job that re-enters after a
mid-stage kill resumes from the last checkpoint rather than redoing completed
stages." Simulates a worker process dying right after the `setup_contract`
stage checkpoints (the compiled graph object is discarded entirely -- nothing
in-process survives), then a fresh worker rebuilds the graph against the same
checkpointer/thread_id and resumes. Asserts the already-completed stage is
NOT re-executed a second time.

`_setup_contract` and `_triage` are wrapped with call counters rather than
run for real -- `_triage`'s real implementation makes an external search call
that this sandbox can't reach, and this test's job is checkpoint-resume
semantics, not triage's own logic (that's `test_triage_stage_llm.py`'s job).
"""

from __future__ import annotations

from unittest.mock import patch

from packages.agents.teaching_pack import nodes
from packages.agents.teaching_pack.graph import build_teaching_pack_graph, teaching_pack_thread_config

DATABASE_URL = "postgresql://omc_dev:omc_dev@localhost:5432/oh_my_class"


async def test_resuming_after_a_mid_stage_kill_does_not_redo_the_completed_stage() -> None:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    run_id = "test-resilience-checkpoint-resume-1"
    setup_contract_calls = 0
    triage_calls = 0
    original_setup_contract = nodes._setup_contract

    def counting_setup_contract(state: object) -> object:
        nonlocal setup_contract_calls
        setup_contract_calls += 1
        return original_setup_contract(state)

    async def fake_triage(state: dict) -> dict:
        nonlocal triage_calls
        triage_calls += 1
        return {"contract": state.get("contract", {})}

    try:
        async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
            await checkpointer.setup()
            config = teaching_pack_thread_config(run_id)
            initial_state = {
                "run_id": run_id,
                "raw_request": "Build a lesson about photosynthesis",
                "contract": {
                    "raw_request": "Build a lesson about photosynthesis",
                    "class_info": {"grade": 5},
                },
            }

            with (
                patch.object(nodes, "_setup_contract", counting_setup_contract),
                patch.object(nodes, "_triage", fake_triage),
            ):
                # Worker A: runs setup_contract, checkpoints, then "dies" --
                # interrupt_after simulates the kill happening right after the
                # stage's side effects/checkpoint commit, before the next stage.
                worker_a_graph = build_teaching_pack_graph(
                    checkpointer=checkpointer, interrupt_after=["setup_contract"],
                )
                result_a = await worker_a_graph.ainvoke(initial_state, config)
                assert setup_contract_calls == 1
                assert triage_calls == 0
                assert result_a.get("completed_stages") == [nodes.StageEnum.SETUP_CONTRACT]

                # Worker B: a brand-new graph object (nothing from worker A's
                # process survives) resumes on the same checkpointer/thread_id.
                worker_b_graph = build_teaching_pack_graph(
                    checkpointer=checkpointer, interrupt_after=["triage"],
                )
                result_b = await worker_b_graph.ainvoke(None, config)

                # The already-checkpointed stage was NOT redone; only the
                # next (not-yet-completed) stage advanced.
                assert setup_contract_calls == 1, "setup_contract re-ran after resume"
                assert triage_calls == 1
                assert result_b.get("completed_stages") == [
                    nodes.StageEnum.SETUP_CONTRACT,
                    nodes.StageEnum.TRIAGE,
                ]
    finally:
        import psycopg

        with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
            conn.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (run_id,))
            conn.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (run_id,))
            conn.execute("DELETE FROM checkpoints WHERE thread_id = %s", (run_id,))
