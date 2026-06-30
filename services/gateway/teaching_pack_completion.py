from __future__ import annotations

from uuid import uuid4

from services.gateway.models import RunStatus
from services.gateway.outcome_delivery import OutcomeDeliverySink, OutcomeDeliveryWriteError
from services.gateway.teaching_pack_export_writer import (
    FileSystemTeachingPackExportWriter,
    RendererAdapterSnapshotRenderer,
    TeachingPackExportWriter,
    TeachingPackSnapshotRenderer,
)
from services.gateway.teaching_pack_models import TeachingPackEventVisibility
from services.gateway.teaching_pack_snapshot_store import ArtifactSnapshotCreate
from services.gateway.teaching_pack_store import (
    TeachingPackEventCreate,
    TeachingPackGateCreate,
    TeachingPackStatusTransition,
)
from services.gateway.teaching_pack_types import JsonObject, JsonValue, RunId

from .teaching_pack_executor_types import TeachingPackFailureStore, TeachingPackNotificationSink


class TeachingPackCompletionRecorder:
    def __init__(
        self,
        store: TeachingPackFailureStore,
        renderer: TeachingPackSnapshotRenderer | None = None,
        export_writer: TeachingPackExportWriter | None = None,
        notifications: TeachingPackNotificationSink | None = None,
        outcome_delivery: OutcomeDeliverySink | None = None,
    ) -> None:
        self._store = store
        self._renderer = renderer or RendererAdapterSnapshotRenderer()
        self._export_writer = export_writer or FileSystemTeachingPackExportWriter(
            renderer=self._renderer,
        )
        self._notifications = notifications
        self._outcome_delivery = outcome_delivery

    async def persist_completion(self, run_id: RunId, state: JsonObject) -> None:
        gate_payload = _content_gate_payload(state)
        if gate_payload is not None:
            await self._persist_content_gate(run_id, gate_payload)
            return
        recovery_route = _quality_recovery_route(state)
        if recovery_route is not None:
            await self._persist_quality_recovery(run_id, recovery_route, state)
            return
        if _has_export_evidence(state):
            run = await self._store.get_run_by_id(run_id)
            exported_files = await self._export_writer.write_exports(run_id, state)
            exported_file_values: list[JsonValue] = [str(file_path) for file_path in exported_files]
            completed_payload: JsonObject = {"exported_files": exported_file_values}
            await self._store.transition_status(TeachingPackStatusTransition(
                run_id=run_id,
                status=RunStatus.EXPORTING,
                stage="export_finalize",
                reason="export_started",
            ))
            await self._store.transition_status(TeachingPackStatusTransition(
                run_id=run_id,
                status=RunStatus.COMPLETED,
                stage=None,
                reason="completed",
            ))
            await self._store.write_event(TeachingPackEventCreate(
                run_id=run_id,
                event_name="teaching_pack.run.completed",
                visibility=TeachingPackEventVisibility.TEACHER,
                payload=completed_payload,
            ))
            if self._notifications is not None and run is not None:
                await self._notifications.notify_completed(run_id, run.teacher_id)
            if self._outcome_delivery is not None and run is not None:
                try:
                    await self._outcome_delivery.record_post_export_delivery(
                        run_id,
                        run.teacher_id,
                        state,
                    )
                except OutcomeDeliveryWriteError:
                    await self._store.write_event(TeachingPackEventCreate(
                        run_id=run_id,
                        event_name="teaching_pack.outcome_delivery.failed",
                        visibility=TeachingPackEventVisibility.INTERNAL,
                        payload={"reason": "outcome_delivery_write_failed"},
                    ))
            return
        await self._store.transition_status(TeachingPackStatusTransition(
            run_id=run_id,
            status=RunStatus.FAILED,
            stage=None,
            reason="missing_export_evidence",
        ))
        await self._store.write_event(TeachingPackEventCreate(
            run_id=run_id,
            event_name="teaching_pack.run.failed",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={"error": "V2 graph completed without export evidence"},
        ))

    async def _persist_content_gate(self, run_id: RunId, gate_payload: JsonObject) -> None:
        for snapshot in _rendered_snapshots(gate_payload):
            content_json = _json_object(snapshot.get("content_json"))
            rendered_html = await self._renderer.render(content_json)
            await self._store.create_snapshot(ArtifactSnapshotCreate(
                snapshot_id=str(snapshot["snapshot_id"]),
                run_id=run_id,
                artifact_id=str(snapshot["artifact_id"]),
                artifact_type=str(snapshot["artifact_type"]),
                content_json=content_json,
                rendered_html=rendered_html,
                student_rendered_html=None,
                renderer_version=str(snapshot.get("renderer_version", "renderer-adapter")),
                template_version=str(snapshot.get("template_version", "eta-agent-renderer")),
                theme_version=str(snapshot.get("theme_version", "default")),
            ))
        gate_id = f"gate-{uuid4()}"
        await self._store.open_gate(TeachingPackGateCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="content_approval",
            payload={"gate_id": gate_id, **gate_payload},
        ))
        await self._store.transition_status(TeachingPackStatusTransition(
            run_id=run_id,
            status=RunStatus.AWAITING_APPROVAL,
            stage="content_approval",
            reason="content_approval",
        ))
        await self._store.write_event(TeachingPackEventCreate(
            run_id=run_id,
            event_name="teaching_pack.content_approval.opened",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={"gate_id": gate_id, "snapshot_ids": gate_payload.get("snapshot_ids", [])},
        ))

    async def _persist_quality_recovery(
        self,
        run_id: RunId,
        recovery_route: str,
        state: JsonObject,
    ) -> None:
        await self._store.transition_status(TeachingPackStatusTransition(
            run_id=run_id,
            status=_recovery_status(recovery_route),
            stage=recovery_route,
            reason=f"quality_recovery:{recovery_route}",
        ))
        recovery_payload: JsonObject = {
            "route": recovery_route,
            "issues": _quality_issues(state),
        }
        await self._store.write_event(TeachingPackEventCreate(
            run_id=run_id,
            event_name="teaching_pack.quality_recovery.started",
            visibility=TeachingPackEventVisibility.INTERNAL,
            payload=recovery_payload,
        ))


def _has_export_evidence(state: JsonObject) -> bool:
    exported_files = state.get("exported_files")
    return isinstance(exported_files, list) and len(exported_files) > 0


def _quality_recovery_route(state: JsonObject) -> str | None:
    value = state.get("quality_recovery_route")
    if isinstance(value, str) and value:
        return value
    return None


def _quality_issues(state: JsonObject) -> list[JsonValue]:
    values = state.get("quality_issues")
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def _recovery_status(recovery_route: str) -> RunStatus:
    _ = recovery_route
    return RunStatus.PLANNING


def _content_gate_payload(state: JsonObject) -> JsonObject | None:
    interrupt_values = state.get("__interrupt__")
    if isinstance(interrupt_values, list) and interrupt_values:
        value = _interrupt_value(interrupt_values[0])
        if value.get("gate") == "content_approval":
            return value
    return None


def _interrupt_value(interrupt_data: object) -> JsonObject:
    if isinstance(interrupt_data, dict):
        value = interrupt_data.get("value", interrupt_data)
        return _json_object(value)
    value = getattr(interrupt_data, "value", {})
    return _json_object(value)


def _rendered_snapshots(gate_payload: JsonObject) -> list[JsonObject]:
    values = gate_payload.get("rendered_snapshots")
    if not isinstance(values, list):
        return []
    return [_json_object(value) for value in values if isinstance(value, dict)]


def _json_object(value: object) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}
