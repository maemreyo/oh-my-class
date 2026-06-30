"""Generate Zod schemas from Pydantic models.

Pipeline: Pydantic model → model_json_schema() → JSON Schema → json-schema-to-zod → Zod .ts
Source of truth: common/contracts/*.py (Pydantic)
Output: common/schemas/src/generated/ (Zod .ts files)

Usage:
    python scripts/generate_zod_schemas.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, TypedDict

# ── Configuration ──────────────────────────────────────────────

class ModelConfig(TypedDict):
    main_model: str
    all_models: list[str]
    output: str
    field_refs: dict[str, str]
    external_field_refs: dict[str, str]

MODELS: dict[str, ModelConfig] = {
    "common.contracts.lesson_plan": {
        "main_model": "LessonPlan",
        "all_models": [
            "LessonPlan",
            "LearningObjective",
            "AssessmentCheckpoint",
            "MethodologyPayloads",
            "MethodologyMetadata",
        ],
        "output": "common/schemas/src/generated/lesson_plan.ts",
        "field_refs": {
            "learning_objectives": "LearningObjective",
            "assessment_checkpoints": "AssessmentCheckpoint",
            "methodology": "MethodologyMetadata",
            "payloads": "MethodologyPayloads",
        },
        "external_field_refs": {
            "inverse_thinking": "InverseThinkingPackSchema:./inverse_thinking.js",
        },
    },
    "common.contracts.artifact": {
        "main_model": "TeachingPack",
        "all_models": ["ArtifactContent", "TeachingPack"],
        "output": "common/schemas/src/generated/artifact.ts",
        "field_refs": {
            "artifacts": "ArtifactContent",
        },
        "external_field_refs": {},
    },
    "common.contracts.judge_output": {
        "main_model": "JudgeOutput",
        "all_models": ["JudgeOutput", "LayerScore"],
        "output": "common/schemas/src/generated/judge_output.ts",
        "field_refs": {
            "layer_scores": "LayerScore",
        },
        "external_field_refs": {},
    },
    "common.contracts.inverse_thinking": {
        "main_model": "InverseThinkingPack",
        "all_models": [
            "InverseThinkingPack",
            "InverseThinkingTeacherOnly",
            "InverseThinkingCase",
            "InverseThinkingSummaryRow",
            "InverseThinkingStudentChallenge",
        ],
        "output": "common/schemas/src/generated/inverse_thinking.ts",
        "field_refs": {
            "cases": "InverseThinkingCase",
            "summary_table": "InverseThinkingSummaryRow",
            "student_challenges": "InverseThinkingStudentChallenge",
            "teacher_only": "InverseThinkingTeacherOnly",
        },
        "external_field_refs": {},
    },
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.contracts.methodology_registry import METHODOLOGY_REGISTRY


# ── Step 1: Extract JSON Schema from Pydantic ──────────────────


def extract_json_schema(module_path: str, main_model: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Import a Pydantic model and extract its JSON Schema.

    Returns (main_schema_with_refs, nested_defs) — the main schema keeps $ref
    references while nested models are extracted from $defs separately.
    """
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    parts = module_path.split(".")
    module = __import__(module_path, fromlist=[parts[-1]])
    model_class = getattr(module, main_model)
    schema = model_class.model_json_schema()

    schema["$schema"] = "http://json-schema.org/draft-07/schema#"

    defs = schema.pop("$defs", {})

    return schema, defs

    return schema, defs


def _resolve_refs(node: dict[str, Any], defs: dict[str, Any]) -> None:
    """Recursively resolve $ref references by inlining from $defs."""
    if isinstance(node, dict):
        if "$ref" in node:
            ref_path = node.pop("$ref")
            # Handle "#/$defs/Name" format
            if ref_path.startswith("#/$defs/"):
                def_name = ref_path.split("/")[-1]
                if def_name in defs:
                    defn = json.loads(json.dumps(defs[def_name]))  # deep copy
                    node.update(defn)
            return
        for value in node.values():
            if isinstance(value, dict):
                _resolve_refs(value, defs)
    elif isinstance(node, list):
        for item in node:
            if isinstance(item, dict):
                _resolve_refs(item, defs)


