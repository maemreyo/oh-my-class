from __future__ import annotations

import json

from common.contracts.methodology_registry import METHODOLOGY_REGISTRY


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
