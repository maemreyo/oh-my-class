from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from packages.agents.teaching_pack.content_orchestrator import ArtifactContentStore
from services.gateway.models import RunStatus
from services.gateway.outcome_delivery import OutcomeDeliverySink, OutcomeDeliveryWriteError
from services.gateway.teaching_pack_export_store import ExportRecordCreate, TeachingPackExportStore
from services.gateway.teaching_pack_export_writer import (
    FileSystemTeachingPackExportWriter,
    RendererAdapterSnapshotRenderer,
    TeachingPackExportWriter,
    TeachingPackSnapshotRenderer,
    approved_snapshots_for_export,
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
        export_store: TeachingPackExportStore | None = None,
        content_store: ArtifactContentStore | None = None,
    ) -> None:
        self._store = store
        self._renderer = renderer or RendererAdapterSnapshotRenderer()
        self._export_writer = export_writer or FileSystemTeachingPackExportWriter(
            renderer=self._renderer,
        )
        self._notifications = notifications
        self._outcome_delivery = outcome_delivery
        self._export_store = export_store
        self._content_store = content_store

    async def persist_completion(self, run_id: RunId, state: JsonObject) -> None:
        content_update_event = _content_update_event(state)
        if content_update_event is not None:
            await self._store.write_event(TeachingPackEventCreate(
                run_id=run_id,
                event_name=str(content_update_event.get("event_name", "teaching_pack.content_version.created")),
                visibility=TeachingPackEventVisibility.TEACHER,
                payload=_json_object(content_update_event.get("payload")),
            ))
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
            export_state = await _hydrate_state_snapshots(state, self._content_store)
            exported_files = await self._export_writer.write_exports(run_id, export_state)
            if self._export_store is not None:
                approved_snapshots = approved_snapshots_for_export(state)
                for record in _export_records_from_files(run_id, exported_files, approved_snapshots):
                    await self._export_store.create_export_record(record)
            exported_file_values: list[JsonValue] = [str(file_path) for file_path in exported_files]
            completed_payload: JsonObject = {"exported_files": exported_file_values}
            auto_approval_payload = _auto_approval_payload(state)
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
            if auto_approval_payload is not None:
                await self._store.write_event(TeachingPackEventCreate(
                    run_id=run_id,
                    event_name="teaching_pack.content_approval.auto_approved",
                    visibility=TeachingPackEventVisibility.TEACHER,
                    payload=auto_approval_payload,
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
                except (OutcomeDeliveryWriteError, TimeoutError):
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
            content_json = await _snapshot_content_from_store(snapshot, self._content_store)
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
            payload={
                "gate_id": gate_id,
                "snapshot_ids": gate_payload.get("snapshot_ids", []),
                "artifact_statuses": gate_payload.get("artifact_statuses", []),
                "content_artifacts": gate_payload.get("content_artifacts", []),
                "quality_scores": gate_payload.get("quality_scores", {}),
            },
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


def _export_records_from_files(
    run_id: RunId,
    exported_files: list[str],
    approved_snapshots: list[JsonObject],
) -> list[ExportRecordCreate]:
    """Map each exported file back to the snapshot(s) it was generated from.

    html/pptx exports are 1:1 (`{snapshot_id}.{ext}`, see exporters.py), so
    the filename stem recovers the exact snapshot_id. Batch formats (gift/
    h5p/qti/anki_apkg/flashcard_tsv) produce one file for every approved
    snapshot combined, so there's no per-snapshot filename to match — those
    fan out to one export_records row per contributing snapshot, sharing the
    same storage_path.
    # ponytail: batch-format rows share a storage_path; revisit if a format
    # ever needs an independently downloadable per-snapshot artifact.
    """
    by_snapshot_id = {str(snapshot.get("snapshot_id", "")): snapshot for snapshot in approved_snapshots}
    records: list[ExportRecordCreate] = []
    for file_path in exported_files:
        stem = Path(file_path).stem
        export_format = Path(file_path).suffix.lstrip(".") or "unknown"
        matched = by_snapshot_id.get(stem)
        targets = [matched] if matched is not None else approved_snapshots
        for snapshot in targets:
            records.append(ExportRecordCreate(
                export_id=f"export-{uuid4()}",
                run_id=run_id,
                artifact_id=str(snapshot.get("artifact_id", "")),
                snapshot_id=str(snapshot.get("snapshot_id", "")),
                format=export_format,
                storage_path=file_path,
            ))
    return records


def _has_export_evidence(state: JsonObject) -> bool:
    exported_files = state.get("exported_files")
    return isinstance(exported_files, list) and len(exported_files) > 0


def _auto_approval_payload(state: JsonObject) -> JsonObject | None:
    gate = state.get("approval_gate")
    if not isinstance(gate, dict) or gate.get("auto_approved") is not True:
        return None
    snapshot_ids = gate.get("snapshot_ids")
    if not isinstance(snapshot_ids, list):
        snapshot_ids = []
    return {
        "gate_name": str(gate.get("gate_name", "content_approval")),
        "snapshot_ids": [str(snapshot_id) for snapshot_id in snapshot_ids],
    }


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


def _content_update_event(state: JsonObject) -> JsonObject | None:
    value = state.get("content_update_event")
    if isinstance(value, dict):
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


def _snapshot_content(snapshot: JsonObject) -> JsonObject:
    content = _json_object(snapshot.get("content_json"))
    if "artifact_type" in content:
        return content
    artifact_type = snapshot.get("artifact_type")
    if not isinstance(artifact_type, str) or not artifact_type:
        return content
    return {**content, "artifact_type": artifact_type}


async def _snapshot_content_from_store(
    snapshot: JsonObject,
    content_store: ArtifactContentStore | None,
) -> JsonObject:
    inline_content = _snapshot_content(snapshot)
    if "content_json" in snapshot or content_store is None:
        return inline_content
    document_id = snapshot.get("document_id")
    if not isinstance(document_id, str) or not document_id:
        return inline_content
    projection = await content_store.read_projection(document_id)
    content = projection.model_dump(mode="json")
    return content if "artifact_type" in content else _snapshot_content({**snapshot, "content_json": content})


async def _hydrate_state_snapshots(
    state: JsonObject,
    content_store: ArtifactContentStore | None,
) -> JsonObject:
    approval_gate = _json_object(state.get("approval_gate"))
    snapshots = _rendered_snapshots(state) or _rendered_snapshots(approval_gate)
    hydrated_snapshots = [
        {**snapshot, "content_json": await _snapshot_content_from_store(snapshot, content_store)}
        for snapshot in snapshots
    ]
    hydrated_approval_gate = {
        **approval_gate,
        "rendered_snapshots": hydrated_snapshots,
    } if approval_gate else {}
    if approval_gate and "rendered_snapshots" not in state:
        return {**state, "approval_gate": hydrated_approval_gate}
    return {**state, "rendered_snapshots": hydrated_snapshots}


def _json_object(value: object) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}
