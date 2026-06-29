from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.branding.generate_theme import (
    generate_core_tokens,
    generate_dark_mode,
    generate_group_tokens,
    generate_print_styles,
    generate_typography_tokens,
    generate_utility_classes,
)
from common.branding.registry import ThemeModule, ThemeRegistry
from common.contracts.rubric import Rubric, RubricRegistry
from packages.agents.prompts.registry import PromptRegistry
from packages.agents.prompts.repair_prompts import REPAIR_PROMPT_MODULES
from packages.agents.prompts.seed import SEED_MODULES
from packages.quality.layer4_judge.rubric_selector import RubricSelector
from packages.renderer.templates.registry import TemplateModule, TemplateRegistry

TEMPLATE_ROOT: Final[Path] = PROJECT_ROOT / "packages" / "renderer" / "templates"
THEME_ROOT: Final[Path] = PROJECT_ROOT / "common" / "branding" / "kits"


class RegistryDriftError(RuntimeError):
    def __init__(self, issues: list[str]) -> None:
        super().__init__("Registry drift detected: " + ", ".join(issues))
        self.issues = issues


@dataclass(frozen=True, slots=True)
class TemplateDriftRecord:
    module: TemplateModule
    content: str


@dataclass(frozen=True, slots=True)
class ThemeDriftRecord:
    module: ThemeModule
    json_content: str
    css_content: str


@dataclass(frozen=True, slots=True)
class RegistryDriftSnapshot:
    prompts: PromptRegistry
    templates: tuple[TemplateDriftRecord, ...]
    themes: tuple[ThemeDriftRecord, ...]
    rubrics: tuple[Rubric, ...]

    def with_template_content(self, module_id: str, content: str) -> RegistryDriftSnapshot:
        records = tuple(
            replace(record, content=content) if record.module.id == module_id else record
            for record in self.templates
        )
        return replace(self, templates=records)


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _template_id(path: Path) -> str:
    relative = path.relative_to(TEMPLATE_ROOT).with_suffix("")
    return "template_" + "_".join(relative.parts)


def _theme_css(theme_data: dict[str, object], theme_name: str) -> str:
    parts = [
        f"/* Auto-generated from theme.json — DO NOT EDIT MANUALLY */\n/* Theme: {theme_name} */\n",
        generate_core_tokens(theme_data),
        generate_group_tokens(theme_data),
        generate_typography_tokens(theme_data),
        generate_utility_classes(theme_data),
        generate_dark_mode(theme_data),
        generate_print_styles(theme_data),
        """body {
    font-family: var(--font-family);
    font-size: var(--font-size-base);
    line-height: var(--line-height);
    color: var(--color-text);
    background-color: var(--color-background);
    margin: 0;
    padding: 0;
}
""",
    ]
    return "\n".join(parts)


def _build_template_records() -> tuple[TemplateDriftRecord, ...]:
    registry = TemplateRegistry()
    records: list[TemplateDriftRecord] = []
    for path in sorted(TEMPLATE_ROOT.rglob("*.html")):
        content = path.read_text(encoding="utf-8")
        module = TemplateModule(
            id=_template_id(path),
            version="1.0.0",
            path=str(path.relative_to(TEMPLATE_ROOT)),
            content_hash=_sha256(content),
        )
        registry.register(module)
        records.append(TemplateDriftRecord(module=module, content=content))
    return tuple(records)


def _build_prompt_registry() -> PromptRegistry:
    registry = PromptRegistry()
    registered: set[tuple[str, str]] = set()
    for module in (*SEED_MODULES, *REPAIR_PROMPT_MODULES):
        key = (module.id, module.version)
        if key in registered:
            continue
        registered.add(key)
        registry.register(
            type(module)(
                id=module.id,
                version=module.version,
                body=module.body,
                output_schema=module.output_schema,
                content_hash=module.content_hash,
                metadata=dict(module.metadata),
            ),
        )
    return registry


def _build_theme_records() -> tuple[ThemeDriftRecord, ...]:
    registry = ThemeRegistry()
    records: list[ThemeDriftRecord] = []
    for path in sorted(THEME_ROOT.glob("*/theme.json")):
        json_content = path.read_text(encoding="utf-8")
        theme_data = json.loads(json_content)
        theme_name = path.parent.name
        css_content = _theme_css(theme_data, theme_name)
        module = ThemeModule(
            id=theme_name,
            version="1.0.0",
            path=str(path.relative_to(THEME_ROOT)),
            content_hash=_sha256(json_content),
            css_hash=_sha256(css_content),
        )
        registry.register(module)
        records.append(
            ThemeDriftRecord(
                module=module,
                json_content=json_content,
                css_content=css_content,
            ),
        )
    return tuple(records)


def build_registry_drift_snapshot() -> RegistryDriftSnapshot:
    return RegistryDriftSnapshot(
        prompts=_build_prompt_registry(),
        templates=_build_template_records(),
        themes=_build_theme_records(),
        rubrics=tuple(RubricSelector().registry),
    )


def assert_all_registry_hashes_clean(snapshot: RegistryDriftSnapshot) -> None:
    issues: list[str] = []

    for prompt in snapshot.prompts.list_all():
        if not snapshot.prompts.validate_hash(prompt.id, prompt.version):
            issues.append(f"prompt:{prompt.id}@{prompt.version}")

    template_registry = TemplateRegistry()
    for record in snapshot.templates:
        template_registry.register(record.module)
        if not template_registry.validate_hash(
            record.module.id,
            record.content,
            record.module.version,
        ):
            issues.append(f"template:{record.module.id}@{record.module.version}")

    theme_registry = ThemeRegistry()
    for record in snapshot.themes:
        theme_registry.register(record.module)
        if not theme_registry.validate_hash(record.module.id, record.json_content):
            issues.append(f"theme:{record.module.id}@{record.module.version}:json")
        if not theme_registry.validate_css_hash(record.module.id, record.css_content):
            issues.append(f"theme:{record.module.id}@{record.module.version}:css")

    rubric_registry = RubricRegistry()
    for rubric in snapshot.rubrics:
        rubric_registry.register(rubric)
        if not rubric_registry.validate_hash(rubric.version_id):
            issues.append(f"rubric:{rubric.version_id}")

    if issues:
        raise RegistryDriftError(issues)


def main() -> None:
    assert_all_registry_hashes_clean(build_registry_drift_snapshot())


if __name__ == "__main__":
    main()
