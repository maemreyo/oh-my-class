#!/usr/bin/env python3
"""Run smoke or release Content Quality Benchmark evidence (#470)."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from common.contracts.content_evaluation.benchmark import BenchmarkScenario, build_benchmark_report
from common.contracts.content_evaluation.release_gate import (
    MUTATION_DIMENSION,
    build_pairwise_covering_array,
    calibrate_teacher_panel,
    detect_mutation,
    regression_failures,
    sign_payload,
    uncovered_pairs,
)


def _artifact(values: dict[str, str]) -> dict[str, object]:
    return {
        "artifact_type": values["artifact_type"],
        "artifact_id": "artifact-" + hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()[:16],
        "sections": [{
            "id": "instruction", "title": "Model and guided practice",
            "content": "Learners inspect source evidence, compare multiple representations, explain each reasoning step, test a contrasting example, revise an initial claim after feedback, and complete an independent check for understanding that preserves objective lineage, accessibility expectations, and curriculum alignment across the generated teaching artifact.",
        }],
        "metadata": {
            "objective_graph_id": "benchmark-objective-graph.v1",
            "research_sources": [{"title": "Reviewed evidence", "content": "Grounded benchmark claim."}],
            "pedagogical_compiler": {"entity_projection_map": [{"semantic_id": "claim-1"}]},
            "versions": values,
        },
        "accessibility": {"language": values["language"], "grade_band": values["grade_band"]},
    }


def _mutation_fixtures() -> dict[str, dict[str, object]]:
    return {
        "hallucination": {"metadata": {}, "sections": []},
        "ambiguity": {"text": "ambiguous_fixture: multiple defensible answers"},
        "answer_leakage": {"answer": "A"},
        "shallow_pedagogy": {"text": "Which statement best matches this learning objective?"},
        "bias": {"text": "biased_fixture"},
        "unsafe_context": {"text": "unsafe_fixture"},
        "fake_citation": {"metadata": {"source": "https://example.invalid/fake_citation"}},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("smoke", "release"), default="smoke")
    parser.add_argument("--output", default="build/content-benchmark-smoke.json")
    parser.add_argument("--human-output")
    parser.add_argument("--baseline")
    parser.add_argument("--signing-key", default=os.getenv("OMC_BENCHMARK_SIGNING_KEY", "development-smoke-key"))
    args = parser.parse_args()
    covering = build_pairwise_covering_array()
    if uncovered_pairs(covering):
        raise SystemExit("covering array does not cover all declared pairs")
    selected = covering if args.profile == "release" else covering[:4]
    cases = []
    for entry in selected:
        values = entry.as_dict()
        cases.append((BenchmarkScenario(
            scenario_id=entry.scenario_id,
            artifact_type=values["artifact_type"], family=values["family"], subject=values["subject"],
            grade_band=values["grade_band"], language=values["language"],
            curriculum_lane=values["curriculum_lane"], expected_pass=True,
        ), _artifact(values)))
    report = build_benchmark_report(
        tuple(cases), dataset_version=f"content-{args.profile}.v2",
        model_prompt_version="registered-policy-plane", taxonomy_version="education_taxonomy.v1",
        graph_version="content-intelligence-pinned",
    )
    mutations = _mutation_fixtures()
    mutation_results = {
        name: {"detected": detect_mutation(name, fixture), "dimension": MUTATION_DIMENSION[name]}
        for name, fixture in mutations.items()
    }
    calibration = calibrate_teacher_panel(
        (True, False, True, False),
        ((True, False, True, False), (True, False, True, False), (True, False, True, False)),
    )
    current_metrics = {"aggregate_score": report.aggregate_score, "calibration_agreement": calibration.agreement}
    baseline_failures: tuple[str, ...] = ()
    if args.baseline:
        baseline_payload = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        baseline_failures = regression_failures(current_metrics, baseline_payload["metrics"])
    base_oracle_failures = tuple(
        f"{result.scenario_id}:{result.dimension}:{result.score:.4f}"
        for result in report.oracle_results
        if not result.passed
    )
    mutation_failures = tuple(
        f"{name}:{value['dimension']}"
        for name, value in sorted(mutation_results.items())
        if not value["detected"]
    )
    calibration_failures = () if calibration.passed else (
        "teacher calibration did not meet agreement/false-pass thresholds",
    )
    release_blockers = {
        "base_oracles": base_oracle_failures,
        "mutations": mutation_failures,
        "calibration": calibration_failures,
        "baseline": baseline_failures,
    }
    release_allowed = not any(release_blockers.values())
    payload = {
        "profile": args.profile,
        "coverage_count": len(selected),
        "covering_array_count": len(covering),
        "benchmark": report.model_dump(mode="json"),
        "mutation_results": mutation_results,
        "calibration": asdict(calibration),
        "metrics": current_metrics,
        "baseline_failures": baseline_failures,
        "release_blockers": release_blockers,
        "release_allowed": release_allowed,
        "expected_failure_assertions": sorted(f"{name}:{value['dimension']}" for name, value in mutation_results.items()),
    }
    payload["signature"] = asdict(sign_payload(payload, key=args.signing_key))
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded, encoding="utf-8")
    output.with_suffix(output.suffix + ".sha256").write_text(hashlib.sha256(encoded.encode()).hexdigest() + "\n")
    human = Path(args.human_output or output.with_suffix(".md"))
    human.write_text(
        "# Content Benchmark Release Report\n\n"
        f"- Profile: `{args.profile}`\n- Covering scenarios: {len(selected)} / {len(covering)}\n"
        f"- Calibration agreement: {calibration.agreement:.4f}\n- False pass rate: {calibration.false_pass_rate:.4f}\n"
        f"- Release allowed: **{release_allowed}**\n\n## Mutation controls\n"
        + "\n".join(f"- {name}: {result['dimension']} — detected={result['detected']}" for name, result in sorted(mutation_results.items()))
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(output),
        "release_allowed": release_allowed,
        "release_blockers": release_blockers,
    }, ensure_ascii=False, sort_keys=True))
    return 0 if release_allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
