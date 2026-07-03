#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

uv run python scripts/run_teacher_scenarios.py --fixture --output-dir "$PROJECT_ROOT/.scratch/teacher-scenarios"
