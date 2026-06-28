"""Protocol ports for Teaching Pack runtime adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping

    from common.contracts.artifact_workflow import ArtifactWorkflowState
    from common.contracts.quality import ArtifactQualityReport
    from common.contracts.research_brief import ResearchBrief
    from common.contracts.run_contract import JsonObject, RunContract
    from packages.agents.teaching_pack.stages import TeachingPackStage


class RunStore(Protocol):
    """Persistence boundary for run metadata."""

    async def mark_stage_started(self, run_id: str, stage: TeachingPackStage) -> None:
        """Persist that a stage has started."""
        ...

    async def mark_stage_completed(self, run_id: str, stage: TeachingPackStage) -> None:
        """Persist that a stage has completed."""
        ...


class EventWriter(Protocol):
    """Persistence boundary for compact run events."""

    async def write_stage_event(
        self,
        run_id: str,
        stage: TeachingPackStage,
        event_name: str,
    ) -> None:
        """Persist a compact stage event."""
        ...


class ArtifactSnapshotStore(Protocol):
    """Persistence boundary for rendered artifact snapshots."""

    async def has_snapshot(self, content_hash: str) -> bool:
        """Return whether a snapshot already exists for a content hash."""
        ...


class RunExecutor(Protocol):
    """Control-plane boundary for queued run execution."""

    async def enqueue_start(self, run_id: str) -> None:
        """Queue a run start request."""
        ...

    async def enqueue_resume(self, run_id: str, gate_response_id: str) -> None:
        """Queue a run resume request."""
        ...


class TeachingPackGraph(Protocol):
    """LangGraph execution boundary for Teaching Pack orchestration."""

    async def ainvoke(
        self,
        input_state: JsonObject,
        config: Mapping[str, object],
    ) -> JsonObject:
        """Execute or resume the pipeline graph."""
        ...


class LLMTransport(Protocol):
    """Boundary for structured model calls used by pipeline stages."""

    async def complete_json(
        self,
        *,
        run_id: str,
        agent_name: str,
        prompt: str,
        schema_name: str,
    ) -> JsonObject:
        """Return parsed JSON from the configured LLM gateway."""
        ...


class SearchFetchClient(Protocol):
    """Boundary for search and source-fetch providers."""

    async def collect_research(self, contract: RunContract) -> ResearchBrief:
        """Return a compact, cited research brief for a run contract."""
        ...


class ArtifactRenderer(Protocol):
    """Boundary for rendering artifact content into standalone HTML."""

    async def render_snapshot(
        self,
        *,
        artifact: JsonObject,
        theme: str,
    ) -> str:
        """Render one artifact into standalone HTML for preview/export."""
        ...


class NotificationChannel(Protocol):
    """Boundary for teacher/admin notifications."""

    async def notify(
        self,
        *,
        run_id: str,
        teacher_id: str,
        event_type: str,
        payload: JsonObject,
    ) -> None:
        """Deliver a pipeline notification through an adapter."""
        ...


class QualityGate(Protocol):
    """Boundary for deterministic and model-assisted artifact quality checks."""

    async def evaluate(self, state: ArtifactWorkflowState) -> ArtifactQualityReport:
        """Evaluate one artifact workflow state."""
        ...