# ── Step 2: Convert JSON Schema → Zod via npm ──────────────────


def json_schema_to_zod(schema: dict[str, Any], name: str) -> str:
    """Run json-schema-to-zod CLI to convert JSON Schema to Zod TypeScript code."""
    schema_json = json.dumps(schema, indent=2)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as tmp:
        tmp.write(schema_json)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [
                "npx",
                "json-schema-to-zod",
                "-i",
                tmp_path,
                "--module",
                "esm",
                "--name",
                name,
                "--depth",
                "5",
            ],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(PROJECT_ROOT),
        )
        return result.stdout
    except FileNotFoundError:
        print(
            "ERROR: npx not found. Install Node.js and run 'npm install -g npx'.",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(
            f"ERROR: json-schema-to-zod failed:\n{exc.stderr}",
            file=sys.stderr,
        )
        sys.exit(1)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ── Step 3: Post-process Zod output ────────────────────────────


def post_process_zod(
    zod_code: str,
    model_names: list[str],
    field_refs: dict[str, str],
    external_field_refs: dict[str, str],
) -> str:
    lines = zod_code.split("\n")
    seen_import = False
    deduped: list[str] = []
    for line in lines:
        if line.strip() == 'import { z } from "zod"':
            if seen_import:
                continue
            seen_import = True
        deduped.append(line)

    result = "\n".join(deduped)

    for field_name, model_name in field_refs.items():
        result = re.sub(
            rf'"{field_name}": z\.array\(z\.any\(\)\)',
            f'"{field_name}": z.array({model_name}Schema)',
            result,
        )
        result = re.sub(
            rf'"{field_name}": z\.any\(\)\.optional\(\)',
            f'"{field_name}": {model_name}Schema.optional()',
            result,
        )
        result = re.sub(
            rf'"{field_name}": z\.any\(\)',
            f'"{field_name}": {model_name}Schema',
            result,
        )
        result = re.sub(
            rf'"{field_name}": z\.union\(\[z\.any\(\), z\.null\(\)\]\)\.default\(null\)',
            f'"{field_name}": z.union([{model_name}Schema, z.null()]).default(null)',
            result,
        )
        result = re.sub(
            rf'"{field_name}": z\.union\(\[z\.any\(\), z\.null\(\)\]\)',
            f'"{field_name}": z.union([{model_name}Schema, z.null()])',
            result,
        )

    external_imports: list[str] = []
    for field_name, ref in external_field_refs.items():
        schema_name, import_path = ref.split(":", maxsplit=1)
        external_imports.append(f'import {{ {schema_name} }} from "{import_path}"')
        result = re.sub(
            rf'"{field_name}": z\.union\(\[z\.any\(\), z\.null\(\)\]\)',
            f'"{field_name}": z.union([{schema_name}, z.null()])',
            result,
        )
        result = re.sub(
            rf'"{field_name}": z\.union\(\[z\.any\(\), z\.null\(\)\]\)\.default\(null\)',
            f'"{field_name}": z.union([{schema_name}, z.null()]).default(null)',
            result,
        )
        result = re.sub(
            rf'"{field_name}": z\.any\(\)',
            f'"{field_name}": {schema_name}',
            result,
        )

    if external_imports:
        result = result.replace(
            'import { z } from "zod"',
            'import { z } from "zod"\n' + "\n".join(external_imports),
            1,
        )

    type_exports = "\n".join(
        f"export type {name} = z.infer<typeof {name}Schema>;"
        for name in model_names
    )
    return result.rstrip() + "\n\n" + type_exports + "\n"


# ── Step 4: Wrap with header and write ─────────────────────────


def generate_zod_file(zod_code: str) -> str:
    """Wrap Zod code with the auto-generated header."""
    header = """\
/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

"""
    return header + zod_code


def generate_methodology_registry_file() -> str:
    entries = [
        {
            "tag": entry.tag,
            "labelEn": entry.label_en,
            "labelVi": entry.label_vi,
            "description": entry.description,
            "requiredComponents": list(entry.required_components),
            "requirementMode": entry.requirement_mode,
            "supportedArtifacts": list(entry.supported_artifacts),
            "exportFormats": list(entry.export_formats),
            "conflicts": list(entry.conflicts),
            "compatibleWith": list(entry.compatible_with),
        }
        for entry in METHODOLOGY_REGISTRY
    ]
    body = json.dumps(entries, indent=2, ensure_ascii=False)
    return (
        "/**\n"
        " * AUTO-GENERATED from common.contracts.methodology_registry\n"
        " * DO NOT EDIT MANUALLY — run `uv run python scripts/generate_zod_schemas.py` to regenerate\n"
        " */\n\n"
        f"export const METHODOLOGY_REGISTRY = {body} as const;\n\n"
        "export type MethodologyRegistryEntry = (typeof METHODOLOGY_REGISTRY)[number];\n"
        "export type MethodologyRegistryTag = MethodologyRegistryEntry[\"tag\"];\n"
    )


# ── Main ───────────────────────────────────────────────────────


def main() -> None:
    output_dir = PROJECT_ROOT / "common" / "schemas" / "src" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    for module_path, config in MODELS.items():
        main_model = config["main_model"]
        all_models = config["all_models"]
        output_path = PROJECT_ROOT / config["output"]

        print(f"Processing {module_path} (main={main_model})...")

        schema, defs = extract_json_schema(module_path, main_model)

        # Generate main model with $ref references (depth=0 → nested as z.any())
        raw_zod = json_schema_to_zod(schema, f"{main_model}Schema")

        # Generate each nested model separately from $defs
        nested_parts: list[str] = []
        for model_name in all_models:
            if model_name == main_model:
                continue
            if model_name in defs:
                nested_schema = dict(defs[model_name])
                nested_schema["$schema"] = "http://json-schema.org/draft-07/schema#"
                nested_raw = json_schema_to_zod(nested_schema, f"{model_name}Schema")
                nested_parts.append(nested_raw.strip())

        # Combine: nested models first, then main model
        combined = "\n\n".join(nested_parts) + "\n\n" + raw_zod
        zod_ts = post_process_zod(
            combined,
            all_models,
            config["field_refs"],
            config["external_field_refs"],
        )
        final = generate_zod_file(zod_ts)

        output_path.write_text(final)
        print(f"  → {output_path.relative_to(PROJECT_ROOT)}")

    # Generate index.ts that re-exports all generated schemas
    index_lines = [
        "/**",
        " * AUTO-GENERATED — re-exports all Zod schemas from Pydantic source",
        " * DO NOT EDIT MANUALLY",
        " */",
        "",
    ]
    for _module_path, config in MODELS.items():
        all_models = config["all_models"]
        filename = Path(config["output"]).stem
        exports = ", ".join(
            f"{name}Schema" for name in all_models
        )
        type_exports = ", ".join(all_models)
        index_lines.append(f'export {{ {exports} }} from "./{filename}.js";')
        index_lines.append(f'export type {{ {type_exports} }} from "./{filename}.js";')
    index_lines.append(
        'export { METHODOLOGY_REGISTRY } from "./methodology_registry.js";'
    )
    index_lines.append(
        'export type { MethodologyRegistryEntry, MethodologyRegistryTag } from "./methodology_registry.js";'
    )

    (output_dir / "index.ts").write_text("\n".join(index_lines) + "\n")
    print(f"  → {output_dir.relative_to(PROJECT_ROOT)}/index.ts")

    registry_path = output_dir / "methodology_registry.ts"
    registry_path.write_text(generate_methodology_registry_file())
    print(f"  → {registry_path.relative_to(PROJECT_ROOT)}")

    print("\n✅ Zod schemas generated from Pydantic models.")
    print("   Run `pnpm test` to verify schemas are valid.")


if __name__ == "__main__":
    main()
