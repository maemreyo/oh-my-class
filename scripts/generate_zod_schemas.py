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
from typing import Any, TypeAlias

JsonSchemaNode: TypeAlias = dict[str, Any] | list[Any]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.schema_codegen_config import MODELS
from scripts.schema_codegen_registry import generate_methodology_registry_file

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


def extract_named_json_schema(module_path: str, model_name: str) -> dict[str, Any]:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    parts = module_path.split(".")
    module = __import__(module_path, fromlist=[parts[-1]])
    model_class = getattr(module, model_name)
    schema = model_class.model_json_schema()
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    return schema


def _resolve_refs(node: JsonSchemaNode, defs: dict[str, Any]) -> None:
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
    def internal_schema_ref(model_name: str) -> str:
        return f"z.lazy(() => {model_name}Schema)"

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
            f'"{field_name}": z.array({internal_schema_ref(model_name)})',
            result,
        )
        result = re.sub(
            rf'"{field_name}": z\.any\(\)\.optional\(\)',
            f'"{field_name}": {internal_schema_ref(model_name)}.optional()',
            result,
        )
        result = re.sub(
            rf'"{field_name}": z\.any\(\)',
            f'"{field_name}": {internal_schema_ref(model_name)}',
            result,
        )
        result = re.sub(
            rf'"{field_name}": z\.union\(\[z\.any\(\), z\.null\(\)\]\)\.default\(null\)',
            f'"{field_name}": z.union([{internal_schema_ref(model_name)}, z.null()]).default(null)',
            result,
        )
        result = re.sub(
            rf'"{field_name}": z\.union\(\[z\.any\(\), z\.null\(\)\]\)',
            f'"{field_name}": z.union([{internal_schema_ref(model_name)}, z.null()])',
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

        nested_parts: list[str] = []
        top_level_parts: list[str] = []
        for model_name in all_models:
            if model_name == main_model:
                continue
            if model_name in defs:
                nested_schema = dict(defs[model_name])
                nested_schema["$schema"] = "http://json-schema.org/draft-07/schema#"
                nested_raw = json_schema_to_zod(nested_schema, f"{model_name}Schema")
                nested_parts.append(nested_raw.strip())
            else:
                nested_schema = extract_named_json_schema(module_path, model_name)
                nested_schema.pop("$defs", None)
                _resolve_refs(nested_schema, defs)
                nested_raw = json_schema_to_zod(nested_schema, f"{model_name}Schema")
                top_level_parts.append(nested_raw.strip())

        # Combine: nested models first, then main model
        combined_parts = [*nested_parts, raw_zod, *top_level_parts]
        combined = "\n\n".join(combined_parts)
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
