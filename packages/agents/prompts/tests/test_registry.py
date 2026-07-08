"""Comprehensive tests for PromptModule, TemplateModule, ThemeModule registries,
drift detection, prompt metadata, and seed data.

Covers all invariants required by ISSUE-015:
- Versioned registration and retrieval
- Content hash computation and validation
- Drift detection (clean and dirty)
- Prompt metadata for Langfuse tracing
- Seed data integrity
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from packages.agents.prompts.drift import DriftReport, detect_drift, detect_drift_all
from packages.agents.prompts.registry import PromptModule, PromptRegistry, _sha256
from packages.agents.prompts.seed import SEED_MODULES, create_seeded_registry

if TYPE_CHECKING:
    from common.branding.registry import ThemeModule
    from packages.renderer.templates.registry import TemplateModule


# ═══════════════════════════════════════════════════════════════════════════════
# PromptModule
# ═══════════════════════════════════════════════════════════════════════════════


class TestPromptModule:
    """Tests for PromptModule dataclass creation and hash validation."""

    def test_create_auto_computes_hash(self) -> None:
        body = "You are a helpful assistant."
        module = PromptModule.create(id="test_v1", version="1.0.0", body=body)
        assert module.content_hash == hashlib.sha256(body.encode("utf-8")).hexdigest()

    def test_create_with_explicit_hash_matches(self) -> None:
        body = "Some prompt body"
        expected = hashlib.sha256(body.encode("utf-8")).hexdigest()
        module = PromptModule(id="test_v1", version="1.0.0", body=body, content_hash=expected)
        assert module.content_hash == expected

    def test_rejects_hash_mismatch(self) -> None:
        with pytest.raises(ValueError, match="Content hash mismatch"):
            PromptModule(id="test_v1", version="1.0.0", body="body", content_hash="bad_hash")

    def test_rejects_invalid_semver(self) -> None:
        with pytest.raises(ValueError, match="Invalid semver"):
            PromptModule.create(id="test_v1", version="1.0", body="body")

    def test_rejects_non_semver(self) -> None:
        with pytest.raises(ValueError, match="Invalid semver"):
            PromptModule.create(id="test_v1", version="v1.0.0", body="body")

    def test_frozen_dataclass(self) -> None:
        module = PromptModule.create(id="test_v1", version="1.0.0", body="body")
        with pytest.raises(AttributeError):
            module.body = "changed"  # type: ignore[misc]

    def test_metadata_defaults_to_empty(self) -> None:
        module = PromptModule.create(id="test_v1", version="1.0.0", body="body")
        assert module.metadata == {}

    def test_metadata_preserved(self) -> None:
        meta: dict[str, object] = {"task": "planning", "locale": "vi"}
        module = PromptModule.create(id="test_v1", version="1.0.0", body="body", metadata=meta)
        assert module.metadata == meta

    def test_output_schema_optional(self) -> None:
        module = PromptModule.create(id="test_v1", version="1.0.0", body="body")
        assert module.output_schema is None

    def test_output_schema_preserved(self) -> None:
        schema = {"type": "object", "required": ["title"]}
        module = PromptModule.create(id="test_v1", version="1.0.0", body="body", output_schema=schema)
        assert module.output_schema == schema


# ═══════════════════════════════════════════════════════════════════════════════
# PromptRegistry
# ═══════════════════════════════════════════════════════════════════════════════


class TestPromptRegistry:
    """Tests for PromptRegistry register/get/list_versions/validate_hash."""

    def _make_module(self, id: str = "test_v1", version: str = "1.0.0", body: str = "body") -> PromptModule:
        return PromptModule.create(id=id, version=version, body=body)

    def test_register_and_get_latest(self) -> None:
        reg = PromptRegistry()
        m1 = self._make_module(version="1.0.0")
        m2 = self._make_module(version="1.1.0")
        reg.register(m1)
        reg.register(m2)
        latest = reg.get("test_v1")
        assert latest.version == "1.1.0"

    def test_get_specific_version(self) -> None:
        reg = PromptRegistry()
        reg.register(self._make_module(version="1.0.0"))
        reg.register(self._make_module(version="2.0.0"))
        result = reg.get("test_v1", version="1.0.0")
        assert result.version == "1.0.0"

    def test_get_missing_id_raises_key_error(self) -> None:
        reg = PromptRegistry()
        with pytest.raises(KeyError, match="No PromptModule"):
            reg.get("nonexistent")

    def test_get_missing_version_raises_key_error(self) -> None:
        reg = PromptRegistry()
        reg.register(self._make_module(version="1.0.0"))
        with pytest.raises(KeyError, match="has no version"):
            reg.get("test_v1", version="9.9.9")

    def test_duplicate_registration_raises(self) -> None:
        reg = PromptRegistry()
        reg.register(self._make_module())
        with pytest.raises(ValueError, match="already registered"):
            reg.register(self._make_module())

    def test_list_versions(self) -> None:
        reg = PromptRegistry()
        reg.register(self._make_module(version="1.0.0"))
        reg.register(self._make_module(version="1.2.0"))
        reg.register(self._make_module(version="1.1.0"))
        versions = reg.list_versions("test_v1")
        assert versions == ["1.0.0", "1.1.0", "1.2.0"]

    def test_list_versions_missing_id(self) -> None:
        reg = PromptRegistry()
        with pytest.raises(KeyError, match="No PromptModule"):
            reg.list_versions("nonexistent")

    def test_validate_hash_valid(self) -> None:
        body = "Valid prompt body"
        reg = PromptRegistry()
        reg.register(PromptModule.create(id="test_v1", version="1.0.0", body=body))
        assert reg.validate_hash("test_v1") is True

    def test_validate_hash_consistent_for_frozen_modules(self) -> None:
        body = "Original body"
        reg = PromptRegistry()
        reg.register(PromptModule.create(id="test_v1", version="1.0.0", body=body))
        assert reg.validate_hash("test_v1") is True

    def test_list_all(self) -> None:
        reg = PromptRegistry()
        reg.register(self._make_module(id="a_v1", version="1.0.0"))
        reg.register(self._make_module(id="b_v1", version="1.0.0"))
        all_modules = reg.list_all()
        ids = {m.id for m in all_modules}
        assert ids == {"a_v1", "b_v1"}

    def test_version_sorting_is_semver(self) -> None:
        reg = PromptRegistry()
        reg.register(self._make_module(version="1.9.0"))
        reg.register(self._make_module(version="1.10.0"))
        reg.register(self._make_module(version="2.0.0"))
        versions = reg.list_versions("test_v1")
        assert versions == ["1.9.0", "1.10.0", "2.0.0"]
        assert reg.get("test_v1").version == "2.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# Drift Detection
# ═══════════════════════════════════════════════════════════════════════════════


class TestDriftDetection:
    """Tests for detect_drift and DriftReport."""

    def test_clean_module(self) -> None:
        reg = PromptRegistry()
        reg.register(PromptModule.create(id="mod_v1", version="1.0.0", body="unchanged"))
        report = detect_drift(reg, "mod_v1")
        assert report.is_clean is True
        assert report.issues == []

    def test_hash_mismatch_detected(self) -> None:
        """Simulate a hash mismatch by constructing a tampered module."""
        original_body = "Original prompt"
        computed_hash = _sha256(original_body)

        # Create a valid module, then register a tampered copy
        # We need to bypass the validation, so we register normally then check
        reg = PromptRegistry()
        module = PromptModule.create(id="tampered_v1", version="1.0.0", body=original_body)

        # Tamper with the body via direct attribute manipulation (bypass frozen)
        object.__setattr__(module, "body", "Tampered body")
        reg.register(module)

        report = detect_drift(reg, "tampered_v1")
        assert report.is_clean is False
        assert any("Hash mismatch" in issue for issue in report.issues)

    def test_unbumped_version_detected(self) -> None:
        """Hash mismatch on a 1.0.0-only module triggers unbumped warning."""
        original_body = "Original prompt"
        reg = PromptRegistry()
        module = PromptModule.create(id="unbumped_v1", version="1.0.0", body=original_body)

        # Tamper and register
        object.__setattr__(module, "body", "Changed body")
        reg.register(module)

        report = detect_drift(reg, "unbumped_v1")
        assert report.is_clean is False
        assert any("version bump" in issue.lower() for issue in report.issues)

    def test_module_not_found(self) -> None:
        reg = PromptRegistry()
        report = detect_drift(reg, "nonexistent")
        assert report.is_clean is False
        assert "not found" in report.issues[0].lower()

    def test_drift_report_is_clean_property(self) -> None:
        clean = DriftReport(module_id="a")
        dirty = DriftReport(module_id="b", issues=["something wrong"])
        assert clean.is_clean is True
        assert dirty.is_clean is False

    def test_detect_drift_all(self) -> None:
        reg = PromptRegistry()
        reg.register(PromptModule.create(id="a_v1", version="1.0.0", body="body a"))
        reg.register(PromptModule.create(id="b_v1", version="1.0.0", body="body b"))
        reports = detect_drift_all(reg)
        assert len(reports) == 2
        assert all(r.is_clean for r in reports)


# ═══════════════════════════════════════════════════════════════════════════════
# TemplateRegistry (packages/renderer/templates/registry.py)
# ═══════════════════════════════════════════════════════════════════════════════


class TestTemplateRegistry:
    """Tests for TemplateModule and TemplateRegistry."""

    def _make_template(self, id: str = "quiz_v1", version: str = "1.0.0", content_hash: str = "") -> TemplateModule:
        from packages.renderer.templates.registry import TemplateModule
        if not content_hash:
            content_hash = _sha256("<html>quiz template</html>")
        return TemplateModule(
            id=id,
            version=version,
            path=f"pages/{id.split('_')[0]}.html",
            content_hash=content_hash,
            artifact_types=["quiz"],
        )

    def test_register_and_get(self) -> None:
        from packages.renderer.templates.registry import TemplateRegistry
        reg = TemplateRegistry()
        t = self._make_template()
        reg.register(t)
        result = reg.get("quiz_v1")
        assert result.id == "quiz_v1"

    def test_get_missing_raises(self) -> None:
        from packages.renderer.templates.registry import TemplateRegistry
        reg = TemplateRegistry()
        with pytest.raises(KeyError, match="No TemplateModule"):
            reg.get("nonexistent")

    def test_get_latest_version(self) -> None:
        from packages.renderer.templates.registry import TemplateRegistry
        reg = TemplateRegistry()
        reg.register(self._make_template(version="1.0.0"))
        reg.register(self._make_template(version="2.0.0"))
        result = reg.get("quiz_v1")
        assert result.version == "2.0.0"

    def test_duplicate_raises(self) -> None:
        from packages.renderer.templates.registry import TemplateRegistry
        reg = TemplateRegistry()
        reg.register(self._make_template())
        with pytest.raises(ValueError, match="already registered"):
            reg.register(self._make_template())

    def test_validate_hash_match(self) -> None:
        from packages.renderer.templates.registry import TemplateRegistry
        content = "<html>quiz template</html>"
        reg = TemplateRegistry()
        reg.register(self._make_template(content_hash=_sha256(content)))
        assert reg.validate_hash("quiz_v1", content) is True

    def test_validate_hash_mismatch(self) -> None:
        from packages.renderer.templates.registry import TemplateRegistry
        content = "<html>quiz template</html>"
        reg = TemplateRegistry()
        reg.register(self._make_template(content_hash=_sha256(content)))
        assert reg.validate_hash("quiz_v1", "<html>tampered</html>") is False

    def test_invalid_semver_rejected(self) -> None:
        from packages.renderer.templates.registry import TemplateModule
        with pytest.raises(ValueError, match="Invalid semver"):
            TemplateModule(id="bad_v1", version="1.0", path="test.html")


# ═══════════════════════════════════════════════════════════════════════════════
# ThemeRegistry (common/branding/registry.py)
# ═══════════════════════════════════════════════════════════════════════════════


class TestThemeRegistry:
    """Tests for ThemeModule and ThemeRegistry."""

    def _make_theme(self, id: str = "ocean", version: str = "1.0.0", json_content: str = '{"color":"blue"}', css_content: str = ":root { --color: blue; }") -> ThemeModule:
        from common.branding.registry import ThemeModule
        return ThemeModule(
            id=id,
            version=version,
            path=f"kits/{id}/theme.json",
            content_hash=_sha256(json_content),
            css_hash=_sha256(css_content),
        )

    def test_register_and_get(self) -> None:
        from common.branding.registry import ThemeRegistry
        reg = ThemeRegistry()
        theme = self._make_theme()
        reg.register(theme)
        result = reg.get("ocean")
        assert result.id == "ocean"

    def test_get_missing_raises(self) -> None:
        from common.branding.registry import ThemeRegistry
        reg = ThemeRegistry()
        with pytest.raises(KeyError, match="No ThemeModule"):
            reg.get("nonexistent")

    def test_register_replaces_previous(self) -> None:
        from common.branding.registry import ThemeRegistry
        reg = ThemeRegistry()
        reg.register(self._make_theme(version="1.0.0"))
        reg.register(self._make_theme(version="2.0.0"))
        result = reg.get("ocean")
        assert result.version == "2.0.0"

    def test_validate_hash_match(self) -> None:
        from common.branding.registry import ThemeRegistry
        json_content = '{"color":"blue"}'
        reg = ThemeRegistry()
        reg.register(self._make_theme(json_content=json_content))
        assert reg.validate_hash("ocean", json_content) is True

    def test_validate_hash_mismatch(self) -> None:
        from common.branding.registry import ThemeRegistry
        json_content = '{"color":"blue"}'
        reg = ThemeRegistry()
        reg.register(self._make_theme(json_content=json_content))
        assert reg.validate_hash("ocean", '{"color":"red"}') is False

    def test_validate_css_hash_match(self) -> None:
        from common.branding.registry import ThemeRegistry
        css_content = ":root { --color: blue; }"
        reg = ThemeRegistry()
        reg.register(self._make_theme(css_content=css_content))
        assert reg.validate_css_hash("ocean", css_content) is True

    def test_validate_css_hash_mismatch(self) -> None:
        from common.branding.registry import ThemeRegistry
        css_content = ":root { --color: blue; }"
        reg = ThemeRegistry()
        reg.register(self._make_theme(css_content=css_content))
        assert reg.validate_css_hash("ocean", ":root { --color: red; }") is False

    def test_list_all(self) -> None:
        from common.branding.registry import ThemeRegistry
        reg = ThemeRegistry()
        reg.register(self._make_theme(id="default"))
        reg.register(self._make_theme(id="ocean"))
        reg.register(self._make_theme(id="forest"))
        all_themes = reg.list_all()
        ids = {t.id for t in all_themes}
        assert ids == {"default", "ocean", "forest"}

    def test_invalid_semver_rejected(self) -> None:
        from common.branding.registry import ThemeModule
        with pytest.raises(ValueError, match="Invalid semver"):
            ThemeModule(id="bad", version="v1", path="test.json")


# ═══════════════════════════════════════════════════════════════════════════════
# Prompt Metadata (packages/agents/llm/prompt_metadata.py)
# ═══════════════════════════════════════════════════════════════════════════════


class TestPromptMetadata:
    """Tests for PromptMetadata building and Langfuse conversion."""

    def test_build_prompt_metadata(self) -> None:
        from packages.agents.llm.prompt_metadata import build_prompt_metadata
        module = PromptModule.create(
            id="test_v1",
            version="1.0.0",
            body="# Section One\nHello\n## Section Two\nWorld",
        )
        compiled = "# Section One\nCompiled\n## Section Two\nContent"
        meta = build_prompt_metadata(module, compiled)

        assert meta.prompt_id == "test_v1"
        assert meta.prompt_version == "1.0.0"
        assert meta.content_hash == module.content_hash
        assert meta.compiled_hash == _sha256(compiled)
        assert meta.sections == ["Section One", "Section Two"]
        assert meta.output_schema_version is None

    def test_build_with_schema_version(self) -> None:
        from packages.agents.llm.prompt_metadata import build_prompt_metadata
        module = PromptModule.create(id="test_v1", version="1.0.0", body="# Hi")
        meta = build_prompt_metadata(module, "# Hi", output_schema_version="2.0")
        assert meta.output_schema_version == "2.0"

    def test_sections_extracted_from_body(self) -> None:
        from packages.agents.llm.prompt_metadata import build_prompt_metadata
        body = "# H1\n## H2\n### H3\nRegular text\n# Another H1"
        module = PromptModule.create(id="test_v1", version="1.0.0", body=body)
        meta = build_prompt_metadata(module, body)
        assert meta.sections == ["H1", "H2", "H3", "Another H1"]

    def test_no_sections_when_no_headers(self) -> None:
        from packages.agents.llm.prompt_metadata import build_prompt_metadata
        body = "Just some plain text without headers."
        module = PromptModule.create(id="test_v1", version="1.0.0", body=body)
        meta = build_prompt_metadata(module, body)
        assert meta.sections == []

    def test_to_langfuse_metadata(self) -> None:
        from packages.agents.llm.prompt_metadata import PromptMetadata, to_langfuse_metadata
        meta = PromptMetadata(
            prompt_id="planner_v1",
            prompt_version="1.0.0",
            content_hash="abc123",
            compiled_hash="def456",
            sections=["Intro", "Steps"],
            output_schema_version="1.0",
            overlay_ids=["vi_vn", "math"],
        )
        langfuse = to_langfuse_metadata(meta)

        assert langfuse["prompt_id"] == "planner_v1"
        assert langfuse["prompt_version"] == "1.0.0"
        assert langfuse["content_hash"] == "abc123"
        assert langfuse["compiled_hash"] == "def456"
        assert langfuse["sections"] == ["Intro", "Steps"]
        assert langfuse["output_schema_version"] == "1.0"
        assert langfuse["overlay_ids"] == ["vi_vn", "math"]

    def test_langfuse_metadata_none_schema(self) -> None:
        from packages.agents.llm.prompt_metadata import PromptMetadata, to_langfuse_metadata
        meta = PromptMetadata(
            prompt_id="test_v1",
            prompt_version="1.0.0",
            content_hash="abc",
            compiled_hash="def",
            sections=[],
        )
        langfuse = to_langfuse_metadata(meta)
        assert langfuse["output_schema_version"] is None
        assert langfuse["overlay_ids"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# Seed Data
# ═══════════════════════════════════════════════════════════════════════════════


class TestSeedData:
    """Tests for initial prompt module seed data."""

    def test_seed_count(self) -> None:
        assert len(SEED_MODULES) == 7

    def test_seed_ids(self) -> None:
        ids = {m.id for m in SEED_MODULES}
        expected = {
            "planner_v1",
            "content_creator_mcq_v1",
            "content_creator_lesson_v1",
            "content_creator_flashcard_v1",
            "researcher_v1",
            "judge_v1",
            "repair_v1",
        }
        assert ids == expected

    def test_all_seeds_have_valid_hash(self) -> None:
        for module in SEED_MODULES:
            assert module.content_hash == _sha256(module.body), (
                f"Hash mismatch in seed module '{module.id}'"
            )

    def test_all_seeds_have_output_schema(self) -> None:
        for module in SEED_MODULES:
            assert module.output_schema is not None, (
                f"Missing output_schema in seed module '{module.id}'"
            )

    def test_all_seeds_have_metadata(self) -> None:
        for module in SEED_MODULES:
            assert module.metadata, f"Empty metadata in seed module '{module.id}'"

    def test_all_seeds_are_v1(self) -> None:
        for module in SEED_MODULES:
            assert module.version == "1.0.0", (
                f"Unexpected version in seed module '{module.id}': {module.version}"
            )

    def test_create_seeded_registry(self) -> None:
        registry = create_seeded_registry()
        for module in SEED_MODULES:
            result = registry.get(module.id)
            assert result.id == module.id
            assert result.version == module.version

    def test_seeded_registry_all_validate(self) -> None:
        registry = create_seeded_registry()
        for module in SEED_MODULES:
            assert registry.validate_hash(module.id) is True, (
                f"Hash validation failed for '{module.id}'"
            )

    def test_seeded_registry_versions(self) -> None:
        registry = create_seeded_registry()
        for module in SEED_MODULES:
            versions = registry.list_versions(module.id)
            assert versions == ["1.0.0"]
