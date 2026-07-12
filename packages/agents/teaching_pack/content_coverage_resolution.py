"""#464: joint generation-capability resolution -- specialist capability
(can the code generate this artifact type at all) combined with subject
capability-pack coverage (is there certified curriculum backing for this
artifact family in this subject/grade band).

Deliberately a *separate* module from `specialist_capability.py`, not a
change to it: that module's own docstring is explicit that declaring
subject/grade specificity per specialist would be fabricated, since none of
the ten registered specialists branch on subject or grade band in code.
This module composes the two existing single-sources-of-truth
(`resolve_specialist_capability` for code capability,
`SubjectCapabilityPack` for curriculum coverage) into one joint decision,
without blurring what each one actually certifies.

**Not yet wired to a live caller** (#464 remains open pending this):
`generate_one_artifact.py`'s payload (`GenerateOneArtifactPayload`) carries
no `subject`/`grade_band` field today, and neither does `ContentBrief` --
threading that through the graph state/payload is a separate, larger
integration task. This module is the resolution logic that integration
would call once that data exists; it's tested in isolation against the four
real capability-pack fixtures (`common/component_strategy_knowledge/capabilities/`)
in the meantime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from common.contracts.grade_band import GradeBand
from common.contracts.subject_capability_pack import SubjectCapabilityPack
from packages.agents.teaching_pack.specialist_capability import (
    CapabilityResolution,
    resolve_specialist_capability,
)

ContentCoverageStatus = Literal["supported", "degraded", "unsupported"]


@dataclass(frozen=True, slots=True)
class ContentCoverageResolution:
    """The joint outcome of code-capability and curriculum-coverage resolution.

    `status` is the more restrictive of the two component signals:
    `unsupported` if the specialist resolution is unsupported (curriculum
    coverage is irrelevant if the code can't generate it at all); otherwise
    `degraded` if no capability pack backs this artifact type for the given
    subject/grade band; `supported` only when both agree.
    """

    artifact_type: str
    status: ContentCoverageStatus
    specialist_resolution: CapabilityResolution
    coverage_policy_note: str | None = None


def resolve_content_coverage(
    artifact_type: str,
    *,
    subject: str,
    grade_band: GradeBand,
    generic_fallback_enabled: bool,
    capability_packs: dict[str, SubjectCapabilityPack],
) -> ContentCoverageResolution:
    """Resolve `artifact_type` for one (subject, grade_band) pair.

    `capability_packs` is keyed by `subject` -- the caller supplies whichever
    packs it has loaded. A missing key, or a pack that exists but doesn't
    certify this artifact family for this grade band, degrades rather than
    blocks: the specialist can still generate the content, it's just not
    backed by a certified capability pack, and `coverage_policy_note` names
    exactly why.
    """
    specialist_resolution = resolve_specialist_capability(
        artifact_type, generic_fallback_enabled=generic_fallback_enabled,
    )
    if specialist_resolution.status == "unsupported":
        return ContentCoverageResolution(
            artifact_type=artifact_type,
            status="unsupported",
            specialist_resolution=specialist_resolution,
        )

    pack = capability_packs.get(subject)
    if pack is None:
        return ContentCoverageResolution(
            artifact_type=artifact_type,
            status="degraded",
            specialist_resolution=specialist_resolution,
            coverage_policy_note=(
                f"no capability pack registered for subject {subject!r}; "
                "generation proceeds without certified curriculum coverage"
            ),
        )

    coverage = pack.coverage_for(grade_band)
    if artifact_type not in coverage.artifact_families:
        return ContentCoverageResolution(
            artifact_type=artifact_type,
            status="degraded",
            specialist_resolution=specialist_resolution,
            coverage_policy_note=(
                f"{subject}/{grade_band.value} capability pack ({pack.manifest_version}) "
                f"does not certify {artifact_type!r}; certified families: "
                + ", ".join(sorted(coverage.artifact_families))
            ),
        )
    return ContentCoverageResolution(
        artifact_type=artifact_type,
        status=specialist_resolution.status,
        specialist_resolution=specialist_resolution,
    )
