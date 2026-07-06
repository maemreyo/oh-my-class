from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.contracts.components.registry import get_entry
from common.contracts.component_strategy_knowledge import default_capability_manifest_path

SELECTABLE_COMPONENT_TYPES = (
    "contrastive_pairs",
    "flow_step",
    "question_card",
    "question_list",
    "table",
    "vocab_cluster",
)

REVIEWED_COMPONENT_ANNOTATIONS = {
    "contrastive_pairs": {
        "cognitive_load": "medium",
        "print_risk": "low",
        "item_limit": 6,
        "accessibility_requirements": ("side_by_side_labels", "print_safe"),
        "known_limitations": ("dense rows should fall back to table",),
    },
    "flow_step": {
        "cognitive_load": "medium",
        "print_risk": "low",
        "item_limit": 8,
        "accessibility_requirements": ("ordered_steps",),
        "known_limitations": ("long procedures should fall back to table",),
    },
    "question_card": {
        "cognitive_load": "low",
        "print_risk": "low",
        "item_limit": 1,
        "accessibility_requirements": ("answer_key_separation",),
        "known_limitations": ("single-item fallback only",),
    },
    "question_list": {
        "cognitive_load": "medium",
        "print_risk": "medium",
        "item_limit": 12,
        "accessibility_requirements": ("answer_key_separation",),
        "known_limitations": ("small item counts may prefer question_card",),
    },
    "table": {
        "cognitive_load": "low",
        "print_risk": "low",
        "item_limit": 20,
        "accessibility_requirements": ("headers",),
        "known_limitations": ("not suitable for rich concept maps",),
    },
    "vocab_cluster": {
        "cognitive_load": "medium",
        "print_risk": "low",
        "item_limit": 8,
        "accessibility_requirements": ("semantic_group_labels",),
        "known_limitations": ("large clusters should fall back to table",),
    },
}

EXPORTER_MANIFEST = {
    "manifest_version": "exporter-capabilities.v1",
    "generated_from": "packages.exporters",
    "exporters": [
        {
            "export_format": "html",
            "supported_artifact_types": ["lesson", "worksheet", "quiz", "drill", "recap", "infographic"],
            "known_limitations": [],
        },
        {
            "export_format": "gift",
            "supported_artifact_types": ["quiz"],
            "known_limitations": ["assessment-only export"],
        },
        {
            "export_format": "h5p",
            "supported_artifact_types": ["quiz", "drill"],
            "known_limitations": ["interactive package export only"],
        },
    ],
}


def main() -> None:
    renderer = {
        "manifest_version": "renderer-capabilities.v1",
        "generated_from": "common.contracts.components.registry",
        "components": [_component_entry(component_type) for component_type in SELECTABLE_COMPONENT_TYPES],
    }
    _write_json(default_capability_manifest_path("renderer"), renderer)
    _write_json(default_capability_manifest_path("exporter"), EXPORTER_MANIFEST)


def _component_entry(component_type: str) -> dict[str, object]:
    registry_entry = get_entry(component_type)
    annotations = REVIEWED_COMPONENT_ANNOTATIONS[component_type]
    return {
        "component_type": registry_entry.type,
        "supported_artifact_types": sorted(registry_entry.artifact_types),
        "required_fields": list(registry_entry.required_fields),
        "template": registry_entry.template,
        "cognitive_load": annotations["cognitive_load"],
        "print_risk": annotations["print_risk"],
        "item_limit": annotations["item_limit"],
        "accessibility_requirements": list(annotations["accessibility_requirements"]),
        "known_limitations": list(annotations["known_limitations"]),
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
