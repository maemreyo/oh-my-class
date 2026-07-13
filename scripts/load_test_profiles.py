"""Request-mix + arrival-schedule generation for the QA-02 load harness.

Two things live here, deliberately separated from the driver (scripts/load_test_driver.py)
so both are independently unit-testable without a network:

1. Payload generation — realistic `raw_request` / `class_info` sizes, a
   configurable mix of pipeline modes (generate_pack is lighter than
   diagnose_then_generate — skewing the mix would make p95 meaningless, see
   issue #130's implementation notes).
2. Arrival schedule — when each request fires, as a list of offsets in
   seconds from t=0. Supports a flat "steady" rate and a "burst" profile
   (short high-rate windows), because 5,000/day steady-state and a burst
   are different failure modes for backpressure/autoscaling.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

PipelineMode = Literal["generate_pack", "diagnose_then_generate"]

# Subjects/topics/grades used to vary payload content+size realistically —
# not just the same fixed string N times (that would let the pipeline
# cache/short-circuit in ways production traffic never would).
_SUBJECTS: tuple[str, ...] = ("math", "science", "english", "history", "art")
_TOPICS: tuple[str, ...] = (
    "Fractions", "Photosynthesis", "Persuasive essays", "The Industrial Revolution",
    "Color theory", "Long division", "Ecosystems", "Grammar: subject-verb agreement",
    "World War II causes", "Perspective drawing",
)
_GRADES: tuple[int, ...] = (3, 4, 5, 6, 7, 8)
_EVIDENCE: tuple[str, ...] = (
    "Students confuse numerator and denominator when adding fractions.",
    "Students struggle to identify the independent variable in an experiment.",
    "Students write run-on sentences instead of using conjunctions.",
)


@dataclass(frozen=True, slots=True)
class RequestMix:
    """Ratio of pipeline modes to submit. Must sum to 1.0."""

    generate_pack: float = 0.7
    diagnose_then_generate: float = 0.3

    def __post_init__(self) -> None:
        total = self.generate_pack + self.diagnose_then_generate
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"RequestMix ratios must sum to 1.0, got {total}")

    def pick(self, rng: random.Random) -> PipelineMode:
        return "diagnose_then_generate" if rng.random() < self.diagnose_then_generate else "generate_pack"


@dataclass(frozen=True, slots=True)
class LoadProfile:
    """A named load shape: how many requests, over what wall-clock window,
    with what burst multiplier applied to a fraction of the window."""

    name: str
    total_requests: int
    duration_seconds: float
    mix: RequestMix = field(default_factory=RequestMix)
    burst_fraction: float = 0.0
    """Fraction of duration_seconds that is a burst window (0 = pure steady state)."""
    burst_multiplier: float = 1.0
    """Arrival-rate multiplier during the burst window relative to steady rate."""


# 5,000 packs/day peak == ~208/hour == ~3.47/min average (ADR-034 north star).
# The "full" profile drives at that steady rate across a 1-hour representative
# window, plus a 10% burst window at 3x rate — real target scale, needs a real
# fleet + real wall-clock time (not CI-safe).
FULL_PROFILE = LoadProfile(
    name="full",
    total_requests=5000,
    duration_seconds=24 * 60 * 60,
    burst_fraction=0.1,
    burst_multiplier=3.0,
)

# CI-safe: same shape (mix + burst pattern), tiny volume, fast wall-clock.
# Proves the harness's own mechanics, not the SLO at scale.
SMOKE_PROFILE = LoadProfile(
    name="smoke",
    total_requests=10,
    duration_seconds=20.0,
    burst_fraction=0.3,
    burst_multiplier=3.0,
)

PROFILES: dict[str, LoadProfile] = {"smoke": SMOKE_PROFILE, "full": FULL_PROFILE}


def build_class_info(mode: PipelineMode, rng: random.Random) -> dict:
    """Realistic-sized class_info payload. diagnose_then_generate carries an
    extra student_evidence field (heavier prompt, matching production)."""
    class_info: dict = {
        "topic": rng.choice(_TOPICS),
        "grade": rng.choice(_GRADES),
        "subject": rng.choice(_SUBJECTS),
        "mode": mode,
        "artifact_types": ["lesson", "worksheet", "quiz"],
        "export_formats": ["html"],
    }
    if mode == "diagnose_then_generate":
        class_info["student_evidence"] = rng.choice(_EVIDENCE)
    return class_info


def build_run_payload(mode: PipelineMode, rng: random.Random) -> dict:
    class_info = build_class_info(mode, rng)
    return {
        "raw_request": f"Teach {class_info['topic']} to Grade {class_info['grade']}",
        "class_info": class_info,
    }


def generate_request_plan(profile: LoadProfile, *, seed: int = 0) -> list[tuple[float, PipelineMode, dict]]:
    """Return [(arrival_offset_seconds, mode, payload), ...] sorted by arrival time.

    Burst window is the *last* `burst_fraction` of duration_seconds, at
    `burst_multiplier` times the steady-state instantaneous rate — modeling
    an end-of-day cram rather than a warm-up ramp.
    """
    rng = random.Random(seed)
    n = profile.total_requests
    if n <= 0:
        return []

    burst_seconds = profile.duration_seconds * profile.burst_fraction
    steady_seconds = profile.duration_seconds - burst_seconds

    # Split requests between steady/burst windows proportional to their
    # "capacity" (duration * rate-multiplier) so burst really is denser.
    steady_weight = steady_seconds * 1.0
    burst_weight = burst_seconds * profile.burst_multiplier
    total_weight = steady_weight + burst_weight
    n_burst = round(n * (burst_weight / total_weight)) if total_weight > 0 and burst_seconds > 0 else 0
    n_steady = n - n_burst

    offsets: list[float] = []
    if n_steady > 0 and steady_seconds > 0:
        offsets.extend(rng.uniform(0.0, steady_seconds) for _ in range(n_steady))
    elif n_steady > 0:
        offsets.extend(0.0 for _ in range(n_steady))
    if n_burst > 0 and burst_seconds > 0:
        offsets.extend(rng.uniform(steady_seconds, profile.duration_seconds) for _ in range(n_burst))
    elif n_burst > 0:
        offsets.extend(steady_seconds for _ in range(n_burst))

    offsets.sort()
    plan: list[tuple[float, PipelineMode, dict]] = []
    for offset in offsets:
        mode = profile.mix.pick(rng)
        payload = build_run_payload(mode, rng)
        plan.append((offset, mode, payload))
    return plan
