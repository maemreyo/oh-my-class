#!/usr/bin/env python3
"""Run deterministic Content Quality Benchmark smoke/release fixtures (#470)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from common.contracts.content_evaluation.benchmark import BenchmarkScenario, build_benchmark_report


def _artifact(*, shallow: bool) -> dict[str, object]:
    text = (
        "Which statement best matches this learning objective? Identify equivalent fractions."
        if shallow else
        "Learners compare differently partitioned models, explain why they name the same value, and justify a transfer example."
    )
    return {
        "artifact_type": "lesson",
        "artifact_id": "benchmark-lesson-1",
        "sections": [{"id": "phase-model", "title": "Model", "content": text}],
        "metadata": {
            "objective_graph_id": "benchmark-graph-v1",
            "research_sources": [{"title": "Reviewed source", "content": "Equivalent fractions name the same value."}],
            "pedagogical_compiler": {"entity_projection_map": [{"semantic_id": "claim-1", "disposition": "transformed"}]},
        },
        "accessibility": {"language": "en", "reading_level": "grades_3_5"},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="build/content-benchmark-smoke.json")
    parser.add_argument("--expect-shallow-failure", action="store_true", default=True)
    args = parser.parse_args()
    scenario_good = BenchmarkScenario(
        scenario_id="positive-math-g5-en", artifact_type="lesson", family="lesson_design",
        subject="math", grade_band="grades_3_5", language="en", curriculum_lane="ccss", expected_pass=True,
    )
    scenario_shallow = BenchmarkScenario(
        scenario_id="negative-shallow-restatement", artifact_type="lesson", family="lesson_design",
        subject="math", grade_band="grades_3_5", language="en", curriculum_lane="ccss", expected_pass=False,
        mutation_tags=("shallow_pedagogy",),
    )
    positive = build_benchmark_report(((scenario_good, _artifact(shallow=False)),), dataset_version="content-smoke.v1")
    negative = build_benchmark_report(((scenario_shallow, _artifact(shallow=True)),), dataset_version="content-smoke.v1")
    if not positive.release_allowed:
        raise SystemExit("positive benchmark control did not pass")
    if negative.release_allowed:
        raise SystemExit("shallow negative control was not detected")
    payload = {
        "positive": positive.model_dump(mode="json"),
        "negative": negative.model_dump(mode="json"),
        "expected_failure_assertions": ["negative-shallow-restatement:pedagogy"],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encoded)
    output.with_suffix(output.suffix + ".sha256").write_text(hashlib.sha256(encoded).hexdigest() + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
