from __future__ import annotations

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


def has_scoped_section_edit(gate_payload: JsonObject) -> bool:
    return gate_payload.get("edit_type") == "scoped_section" and isinstance(gate_payload.get("section_edit"), dict)


def has_scoped_slide_deck_block_edit(gate_payload: JsonObject) -> bool:
    return (
        gate_payload.get("edit_type") == "scoped_slide_deck_block"
        and isinstance(gate_payload.get("slide_deck_block_edit"), dict)
    )


def apply_scoped_slide_deck_block_edit_on_artifacts(
    artifacts: list[JsonObject],
    gate_payload: JsonObject,
) -> JsonObject:
    """Gate-resume-flow marshaling wrapper around SDE-04's shared business function.

    Mirrors `apply_scoped_section_edit`'s JSON-in/JSON-out shape and
    graceful-no-op-on-invalid-input convention exactly, so `nodes.py`'s
    `_rollback_artifact_workflow` can branch on artifact type without any
    other change to that function's contract. Delegates the actual typed
    edit + SDE-02 registry validation to
    `packages.agents.slide_deck_engine.scoped_block_edit`, the single
    business function also used by the standalone snapshot-edit endpoint.
    """
    from common.contracts.slide_deck import SlideDeckData
    from packages.agents.slide_deck_engine.scoped_block_edit import (
        apply_scoped_slide_deck_block_edit,
        slide_deck_block_edit_event,
    )

    edit = gate_payload.get("slide_deck_block_edit")
    if not isinstance(edit, dict):
        return {"artifacts": _json_values(artifacts)}
    artifact_id = str(edit.get("artifact_id", ""))
    block_id = str(edit.get("block_id", ""))
    new_content = str(edit.get("new_content", ""))
    rationale = str(edit.get("rationale", ""))

    next_artifacts: list[JsonObject] = []
    edited = False
    for artifact in artifacts:
        is_target = (
            not edited
            and artifact.get("artifact_type") == "slide_deck"
            and str(artifact.get("artifact_id", artifact.get("id", ""))) == artifact_id
        )
        deck_data = _slide_deck_data(artifact) if is_target else None
        if not is_target or deck_data is None:
            next_artifacts.append(artifact)
            continue
        try:
            deck = SlideDeckData.model_validate(deck_data)
            updated_deck = apply_scoped_slide_deck_block_edit(deck, block_id, new_content)
        except ValueError:
            next_artifacts.append(artifact)
            continue
        next_artifacts.append(_artifact_with_slide_deck_data(artifact, updated_deck.model_dump(mode="json")))
        edited = True
    if not edited:
        return {"artifacts": _json_values(artifacts)}
    return {
        "artifacts": _json_values(next_artifacts),
        "content_update_event": slide_deck_block_edit_event(artifact_id, block_id, rationale),
    }


def apply_scoped_section_edit(artifacts: list[JsonObject], gate_payload: JsonObject) -> JsonObject:
    edit = gate_payload.get("section_edit")
    if not isinstance(edit, dict):
        return {"artifacts": _json_values(artifacts)}
    artifact_id = str(edit.get("artifact_id", ""))
    section_id = str(edit.get("section_id", ""))
    replacement = str(edit.get("replacement_content", ""))
    rationale = str(edit.get("rationale", ""))
    next_artifacts = [_edited_artifact(artifact, artifact_id, section_id, replacement, rationale) for artifact in artifacts]
    return {
        "artifacts": _json_values(next_artifacts),
        "content_update_event": {
            "event_name": "teaching_pack.content_version.created",
            "payload": {
                "artifact_id": artifact_id,
                "section_id": section_id,
                "authority": "teacher_edit",
                "diff": {
                    "status": "teacher_section_edit",
                    "changed_path": f"{artifact_id}.sections[{section_id}]",
                    "rationale": rationale,
                },
            },
        },
    }


