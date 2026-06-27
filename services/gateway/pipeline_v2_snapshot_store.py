from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Literal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from services.gateway.pipeline_v2_snapshot_models import ArtifactSnapshot
from services.gateway.pipeline_v2_types import RunId

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.gateway.pipeline_v2_types import JsonObject, JsonValue


@dataclass(frozen=True, slots=True)
class ArtifactSnapshotCreate:
    snapshot_id: str
    run_id: RunId
    artifact_id: str
    artifact_type: str
    content_json: JsonObject
    rendered_html: str
    renderer_version: str
    template_version: str = "unknown"
    theme_version: str = "unknown"
    student_rendered_html: str | None = None
    version_mismatch_policy: Literal["block", "warn"] = "block"


@dataclass(frozen=True, slots=True)
class ArtifactSnapshotRead:
    snapshot_id: str
    run_id: RunId
    artifact_id: str
    artifact_type: str
    content_hash: str
    html_hash: str
    content_json: JsonObject | None
    rendered_html: str
    student_rendered_html: str
    renderer_version: str
    template_version: str
    theme_version: str
    standalone_valid: bool
    approved_at: datetime | None


_CSS_EXTERNAL_ASSET_PATTERN = re.compile(
    r"(?:@import\s+url\(|url\()\s*['\"]?(?:https?://|//)",
    re.IGNORECASE,
)


