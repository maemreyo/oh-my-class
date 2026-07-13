"""Evidence-aware synthesis plans, prerequisite ordering, and visual semantics."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

JsonObject = dict[str, Any]
ClaimAuthority = Literal["verified", "modified", "uncertain"]


class SynthesisClaim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str = Field(min_length=1, max_length=160)
    text: str = Field(min_length=1, max_length=4_000)
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    authority: ClaimAuthority
    required: bool = False


class SynthesisPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_version: str = "synthesis_plan.v1"
    retained_claims: tuple[SynthesisClaim, ...] = Field(min_length=1)
    omitted_claim_ids: tuple[str, ...] = ()
    terminology_policy: tuple[str, ...] = ()
    audience: str = Field(min_length=1, max_length=80)
    target_length_words: int = Field(ge=20, le=10_000)
    discourse_structure: tuple[str, ...] = Field(min_length=1)
    warnings: tuple[str, ...] = ()


class PrerequisiteCycleError(ValueError):
    def __init__(self, cycle_nodes: tuple[str, ...]) -> None:
        self.cycle_nodes = cycle_nodes
        super().__init__(f"prerequisite cycle detected: {', '.join(cycle_nodes)}")


def build_synthesis_plan(
    lesson_plan: JsonObject,
    research_brief: JsonObject,
    *,
    target_length_words: int,
    audience: str = "student",
) -> SynthesisPlan:
    claims: list[SynthesisClaim] = []
    for index, (objective_id, text) in enumerate(_objectives(lesson_plan), start=1):
        claims.append(SynthesisClaim(
            claim_id=f"claim:{objective_id}",
            text=text,
            evidence_ids=(objective_id,),
            authority="verified",
            required=True,
        ))
    warnings: list[str] = []
    source_claims = _source_claims(research_brief)
    by_normalized_text: dict[str, list[SynthesisClaim]] = defaultdict(list)
    for claim in source_claims:
        by_normalized_text[_normalize_claim(claim.text)].append(claim)
    for group in by_normalized_text.values():
        evidence = tuple(dict.fromkeys(evidence_id for claim in group for evidence_id in claim.evidence_ids))
        authority: ClaimAuthority = "verified" if len(evidence) >= 2 and all(
            claim.authority == "verified" for claim in group
        ) else ("uncertain" if any(claim.authority == "uncertain" for claim in group) else "modified")
        representative = group[0]
        if len(evidence) < 2:
            warnings.append(f"{representative.claim_id}: material claim has fewer than two independent evidence IDs")
        claims.append(representative.model_copy(update={"evidence_ids": evidence, "authority": authority}))
    if not claims:
        raise ValueError("synthesis requires an approved objective or grounded source claim")
    required = [claim for claim in claims if claim.required]
    optional = [claim for claim in claims if not claim.required and claim.authority != "uncertain"]
    retained: list[SynthesisClaim] = []
    word_budget = target_length_words
    for claim in [*required, *optional]:
        claim_words = max(1, len(claim.text.split()))
        if claim.required or claim_words <= word_budget:
            retained.append(claim)
            word_budget = max(0, word_budget - claim_words)
    retained_ids = {claim.claim_id for claim in retained}
    omitted = tuple(claim.claim_id for claim in claims if claim.claim_id not in retained_ids)
    terminology = tuple(dict.fromkeys(_strings(lesson_plan.get("terminology"))))
    return SynthesisPlan(
        retained_claims=tuple(retained),
        omitted_claim_ids=omitted,
        terminology_policy=terminology,
        audience=audience,
        target_length_words=target_length_words,
        discourse_structure=("orient", "explain", "connect", "retrieve"),
        warnings=tuple(warnings),
    )


def prerequisite_order(
    objective_ids: list[str],
    edges: list[tuple[str, str]],
) -> tuple[str, ...]:
    """Topologically order objectives; edge is ``prerequisite -> dependent``."""
    nodes = list(dict.fromkeys(objective_ids))
    indegree = {node: 0 for node in nodes}
    outgoing: dict[str, list[str]] = {node: [] for node in nodes}
    for prerequisite, dependent in edges:
        if prerequisite not in indegree or dependent not in indegree:
            continue
        outgoing[prerequisite].append(dependent)
        indegree[dependent] += 1
    queue = deque(node for node in nodes if indegree[node] == 0)
    ordered: list[str] = []
    while queue:
        node = queue.popleft()
        ordered.append(node)
        for dependent in outgoing[node]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                queue.append(dependent)
    if len(ordered) != len(nodes):
        raise PrerequisiteCycleError(tuple(node for node in nodes if indegree[node] > 0))
    return tuple(ordered)


def visual_semantics(plan: SynthesisPlan) -> tuple[JsonObject, ...]:
    visuals: list[JsonObject] = []
    for index, claim in enumerate(plan.retained_claims, start=1):
        visuals.append({
            "visual_id": f"visual-{index}",
            "claim_id": claim.claim_id,
            "semantic_role": "sequence" if index > 1 else "anchor",
            "label": claim.text,
            "alt_text": claim.text,
            "long_description": (
                f"Visual {index} represents {claim.text} Evidence: {', '.join(claim.evidence_ids)}. "
                "Meaning does not depend on color."
            ),
            "grayscale_safe": True,
            "no_image_fallback": claim.text,
        })
    return tuple(visuals)


def _objectives(lesson_plan: JsonObject) -> list[tuple[str, str]]:
    raw = lesson_plan.get("learning_objectives")
    if not isinstance(raw, list):
        return []
    records: list[tuple[str, str]] = []
    for index, item in enumerate(raw, start=1):
        if isinstance(item, str) and item.strip():
            records.append((f"objective-{index}", item.strip()))
        elif isinstance(item, dict):
            text = item.get("description")
            if isinstance(text, str) and text.strip():
                objective_id = item.get("objective_id")
                records.append((
                    objective_id.strip() if isinstance(objective_id, str) and objective_id.strip() else f"objective-{index}",
                    text.strip(),
                ))
    return records


def _source_claims(research_brief: JsonObject) -> list[SynthesisClaim]:
    raw = research_brief.get("sources")
    if not isinstance(raw, list):
        return []
    claims: list[SynthesisClaim] = []
    for index, source in enumerate(raw, start=1):
        if not isinstance(source, dict):
            continue
        excerpt = source.get("excerpt")
        if not isinstance(excerpt, str) or not excerpt.strip():
            continue
        text = excerpt.strip().split(". ")[0].rstrip(".") + "."
        source_id = str(source.get("source_id") or source.get("evidence_id") or f"source-{index}")
        status = str(source.get("verification_status") or source.get("authority") or "verified").casefold()
        authority: ClaimAuthority = status if status in {"verified", "modified", "uncertain"} else "uncertain"  # type: ignore[assignment]
        claim_id = str(source.get("claim_id") or f"claim:source:{index}")
        claims.append(SynthesisClaim(
            claim_id=claim_id,
            text=text,
            evidence_ids=(source_id,),
            authority=authority,
        ))
    return claims


def _normalize_claim(text: str) -> str:
    return " ".join(text.casefold().replace(".", "").replace(",", "").split())


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
