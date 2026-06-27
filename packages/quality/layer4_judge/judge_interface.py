"""Adaptive judge interface — integrates rubric selection, LLM judge calls,
and deterministic hard-block enforcement.

Design principles:
- Deterministic gates (Layer 1–3, HTML validator) remain authoritative hard blocks.
  A high LLM score can NEVER override: missing_doctype, external_assets,
  answer_key_leakage, PII_leakage, native_radio_inputs, unmanaged_js_runtime,
  missing_brand_string, or teacher_gate_state.
- Judge-unavailable path FAILS CLOSED: raises JudgeUnavailableError so the
  caller can escalate or fail the run — never silently passes.
- LLM transport is injectable for testability (dependency inversion).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from common.contracts.judge_output import JudgeOutput
from packages.quality.layer4_judge.rubric_selector import RubricSelector

if TYPE_CHECKING:
    from common.contracts.rubric import Rubric

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hard blocks — deterministic gate violations that override any LLM score.
# Sourced from packages/quality/layer3_html/html_validator.py HARD_BLOCKS
# and common/contracts/quality.py QualityFailureClass values.
# These are NEVER overridable by LLM judge output.
# ---------------------------------------------------------------------------

HARD_BLOCK_CODES: frozenset[str] = frozenset({
    "missing_doctype",
    "external_assets",          # HTML validator naming
    "external_asset",           # QualityFailureClass naming
    "answer_key_leakage",
    "pii_leakage",
    "native_radio_inputs",
    "unmanaged_js_runtime",
    "missing_brand_string",
    "schema_invalid",
})


class UnavailableStrategy(StrEnum):
    """Strategy when the LLM judge is unavailable."""

    FAIL_CLOSED = "fail_closed"       # Raise JudgeUnavailableError (default)
    USE_DETERMINISTIC_ONLY = "use_deterministic_only"  # Return passed=False with no LLM score


class JudgeUnavailableError(Exception):
    """Raised when the LLM judge is unavailable and strategy is FAIL_CLOSED."""

    def __init__(
        self,
        message: str = "LLM judge unavailable",
        *,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.cause = cause


# ---------------------------------------------------------------------------
# LLM transport protocol — callable matching the async LLM interface.
# ---------------------------------------------------------------------------

LLMTransport = Callable[..., Coroutine[Any, Any, str]]


async def _default_litellm_transport(
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    extra_body: dict[str, Any],
) -> str:
    """Default LLM transport using litellm.acompletion."""
    import litellm

    response = await litellm.acompletion(
        model=model,
        messages=messages,
        temperature=temperature,
        extra_body=extra_body,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Judge result with provenance
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class JudgeResult:
    """Result from the adaptive judge with full provenance.

    Attributes:
        judge_output: The LLM judge's scored output (may have been overridden).
        rubric_version: Which rubric version was used for scoring.
        rubric_description: Human-readable description of the selected rubric.
        deterministic_blocked: True if hard blocks forced passed=False
            regardless of LLM score.
        hard_block_violations: List of hard block codes that triggered the override.
        llm_available: Whether the LLM judge was reachable.
    """

    judge_output: JudgeOutput
    rubric_version: str
    rubric_description: str
    deterministic_blocked: bool
    hard_block_violations: list[str]
    llm_available: bool = True


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM_PROMPT = """\
You are an expert educational content reviewer for oh-my-class.

Score the provided teaching artifacts using the rubric below. For each criterion,
assign a score from 0-10 based on the rubric levels.

Rubric (version {rubric_version}):
{rubric_text}

