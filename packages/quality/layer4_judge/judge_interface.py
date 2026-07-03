"""Adaptive judge interface -- integrates rubric selection, LLM judge calls,
and deterministic hard-block enforcement.

Design principles:
- Deterministic gates (Layer 1-3, HTML validator) remain authoritative hard blocks.
  A high LLM score can NEVER override: missing_doctype, external_assets,
  answer_key_leakage, PII_leakage, native_radio_inputs, unmanaged_js_runtime,
  missing_brand_string, or teacher_gate_state.
- Judge-unavailable path FAILS CLOSED: raises JudgeUnavailableError so the
  caller can escalate or fail the run -- never silently passes.
- LLM transport is injectable for testability (dependency inversion).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from common.contracts.judge_output import JudgeOutput
from common.contracts.rubric import Rubric
from packages.quality.layer4_judge.hard_blocks import (
    HARD_BLOCK_CODES as _HARD_BLOCK_CODES,
    enforce_hard_blocks,
)
from packages.quality.layer4_judge.judge_prompts import (
    JUDGE_SYSTEM_PROMPT,
    build_rubric_text,
    build_user_prompt,
)
from packages.quality.layer4_judge.judge_transport import (
    LLMTransport,
    default_litellm_transport,
)
from packages.quality.layer4_judge.judge_policy import (
    JudgePolicyContext,
    JudgeRiskLevel,
    judge_policy_decision,
)
from packages.quality.layer4_judge.rubric_selector import RubricSelector

logger = logging.getLogger(__name__)

# Re-export for backward-compatible imports from this module.
HARD_BLOCK_CODES = _HARD_BLOCK_CODES


# ---------------------------------------------------------------------------
# Strategy and error types
# ---------------------------------------------------------------------------


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
    policy_triggered: bool = False
    policy_reasons: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# AdaptiveJudge
# ---------------------------------------------------------------------------


class AdaptiveJudge:
    """Adaptive LLM judge with rubric selection and hard-block enforcement.

    Integrates:
    1. RubricSelector -- chooses rubric by (artifact_type, failure_context)
    2. LLM transport -- calls the judge model (injectable for testing)
    3. Hard-block enforcement -- deterministic gates always win
    4. Fail-closed -- judge unavailability escalates per configured strategy

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
        self._llm_transport = llm_transport or default_litellm_transport
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
        subject: str | None = None,
        locale: str | None = None,
        curriculum: str | None = None,
        risk_level: JudgeRiskLevel = "standard",
        borderline_score: float | None = None,
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
        deterministic_issues = deterministic_issues or []
        policy_context = JudgePolicyContext(
            artifact_type=artifact_type,
            deterministic_issues=tuple(deterministic_issues),
            subject=subject,
            locale=locale,
            curriculum=curriculum,
            risk_level=risk_level,
            borderline_score=borderline_score,
        )
        policy_decision = judge_policy_decision(policy_context)

        # Step 1: Select rubric
        rubric = self._selector.select(
            artifact_type,
            deterministic_issues,
            subject=subject,
            locale=locale,
            curriculum=curriculum,
            risk_level=risk_level,
        )

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
            # USE_DETERMINISTIC_ONLY: continue with empty outputs -> will force fail

        # Step 3: Aggregate judge outputs
        if raw_outputs:
            if len(raw_outputs) == 1:
                aggregated = raw_outputs[0]
            else:
                from packages.quality.layer4_judge.majority_vote import majority_vote
                aggregated = majority_vote(raw_outputs, pass_threshold=self._pass_threshold)
        else:
            # No LLM outputs available -- construct a fail result
            aggregated = JudgeOutput(
                overall_score=0.0,
                layer_scores=[],
                critical_issues=["llm_judge_unavailable"],
                passed=False,
                rationale="LLM judge produced no outputs; failing closed.",
                teacher_facing_summary="The automated reviewer was unavailable, so this artifact needs review before approval.",
            )

        # Step 4: Enforce hard blocks (deterministic gates always win)
        final_output, was_blocked, violations = enforce_hard_blocks(
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
            policy_triggered=policy_decision.should_judge,
            policy_reasons=policy_decision.reasons,
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
        rubric_text = build_rubric_text(rubric)

        rubric_prompt = JUDGE_SYSTEM_PROMPT.format(
            rubric_version=rubric.version_id,
            rubric_text=rubric_text,
        )
        system_content = f"{reviewer_system_prompt}\n\n{rubric_prompt}"

        user_prompt = build_user_prompt(
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
