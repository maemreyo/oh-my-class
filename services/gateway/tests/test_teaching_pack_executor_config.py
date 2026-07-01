from __future__ import annotations

from dataclasses import dataclass, field

from langgraph.types import Command

from packages.agents.teaching_pack.graph import LangGraphRunnableConfig
from services.gateway.teaching_pack_executor import (
    TeachingPackExecutor,
    TeachingPackResumeJob,
    TeachingPackStartJob,
)
from services.gateway.teaching_pack_types import JsonObject, RunId


@dataclass(slots=True)
class CapturingGraph:
    configs: list[LangGraphRunnableConfig] = field(default_factory=list)

    async def ainvoke(
        self,
        input_data: JsonObject | Command[tuple[()]],
        *,
        config: LangGraphRunnableConfig,
    ) -> JsonObject:
        _ = input_data
        self.configs.append(config)
        return {"run_id": "run-config"}


@dataclass(slots=True)
class NoopTaskGroup:
    def start_soon(self, func, *args) -> None:
        _ = (func, args)


async def test_start_job_passes_fanout_max_concurrency_to_langgraph(monkeypatch) -> None:
    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    monkeypatch.setenv("TEACHING_PACK_DEFAULT_ARTIFACT_PARALLELISM", "4")
    graph = CapturingGraph()
    executor = TeachingPackExecutor(graph, NoopTaskGroup())

    await executor.run_start_job(TeachingPackStartJob(
        run_id=RunId("run-config"),
        initial_state={"run_id": "run-config"},
    ))

    assert graph.configs == [{"configurable": {"thread_id": "run-config"}, "max_concurrency": 4}]


async def test_resume_job_preserves_thread_id_and_fanout_cap(monkeypatch) -> None:
    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    monkeypatch.setenv("TEACHING_PACK_DEFAULT_ARTIFACT_PARALLELISM", "2")
    graph = CapturingGraph()
    executor = TeachingPackExecutor(graph, NoopTaskGroup())

    await executor.run_resume_job(TeachingPackResumeJob(
        run_id=RunId("run-resume"),
        gate_response_id="gate-response",
        resume_payload={"action": "approve"},
    ))

    assert graph.configs == [{"configurable": {"thread_id": "run-resume"}, "max_concurrency": 2}]