IMPORTANT RULES:
- Write your rationale BEFORE giving numeric scores (think-before-score).
- Do NOT rate longer answers higher.
- Be precise and honest — flag real issues.
- Return ONLY valid JSON matching this schema:
{{
  "overall_score": <0-10>,
  "layer_scores": [{{"layer": "<name>", "score": <0-10>, "weight": <0-1>}}],
  "critical_issues": ["..."],
  "passed": <bool>,
  "rationale": "..."
}}
"""


def _build_rubric_text(rubric: Rubric) -> str:
    """Format rubric criteria into a human-readable prompt section."""
    lines: list[str] = []
    for criterion in rubric.criteria:
        lines.append(f"\n### {criterion.name} (weight: {criterion.weight:.0%})")
        for level in criterion.levels:
            lines.append(f"  Score {level.score}: {level.description}")
        if criterion.descriptors:
            for key, desc in criterion.descriptors.items():
                lines.append(f"  [{key}] {desc}")
    return "\n".join(lines)


def _build_user_prompt(
    artifacts: list[dict[str, Any]],
    lesson_plan: dict[str, Any] | None = None,
    deterministic_issues: list[str] | None = None,
) -> str:
    """Build the user prompt containing artifacts and context."""
    parts = [
        "Evaluate the following teaching artifacts:\n",
        f"Artifacts:\n{json.dumps(artifacts, indent=2, ensure_ascii=False)}",
    ]
    if lesson_plan:
        lp_json = json.dumps(lesson_plan, indent=2, ensure_ascii=False)
        parts.append(f"\nLesson Plan for alignment:\n{lp_json}")
    if deterministic_issues:
        parts.append(
            f"\n⚠️  Deterministic gates already flagged these issues: "
            f"{', '.join(deterministic_issues)}\n"
            f"Focus your review on the areas NOT covered by these flags."
        )
    parts.append("\nScore each criterion and provide overall assessment.")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Core judge logic
# ---------------------------------------------------------------------------


def _enforce_hard_blocks(
    judge_output: JudgeOutput,
    deterministic_issues: list[str],
    teacher_approved: bool,
) -> tuple[JudgeOutput, bool, list[str]]:
    """Enforce deterministic hard blocks on the LLM judge output.

    Returns (modified_judge_output, was_blocked, block_violations).
    If hard blocks are detected:
    - passed is forced to False
    - All hard block codes are added to critical_issues
    - The overall_score is capped (but not zeroed — for diagnostics)
    """
    violations: list[str] = []

    # Check deterministic issues against hard block codes
    for issue in deterministic_issues:
        normalized = issue.strip().lower().replace(" ", "_")
        if normalized in HARD_BLOCK_CODES:
            violations.append(issue)

    # Check teacher gate state
    if not teacher_approved:
        violations.append("teacher_gate_not_approved")

    if not violations:
        return judge_output, False, []

    # Force fail — override passed and ensure violations are in critical_issues
    existing_critical = list(judge_output.critical_issues)
    new_critical = existing_critical.copy()
    for v in violations:
        if v not in new_critical:
            new_critical.append(v)

    overridden = JudgeOutput(
        overall_score=judge_output.overall_score,
        layer_scores=list(judge_output.layer_scores),
        critical_issues=new_critical,
        passed=False,
        rationale=(
            judge_output.rationale
            + f"\n[Deterministic override: {', '.join(violations)} forced fail]"
        ),
    )

    return overridden, True, violations


# ---------------------------------------------------------------------------
# AdaptiveJudge
# ---------------------------------------------------------------------------


class AdaptiveJudge:
    """Adaptive LLM judge with rubric selection and hard-block enforcement.

    Integrates:
    1. RubricSelector — chooses rubric by (artifact_type, failure_context)
    2. LLM transport — calls the judge model (injectable for testing)
    3. Hard-block enforcement — deterministic gates always win
    4. Fail-closed — judge unavailability escalates per configured strategy

    Usage::

        judge = AdaptiveJudge()
        result = await judge.judge(
            artifacts=[{"artifact_type": "quiz", "title": "..."}],
            artifact_type="quiz",
            deterministic_issues=["answer_key_leakage"],
        )
        assert result.judge_output.passed is False  # hard block override
        assert result.rubric_version.startswith("rubric-quiz-")
    """

    def __init__(
        self,
        *,
        rubric_selector: RubricSelector | None = None,
        llm_transport: LLMTransport | None = None,
        model: str = "content-fusion",
        num_judges: int = 3,
        pass_threshold: float = 7.0,
        unavailable_strategy: UnavailableStrategy = UnavailableStrategy.FAIL_CLOSED,
    ) -> None:
        self._selector = rubric_selector or RubricSelector()
        self._llm_transport = llm_transport or _default_litellm_transport
        self._model = model
        self._num_judges = num_judges
        self._pass_threshold = pass_threshold
        self._unavailable_strategy = unavailable_strategy

    async def judge(
        self,
        artifacts: list[dict[str, Any]],
        *,
        artifact_type: str,
        deterministic_issues: list[str] | None = None,
        lesson_plan: dict[str, Any] | None = None,
        teacher_approved: bool = True,
    ) -> JudgeResult:
        """Run the adaptive judge pipeline.

        Args:
            artifacts: Artifact content dicts to evaluate.
            artifact_type: The type of artifact (e.g. "quiz", "lesson").
            deterministic_issues: Issues already flagged by deterministic
                gates (Layers 1-3, HTML validator). These are passed to
                the rubric selector for weight adjustment AND enforced
                as hard blocks that cannot be overridden.
            lesson_plan: Optional lesson plan for alignment scoring.
            teacher_approved: Whether the teacher has approved the blueprint.
                If False, the result is forced to fail regardless of LLM score.

        Returns:
            JudgeResult with the scored output and full provenance.

        Raises:
            JudgeUnavailableError: When the LLM is unreachable and strategy is FAIL_CLOSED.
        """
        # Step 1: Select rubric
        rubric = self._selector.select(artifact_type, deterministic_issues)
        deterministic_issues = deterministic_issues or []

        # Step 2: Call LLM judge(s)
        llm_available = True
        raw_outputs: list[JudgeOutput] = []

        try:
            raw_outputs = await self._call_llm_judges(
                artifacts=artifacts,
                rubric=rubric,
                lesson_plan=lesson_plan,
                deterministic_issues=deterministic_issues,
            )
        except Exception as exc:
            llm_available = False
            logger.warning("LLM judge call failed: %s", exc)

            if self._unavailable_strategy == UnavailableStrategy.FAIL_CLOSED:
                raise JudgeUnavailableError(
                    f"LLM judge unavailable: {exc}",
                    cause=exc,
                ) from exc
            # USE_DETERMINISTIC_ONLY: continue with empty outputs → will force fail

        # Step 3: Aggregate judge outputs
        if raw_outputs:
            if len(raw_outputs) == 1:
                aggregated = raw_outputs[0]
            else:
                from packages.quality.layer4_judge.majority_vote import majority_vote
                aggregated = majority_vote(raw_outputs, pass_threshold=self._pass_threshold)
        else:
            # No LLM outputs available — construct a fail result
            aggregated = JudgeOutput(
                overall_score=0.0,
                layer_scores=[],
                critical_issues=["llm_judge_unavailable"],
                passed=False,
                rationale="LLM judge produced no outputs; failing closed.",
            )

        # Step 4: Enforce hard blocks (deterministic gates always win)
        final_output, was_blocked, violations = _enforce_hard_blocks(
            judge_output=aggregated,
            deterministic_issues=deterministic_issues,
            teacher_approved=teacher_approved,
        )

        return JudgeResult(
            judge_output=final_output,
            rubric_version=rubric.version_id,
            rubric_description=rubric.description,
            deterministic_blocked=was_blocked,
            hard_block_violations=violations,
            llm_available=llm_available,
        )

    async def _call_llm_judges(
        self,
        *,
        artifacts: list[dict[str, Any]],
        rubric: Rubric,
        lesson_plan: dict[str, Any] | None,
        deterministic_issues: list[str],
    ) -> list[JudgeOutput]:
        """Call the LLM judge multiple times and collect outputs."""
        from packages.quality.layer4_judge.prompts import load_system_prompt

        reviewer_system_prompt = load_system_prompt()
        rubric_text = _build_rubric_text(rubric)

        rubric_prompt = _JUDGE_SYSTEM_PROMPT.format(
            rubric_version=rubric.version_id,
            rubric_text=rubric_text,
        )
        system_content = f"{reviewer_system_prompt}\n\n{rubric_prompt}"

        user_prompt = _build_user_prompt(
            artifacts=artifacts,
            lesson_plan=lesson_plan,
            deterministic_issues=deterministic_issues,
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt},
        ]

        outputs: list[JudgeOutput] = []
        last_error: Exception | None = None
        for i in range(self._num_judges):
            try:
                raw_response = await self._llm_transport(
                    model=self._model,
                    messages=messages,
                    temperature=0.3 + (i * 0.1),
                    extra_body={
                        "metadata": {
                            "tags": [
                                "agent:reviewer",
                                f"judge:{i + 1}",
                                f"rubric:{rubric.version_id}",
                                "pipeline:oh-my-class",
                            ]
                        }
                    },
                )

                # Parse JSON from response (strip code fences if present)
                content = raw_response
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                else:
                    json_str = content.strip()

                output_data = json.loads(json_str)
                judge_output = JudgeOutput.model_validate(output_data)
                outputs.append(judge_output)

            except Exception as exc:
                logger.debug(
                    "Judge call %d/%d failed", i + 1, self._num_judges,
                )
                last_error = exc
                continue

        if not outputs and last_error is not None:
            raise last_error

        return outputs
