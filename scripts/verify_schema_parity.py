"""Verify Pydantic and Zod schemas are in sync.

Compares field names between Pydantic model_json_schema() and generated Zod files.
Run in CI to catch drift — fails if Zod files are stale.

Usage:
    python scripts/verify_schema_parity.py
"""

from __future__ import annotations

# import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# (pydantic_module, pydantic_model, zod_file_relative_to_root)
CHECKS: list[tuple[str, str, str]] = [
    (
        "common.contracts.lesson_plan",
        "LessonPlan",
        "common/schemas/src/generated/lesson_plan.ts",
    ),
    (
        "common.contracts.artifact",
        "ArtifactContent",
        "common/schemas/src/generated/artifact.ts",
    ),
    (
        "common.contracts.judge_output",
        "JudgeOutput",
        "common/schemas/src/generated/judge_output.ts",
    ),
]

FORBIDDEN_ZOD_PATTERNS: dict[str, tuple[str, ...]] = {
    "common/schemas/src/generated/lesson_plan.ts": (
        '"methodology": z.union([z.any(), z.null()])',
        '"payloads": z.any()',
    ),
}


def extract_pydantic_fields(module_path: str, model_name: str) -> set[str]:
    """Extract field names from a Pydantic model's JSON Schema properties."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    parts = module_path.split(".")
    module = __import__(module_path, fromlist=[parts[-1]])
    model_class = getattr(module, model_name)
    schema = model_class.model_json_schema()

    # Direct properties
    if "properties" in schema:
        return set(schema["properties"].keys())

    # If the model is in $defs (top-level is just a $ref)
    if "$defs" in schema and model_name in schema["$defs"]:
        defn = schema["$defs"][model_name]
        if "properties" in defn:
            return set(defn["properties"].keys())

    return set()


def extract_zod_fields(zod_file: Path) -> set[str]:
    """Extract field names from a Zod schema file.

    Looks for the first `z.object({ ... })` block and extracts property names
    that precede `: z.` or `: z.lazy(` patterns.
    """
    content = zod_file.read_text()

    # Match both `fieldName: z.` (unquoted) and `"fieldName": z.` (quoted) patterns
    fields: set[str] = set()
    for match in re.finditer(r'"?(\w+)"?\s*:\s*z\.', content):
        field = match.group(1)
        if field in {"z", "import"}:
            continue
        fields.add(field)

    return fields


def schema_has_forbidden_patterns(zod_rel_path: str, zod_file: Path) -> bool:
    content = zod_file.read_text()
    failed = False
    for pattern in FORBIDDEN_ZOD_PATTERNS.get(zod_rel_path, ()):
        if pattern in content:
            print(f"❌ {zod_rel_path}: forbidden arbitrary schema pattern remains: {pattern}")
            failed = True
    return failed


def main() -> int:
    all_ok = True

    for module_path, model_name, zod_rel_path in CHECKS:
        zod_path = PROJECT_ROOT / zod_rel_path

        pydantic_fields = extract_pydantic_fields(module_path, model_name)

        if not zod_path.exists():
            print(f"⚠️  {zod_rel_path} not found — run generate_zod_schemas.py first")
            all_ok = False
            continue

        zod_fields = extract_zod_fields(zod_path)
        if schema_has_forbidden_patterns(zod_rel_path, zod_path):
            all_ok = False

        missing_in_zod = pydantic_fields - zod_fields
        extra_in_zod = zod_fields - pydantic_fields

        if missing_in_zod:
            print(
                f"❌ {model_name}: fields in Pydantic but missing in Zod: {sorted(missing_in_zod)}"
            )
            all_ok = False

        if extra_in_zod:
            print(f"⚠️  {model_name}: fields in Zod but not in Pydantic: {sorted(extra_in_zod)}")

        if not missing_in_zod and not extra_in_zod:
            print(f"✅ {model_name}: fields in sync ({len(pydantic_fields)} fields)")

    if not all_ok:
        print(
            "\n❌ Schema parity check FAILED. "
            "Run `python scripts/generate_zod_schemas.py` and commit the result."
        )
    else:
        print("\n✅ All schemas in sync.")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