class PipelineV2SnapshotStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_snapshot(self, content_hash: str) -> bool:
        statement = select(ArtifactSnapshot.snapshot_id).where(
            ArtifactSnapshot.content_hash == content_hash,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def create_snapshot(self, payload: ArtifactSnapshotCreate) -> ArtifactSnapshotRead:
        student_html = payload.student_rendered_html or render_student_preview_html(
            payload.content_json,
        )
        student_html_safe = remove_answer_keys_from_html(student_html)
        content_hash = snapshot_content_hash(payload.content_json, payload.rendered_html)
        html_hash = sha256(payload.rendered_html.encode()).hexdigest()
        standalone_valid = is_standalone_html(payload.rendered_html)
        statement = pg_insert(ArtifactSnapshot).values(
            snapshot_id=payload.snapshot_id,
            run_id=payload.run_id,
            artifact_id=payload.artifact_id,
            artifact_type=payload.artifact_type,
            content_hash=content_hash,
            html_hash=html_hash,
            content_json=payload.content_json,
            rendered_html=payload.rendered_html,
            student_rendered_html=student_html_safe,
            renderer_version=payload.renderer_version,
            template_version=payload.template_version,
            theme_version=payload.theme_version,
            standalone_valid=standalone_valid,
        ).on_conflict_do_nothing(
            index_elements=["content_hash"],
        )
        await self._session.execute(statement)
        existing_snapshot = await self._get_by_content_hash(content_hash)
        if existing_snapshot is not None:
            _validate_snapshot_versions(payload, existing_snapshot)
        snapshot = await self.get_snapshot(payload.run_id, payload.snapshot_id)
        if snapshot is None:
            snapshot = await self.get_by_run_content_hash(payload.run_id, content_hash)
        if snapshot is None:
            raise SnapshotPersistenceError(payload.snapshot_id)
        return snapshot

    async def _get_by_content_hash(self, content_hash: str) -> ArtifactSnapshot | None:
        statement = select(ArtifactSnapshot).where(ArtifactSnapshot.content_hash == content_hash)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_snapshot(self, run_id: RunId, snapshot_id: str) -> ArtifactSnapshotRead | None:
        statement = select(ArtifactSnapshot).where(
            ArtifactSnapshot.run_id == run_id,
            ArtifactSnapshot.snapshot_id == snapshot_id,
        )
        result = await self._session.execute(statement)
        snapshot = result.scalar_one_or_none()
        if snapshot is None:
            return None
        return _read_snapshot(snapshot)

    async def get_by_run_content_hash(
        self,
        run_id: RunId,
        content_hash: str,
    ) -> ArtifactSnapshotRead | None:
        statement = select(ArtifactSnapshot).where(
            ArtifactSnapshot.run_id == run_id,
            ArtifactSnapshot.content_hash == content_hash,
        )
        result = await self._session.execute(statement)
        snapshot = result.scalar_one_or_none()
        if snapshot is None:
            return None
        return _read_snapshot(snapshot)

    async def list_run_snapshots(self, run_id: RunId) -> list[ArtifactSnapshotRead]:
        statement = select(ArtifactSnapshot).where(ArtifactSnapshot.run_id == run_id)
        result = await self._session.execute(statement)
        return [_read_snapshot(snapshot) for snapshot in result.scalars().all()]

    async def approve_snapshots(self, run_id: RunId, snapshot_ids: list[str]) -> int:
        statement = select(ArtifactSnapshot).where(
            ArtifactSnapshot.run_id == run_id,
            ArtifactSnapshot.snapshot_id.in_(snapshot_ids),
        ).with_for_update()
        result = await self._session.execute(statement)
        snapshots = list(result.scalars().all())
        for snapshot in snapshots:
            if not snapshot.standalone_valid:
                raise NonStandaloneSnapshotApprovalError(snapshot.snapshot_id)
            snapshot.approved_at = datetime.now(tz=snapshot.created_at.tzinfo)
        await self._session.flush()
        return len(snapshots)


def snapshot_content_hash(content_json: JsonObject, rendered_html: str) -> str:
    digest = sha256()
    canonical_content = json.dumps(
        content_json,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    digest.update(canonical_content.encode())
    digest.update(b"\0")
    digest.update(rendered_html.encode())
    return digest.hexdigest()


def is_standalone_html(rendered_html: str) -> bool:
    lowered = rendered_html.lower()
    has_doctype = "<!doctype html" in lowered
    parser = StandaloneHtmlAssetParser()
    parser.feed(rendered_html)
    has_css_external_asset = _CSS_EXTERNAL_ASSET_PATTERN.search(rendered_html) is not None
    return has_doctype and not parser.has_external_asset and not has_css_external_asset


def render_student_preview_html(content_json: JsonObject) -> str:
    title = escape(str(content_json.get("title", "oh-my-class preview")))
    sections = content_json.get("sections", [])
    bodies: list[str] = []
    if isinstance(sections, list):
        for section in sections:
            if isinstance(section, dict) and section.get("teacher_only") is not True:
                bodies.append(f"<section>{_safe_section_text(section)}</section>")
    body = "".join(bodies) or "<section>oh-my-class preview</section>"
    return f"<!DOCTYPE html><html><body><h1>{title}</h1>{body}</body></html>"


def _safe_section_text(section: dict[str, JsonValue]) -> str:
    values = [escape(str(value)) for key, value in section.items() if key != "teacher_only"]
    return " ".join(values)


def remove_answer_keys_from_html(rendered_html: str) -> str:
    """Remove answer key sections and answer-key-marked content from HTML.
    
    Scans the HTML for sections tagged with `data-answer-key="true"` or
    `data-teacher-only="true"` and removes them. Also sanitizes text patterns
    like "Answer:", "Correct:", "Solution:" from student-visible content.
    
    Returns the cleaned HTML; if no answer keys found, returns the input unchanged.
    """
    # Remove sections with data-answer-key or data-teacher-only attributes
    html = re.sub(
        r'<section[^>]*(?:data-answer-key="true"|data-teacher-only="true")[^>]*>.*?</section>',
        '',
        rendered_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    html = re.sub(
        r'<div[^>]*(?:data-answer-key="true"|data-teacher-only="true")[^>]*>.*?</div>',
        '',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    
    # Remove common answer-key text patterns
    html = re.sub(
        r'(?:Answer\s*(?:Key|:)|Correct\s*(?:Answer|:)|Solution\s*:)[^\n]*',
        '',
        html,
        flags=re.IGNORECASE,
    )
    
    return html


class StandaloneHtmlAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.has_external_asset = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._tag_has_external_reference(tag, attrs):
            self.has_external_asset = True

    def _tag_has_external_reference(self, tag: str, attrs: list[tuple[str, str | None]]) -> bool:
        lowered_tag = tag.lower()
        for name, value in attrs:
            if value is None:
                continue
            lowered_name = name.lower()
            if lowered_tag == "link" and lowered_name == "href":
                return not _is_inline_reference_url(value)
            if lowered_tag == "script" and lowered_name == "src":
                return True
            if lowered_name in {"src", "href"} and _is_external_asset_url(value):
                return True
        return False


def _is_external_asset_url(value: str) -> bool:
    stripped = value.strip().lower()
    return stripped.startswith(("http://", "https://", "//"))


def _is_inline_reference_url(value: str) -> bool:
    stripped = value.strip().lower()
    return stripped.startswith(("data:", "#"))


def _read_snapshot(snapshot: ArtifactSnapshot) -> ArtifactSnapshotRead:
    return ArtifactSnapshotRead(
        snapshot_id=snapshot.snapshot_id,
        run_id=RunId(snapshot.run_id),
        artifact_id=snapshot.artifact_id,
        artifact_type=snapshot.artifact_type,
        content_hash=snapshot.content_hash,
        html_hash=snapshot.html_hash,
        content_json=snapshot.content_json,
        rendered_html=snapshot.rendered_html,
        student_rendered_html=snapshot.student_rendered_html,
        renderer_version=snapshot.renderer_version,
        template_version=snapshot.template_version,
        theme_version=snapshot.theme_version,
        standalone_valid=snapshot.standalone_valid,
        approved_at=snapshot.approved_at,
    )


class SnapshotPersistenceError(RuntimeError):
    def __init__(self, snapshot_id: str) -> None:
        super().__init__(snapshot_id)


class NonStandaloneSnapshotApprovalError(RuntimeError):
    def __init__(self, snapshot_id: str) -> None:
        super().__init__(snapshot_id)


class SnapshotVersionMismatchError(RuntimeError):
    def __init__(self, snapshot_id: str) -> None:
        super().__init__(snapshot_id)


def _validate_snapshot_versions(
    payload: ArtifactSnapshotCreate,
    snapshot: ArtifactSnapshot,
) -> None:
    if payload.version_mismatch_policy == "warn":
        return
    if (
        snapshot.renderer_version != payload.renderer_version
        or snapshot.template_version != payload.template_version
        or snapshot.theme_version != payload.theme_version
    ):
        raise SnapshotVersionMismatchError(snapshot.snapshot_id)
