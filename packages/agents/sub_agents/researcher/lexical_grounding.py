from __future__ import annotations

import json

from common.contracts.vocabulary_batch import (
    LexicalGroundingBundle,
    LexicalGroundingCacheKeys,
    LexicalGroundingRequest,
    LexicalGroundingSourceEvidence,
    NormalizedVocabularyCluster,
)


def term_distinction_cache_key(terms: tuple[str, ...]) -> str:
    normalized_terms = sorted({term.strip().casefold() for term in terms if term.strip()})
    return f"lexical-grounding:terms:{'|'.join(normalized_terms)}"


def lexical_grounding_cache_keys(
    cluster: NormalizedVocabularyCluster,
    cluster_snapshot_hash: str,
) -> LexicalGroundingCacheKeys:
    return LexicalGroundingCacheKeys(
        cluster_snapshot_key=f"lexical-grounding:cluster:{cluster_snapshot_hash}",
        term_distinction_key=term_distinction_cache_key(cluster.terms),
    )


async def lexical_grounding_profile(
    request: LexicalGroundingRequest,
    run_id: str,
) -> LexicalGroundingBundle:
    verified_evidence = tuple(
        evidence for evidence in request.source_evidence if evidence.verification_status == "VERIFIED"
    )
    keys = lexical_grounding_cache_keys(request.cluster, request.cluster_snapshot_hash)
    if len(verified_evidence) < 2:
        return _needs_review_bundle(request, verified_evidence, keys)

    from packages.agents.config.models import MODELS
    from packages.agents.llm import extract_json_text
    from packages.agents.runtime import AgentRuntime, AgentRuntimeConfig
    from packages.agents.teaching_pack.stages import StageEnum, stage_number

    current_step = StageEnum.POST_BLUEPRINT_RESEARCH
    runtime = AgentRuntime(AgentRuntimeConfig(
        agent="researcher",
        run_id=run_id,
        step=stage_number(current_step),
        step_label=current_step.value,
        model=MODELS.researcher,
        base_temperature=0.2,
        retry_temperature=0.2,
    ))
    content = await runtime.complete_json(
        messages=runtime.messages(_system_prompt(), _user_prompt(request, verified_evidence, keys)),
        attempt=0,
        extra_tags=("profile:lexical_grounding",),
    )
    data = json.loads(extract_json_text(content))
    return LexicalGroundingBundle.model_validate(data)


def _needs_review_bundle(
    request: LexicalGroundingRequest,
    verified_evidence: tuple[LexicalGroundingSourceEvidence, ...],
    keys: LexicalGroundingCacheKeys,
) -> LexicalGroundingBundle:
    source_ids = tuple(evidence.source_id for evidence in verified_evidence) or ("unverified-source",)
    verified_count = len(verified_evidence)
    return LexicalGroundingBundle(
        bundle_id=f"ground-{request.cluster.cluster_id}",
        cluster_id=request.cluster.cluster_id,
        terms=request.cluster.terms,
        source_ids=source_ids,
        term_definitions=(),
        usage_constraints=(),
        common_confusions=(),
        example_pairs=(),
        distinction_notes=("Lexical distinctions need teacher review because verified evidence is insufficient.",),
        teacher_source_notes=(
            f"Only {verified_count} verified source(s) available; teacher review is required.",
        ),
        student_projection_fields=("distinction_notes",),
        confidence=0.4,
        readiness="needs_review",
        cache_keys=keys,
        uncertainty_flags=("insufficient_verified_sources",),
    )


def _system_prompt() -> str:
    return (
        "You are the Researcher Agent running the lexical_grounding profile. "
        "Return one JSON object matching LexicalGroundingBundle. Use only supplied evidence. "
        "Teacher source notes must stay teacher-facing and must not appear in student_projection_fields."
    )


def _user_prompt(
    request: LexicalGroundingRequest,
    verified_evidence: tuple[LexicalGroundingSourceEvidence, ...],
    keys: LexicalGroundingCacheKeys,
) -> str:
    return json.dumps(
        {
            "profile": "lexical_grounding",
            "cluster": request.cluster.model_dump(mode="json"),
            "source_evidence": [evidence.model_dump(mode="json") for evidence in verified_evidence],
            "required_output": {
                "term_definitions": "definition per term with source_ids and confidence",
                "usage_constraints": "constraints per term with source_ids and confidence",
                "common_confusions": "likely learner confusions",
                "example_pairs": "example/counterexample pairs with contrast notes",
                "teacher_source_notes": "teacher-only source notes",
                "student_projection_fields": [
                    "term_definitions",
                    "usage_constraints",
                    "common_confusions",
                    "example_pairs",
                    "distinction_notes",
                ],
                "confidence": "0..1, lower when sources conflict",
                "readiness": "passed or needs_review or failed",
                "uncertainty_flags": "non-empty when evidence is weak or conflicting",
            },
            "cache_keys": keys.model_dump(mode="json"),
        },
        ensure_ascii=False,
        indent=2,
    )