def merge_regenerated_artifacts(
    artifacts: list[JsonObject],
    gate_payload: JsonObject,
    generated: list[JsonObject],
) -> list[JsonObject]:
    rejections = scoped_rejections(artifacts, gate_payload)
    if not rejections:
        return generated
    rejected_ids = {str(item["artifact_id"]) for item in rejections}
    rejected_types = {str(item["artifact_type"]) for item in rejections}
    preserved = [
        artifact for artifact in artifacts
        if str(artifact.get("artifact_id", "")) not in rejected_ids
        and str(artifact.get("artifact_type", "")) not in rejected_types
    ]
    return [*preserved, *generated]


def rejected_artifact_types(artifacts: list[JsonObject], gate_payload: JsonObject) -> list[str]:
    types: list[str] = []
    for rejection in scoped_rejections(artifacts, gate_payload):
        artifact_type = str(rejection["artifact_type"])
        if artifact_type not in types:
            types.append(artifact_type)
    return types


def scoped_rejections(artifacts: list[JsonObject], gate_payload: JsonObject) -> list[JsonObject]:
    if gate_payload.get("rejection_type") != "scoped" and gate_payload.get("action") != "reject_selected":
        return []
    raw_rejections = gate_payload.get("artifact_rejections")
    if not isinstance(raw_rejections, list):
        return []
    artifacts_by_id = {
        str(artifact.get("artifact_id", artifact.get("id", ""))): artifact
        for artifact in artifacts
    }
    rejections: list[JsonObject] = []
    for raw in raw_rejections:
        if not isinstance(raw, dict):
            continue
        artifact_id = str(raw.get("artifact_id", ""))
        artifact = artifacts_by_id.get(artifact_id)
        if artifact is None:
            continue
        rejections.append({
            "artifact_id": artifact_id,
            "artifact_type": str(artifact.get("artifact_type", "")),
            "reason": str(raw.get("reason", "")),
        })
    return rejections


def _edited_artifact(
    artifact: JsonObject,
    artifact_id: str,
    section_id: str,
    replacement: str,
    rationale: str,
) -> JsonObject:
    if str(artifact.get("artifact_id", artifact.get("id", ""))) != artifact_id:
        return artifact
    sections = artifact.get("sections")
    if not isinstance(sections, list):
        return artifact
    edited_sections = [_edited_section(section, section_id, replacement, rationale) for section in sections]
    metadata = _json_object(artifact.get("metadata"))
    return {
        **artifact,
        "sections": edited_sections,
        "metadata": {
            **metadata,
            "content_lineage": {
                "parent_artifact_id": artifact_id,
                "change_authority": "teacher_edit",
                "changed_section_id": section_id,
                "rationale": rationale,
            },
        },
    }


def _edited_section(section: JsonValue, section_id: str, replacement: str, rationale: str) -> JsonValue:
    if not isinstance(section, dict):
        return section
    candidate = str(section.get("section_id", section.get("id", section.get("title", ""))))
    if candidate != section_id:
        return section
    return {
        **section,
        "content": replacement,
        "edit_history": [
            *_json_objects(section.get("edit_history")),
            {"authority": "teacher_edit", "rationale": rationale},
        ],
    }


def _slide_deck_data(artifact: JsonObject) -> JsonObject | None:
    metadata = artifact.get("metadata")
    if isinstance(metadata, dict) and isinstance(metadata.get("slide_deck_data"), dict):
        return metadata["slide_deck_data"]  # type: ignore[return-value]
    return None


def _artifact_with_slide_deck_data(artifact: JsonObject, deck_data: JsonObject) -> JsonObject:
    # Slide deck artifacts embed the same deck payload twice (build_slide_deck_artifact's
    # ArtifactContent shape): metadata.slide_deck_data and sections[0].slide_deck. Both
    # copies must stay in sync or downstream readers of either one see stale content.
    metadata = _json_object(artifact.get("metadata"))
    next_artifact: JsonObject = {**artifact, "metadata": {**metadata, "slide_deck_data": deck_data}}
    sections = artifact.get("sections")
    if isinstance(sections, list) and sections and isinstance(sections[0], dict) and "slide_deck" in sections[0]:
        next_artifact["sections"] = [{**sections[0], "slide_deck": deck_data}, *sections[1:]]
    return next_artifact


def _json_objects(value: JsonValue | None) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _json_object(value: JsonValue | None) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}


def _json_values(values: list[JsonObject]) -> list[JsonValue]:
    return [value for value in values]
