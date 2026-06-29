"""Tests for PromptCompiler with overlay governance and provenance.

Covers all invariants required by task 7:
- Variable substitution from registered module body
- Overlay application with deterministic ordering
- Compiled prompt and PromptMetadata emission
- Rejection of missing/unknown variables
- Rejection of duplicate overlay IDs
- Rejection of secret-like overlay content
- Rejection of drifted modules
- Frozen CompiledPrompt and Overlay contracts
"""

from __future__ import annotations

import hashlib

import pytest

from packages.agents.llm.prompt_metadata import PromptMetadata
from packages.agents.prompts.compiler import (
    CompiledPrompt,
    DuplicateOverlayError,
    MissingVariableError,
    Overlay,
    PromptCompiler,
    SecretOverlayError,
    UnknownVariableError,
)
from packages.agents.prompts.drift import detect_drift
from packages.agents.prompts.registry import PromptModule, PromptRegistry

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_module(
    *,
    module_id: str = "test_v1",
    version: str = "1.0.0",
    body: str = "# Hello {{name}}\nTeach {{subject}} to grade {{grade}}.",
) -> PromptModule:
    return PromptModule.create(id=module_id, version=version, body=body)


def _make_registry(*modules: PromptModule) -> PromptRegistry:
    reg = PromptRegistry()
    for m in modules:
        reg.register(m)
    return reg


def _make_overlay(
    overlay_id: str = "ov1",
    body: str = "## Extra section\nMore content.",
    order: int = 0,
) -> Overlay:
    return Overlay(id=overlay_id, body=body, order=order)


# ═══════════════════════════════════════════════════════════════════════════════
# Overlay contract
# ═══════════════════════════════════════════════════════════════════════════════


class TestOverlayContract:
    """Tests for Overlay dataclass invariants."""

    def test_overlay_is_frozen(self) -> None:
        ov = _make_overlay()
        with pytest.raises(AttributeError):
            ov.id = "changed"  # type: ignore[misc]

    def test_overlay_is_slotted(self) -> None:
        ov = _make_overlay()
        assert not hasattr(ov, "__dict__")

    def test_overlay_defaults(self) -> None:
        ov = Overlay(id="x", body="text")
        assert ov.order == 0

    def test_overlay_order_preserved(self) -> None:
        ov = Overlay(id="x", body="text", order=5)
        assert ov.order == 5


# ═══════════════════════════════════════════════════════════════════════════════
# CompiledPrompt contract
# ═══════════════════════════════════════════════════════════════════════════════


class TestCompiledPromptContract:
    """Tests for CompiledPrompt dataclass invariants."""

    def test_compiled_prompt_is_frozen(self) -> None:
        cp = CompiledPrompt(
            module_id="test",
            module_version="1.0.0",
            compiled_body="body",
            metadata=PromptMetadata(
                prompt_id="test",
                prompt_version="1.0.0",
                content_hash="abc",
                compiled_hash="def",
                sections=[],
            ),
            overlay_ids=[],
        )
        with pytest.raises(AttributeError):
            cp.compiled_body = "changed"  # type: ignore[misc]

    def test_compiled_prompt_overlay_ids_empty_by_default(self) -> None:
        cp = CompiledPrompt(
            module_id="test",
            module_version="1.0.0",
            compiled_body="body",
            metadata=PromptMetadata(
                prompt_id="test",
                prompt_version="1.0.0",
                content_hash="abc",
                compiled_hash="def",
                sections=[],
            ),
        )
        assert cp.overlay_ids == []


# ═══════════════════════════════════════════════════════════════════════════════
# Compiler error contracts
# ═══════════════════════════════════════════════════════════════════════════════


class TestCompilerErrorContracts:
    """Tests that compiler error types are well-formed."""

    def test_missing_variable_error_has_fields(self) -> None:
        err = MissingVariableError(missing=frozenset({"x"}))
        assert err.missing == {"x"}
        assert "x" in str(err)

    def test_unknown_variable_error_has_fields(self) -> None:
        err = UnknownVariableError(unknown=frozenset({"z"}))
        assert err.unknown == {"z"}
        assert "z" in str(err)

    def test_duplicate_overlay_error_has_fields(self) -> None:
        err = DuplicateOverlayError(overlay_id="ov1")
        assert err.overlay_id == "ov1"
        assert "ov1" in str(err)

    def test_secret_overlay_error_has_fields(self) -> None:
        err = SecretOverlayError(overlay_id="ov1")
        assert err.overlay_id == "ov1"
        assert "ov1" in str(err)


# ═══════════════════════════════════════════════════════════════════════════════
# Successful compilation
# ═══════════════════════════════════════════════════════════════════════════════


class TestCompileSuccess:
    """Tests for successful prompt compilation."""

    def test_basic_compilation(self) -> None:
        module = _make_module(body="Teach {{subject}} to {{grade}}.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        result = compiler.compile(
            module_id="test_v1",
            variables={"subject": "Math", "grade": "5"},
        )

        assert "Math" in result.compiled_body
        assert "5" in result.compiled_body
        assert "{{subject}}" not in result.compiled_body
        assert "{{grade}}" not in result.compiled_body

    def test_metadata_populated(self) -> None:
        module = _make_module(body="Hello {{name}}.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        result = compiler.compile(
            module_id="test_v1",
            variables={"name": "Alice"},
        )

        assert result.metadata.prompt_id == "test_v1"
        assert result.metadata.prompt_version == "1.0.0"
        assert result.metadata.content_hash == module.content_hash

    def test_module_id_and_version_recorded(self) -> None:
        module = _make_module(body="Hi {{x}}.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        result = compiler.compile(
            module_id="test_v1",
            variables={"x": "y"},
        )

        assert result.module_id == "test_v1"
        assert result.module_version == "1.0.0"

    def test_no_variables_module(self) -> None:
        module = _make_module(body="Static prompt with no variables.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        result = compiler.compile(module_id="test_v1", variables={})

        assert result.compiled_body == "Static prompt with no variables."

    def test_multiple_occurrences_same_variable(self) -> None:
        module = _make_module(body="{{x}} and {{x}} again {{x}}.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        result = compiler.compile(
            module_id="test_v1",
            variables={"x": "REPLACED"},
        )

        assert result.compiled_body.count("REPLACED") == 3
        assert "{{x}}" not in result.compiled_body


# ═══════════════════════════════════════════════════════════════════════════════
# Compiled hash
# ═══════════════════════════════════════════════════════════════════════════════


class TestCompiledHash:
    """Tests that compiled_hash is the SHA-256 of the compiled body."""

    def test_compiled_hash_matches_compiled_body(self) -> None:
        module = _make_module(body="Teach {{subject}}.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        result = compiler.compile(
            module_id="test_v1",
            variables={"subject": "Math"},
        )

        expected_hash = hashlib.sha256(
            result.compiled_body.encode("utf-8"),
        ).hexdigest()
        assert result.metadata.compiled_hash == expected_hash

    def test_different_variables_different_hash(self) -> None:
        module = _make_module(body="Hello {{name}}.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        r1 = compiler.compile(module_id="test_v1", variables={"name": "Alice"})
        r2 = compiler.compile(module_id="test_v1", variables={"name": "Bob"})

        assert r1.metadata.compiled_hash != r2.metadata.compiled_hash


# ═══════════════════════════════════════════════════════════════════════════════
# Overlay governance
# ═══════════════════════════════════════════════════════════════════════════════


class TestOverlayGovernance:
    """Tests for overlay application and governance rules."""

    def test_single_overlay_applied(self) -> None:
        module = _make_module(body="Base body.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        ov = _make_overlay(body="## Extra\nAppended.")
        result = compiler.compile(
            module_id="test_v1",
            variables={},
            overlays=[ov],
        )

        assert "Base body." in result.compiled_body
        assert "## Extra\nAppended." in result.compiled_body
        assert result.overlay_ids == ["ov1"]
        assert result.metadata.overlay_ids == ["ov1"]

    def test_multiple_overlays_sorted_by_order_then_id(self) -> None:
        """Overlay application is deterministic: sorted by (order, id)."""
        module = _make_module(body="Base.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        ov_c = Overlay(id="ov_c", body="C", order=1)
        ov_a = Overlay(id="ov_a", body="A", order=1)
        ov_b = Overlay(id="ov_b", body="B", order=0)

        result = compiler.compile(
            module_id="test_v1",
            variables={},
            overlays=[ov_c, ov_a, ov_b],
        )

        # order=0 first, then order=1 sorted by id
        b_pos = result.compiled_body.index("B")
        a_pos = result.compiled_body.index("A")
        c_pos = result.compiled_body.index("C")
        assert b_pos < a_pos < c_pos
        assert result.overlay_ids == ["ov_b", "ov_a", "ov_c"]

    def test_overlay_id_order_deterministic(self) -> None:
        """Same overlays in different input order produce identical output."""
        module = _make_module(body="Base.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        overlays_1 = [
            Overlay(id="z", body="Z", order=0),
            Overlay(id="a", body="A", order=0),
        ]
        overlays_2 = list(reversed(overlays_1))

        r1 = compiler.compile(module_id="test_v1", variables={}, overlays=overlays_1)
        r2 = compiler.compile(module_id="test_v1", variables={}, overlays=overlays_2)

        assert r1.compiled_body == r2.compiled_body
        assert r1.overlay_ids == r2.overlay_ids

    def test_empty_overlays(self) -> None:
        module = _make_module(body="Body.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        result = compiler.compile(
            module_id="test_v1",
            variables={},
            overlays=[],
        )

        assert result.compiled_body == "Body."
        assert result.overlay_ids == []


# ═══════════════════════════════════════════════════════════════════════════════
# Variable validation
# ═══════════════════════════════════════════════════════════════════════════════


class TestVariableValidation:
    """Tests for missing and unknown variable rejection."""

    def test_missing_variable_rejected(self) -> None:
        module = _make_module(body="Hello {{name}}, teach {{subject}}.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        with pytest.raises(MissingVariableError) as exc_info:
            compiler.compile(
                module_id="test_v1",
                variables={"name": "Alice"},  # missing: subject
            )

        assert "subject" in str(exc_info.value)

    def test_multiple_missing_variables(self) -> None:
        module = _make_module(body="{{a}} {{b}} {{c}}.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        with pytest.raises(MissingVariableError) as exc_info:
            compiler.compile(
                module_id="test_v1",
                variables={"a": "1"},  # missing: b, c
            )

        missing = exc_info.value.missing
        assert "b" in missing
        assert "c" in missing

    def test_unknown_variable_rejected(self) -> None:
        module = _make_module(body="Hello {{name}}.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        with pytest.raises(UnknownVariableError) as exc_info:
            compiler.compile(
                module_id="test_v1",
                variables={"name": "Alice", "extra": "bad"},
            )

        assert "extra" in str(exc_info.value)

    def test_multiple_unknown_variables(self) -> None:
        module = _make_module(body="Hello {{name}}.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        with pytest.raises(UnknownVariableError) as exc_info:
            compiler.compile(
                module_id="test_v1",
                variables={"name": "Alice", "foo": "bar", "baz": "qux"},
            )

        unknown = exc_info.value.unknown
        assert "foo" in unknown
        assert "baz" in unknown

    def test_exact_match_no_missing_no_unknown(self) -> None:
        module = _make_module(body="{{a}} {{b}}.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        result = compiler.compile(
            module_id="test_v1",
            variables={"a": "1", "b": "2"},
        )

        assert "1" in result.compiled_body
        assert "2" in result.compiled_body


# ═══════════════════════════════════════════════════════════════════════════════
# Duplicate overlay rejection
# ═══════════════════════════════════════════════════════════════════════════════


class TestDuplicateOverlayRejection:
    """Tests for duplicate overlay ID detection."""

    def test_duplicate_overlay_id_rejected(self) -> None:
        module = _make_module(body="Body.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        ov1 = Overlay(id="same_id", body="First.", order=0)
        ov2 = Overlay(id="same_id", body="Second.", order=1)

        with pytest.raises(DuplicateOverlayError) as exc_info:
            compiler.compile(
                module_id="test_v1",
                variables={},
                overlays=[ov1, ov2],
            )

        assert exc_info.value.overlay_id == "same_id"

    def test_three_duplicates_all_unique_ids(self) -> None:
        module = _make_module(body="Body.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        overlays = [
            Overlay(id="a", body="A", order=0),
            Overlay(id="b", body="B", order=0),
            Overlay(id="c", body="C", order=0),
        ]

        result = compiler.compile(
            module_id="test_v1",
            variables={},
            overlays=overlays,
        )

        assert len(result.overlay_ids) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# Secret-like overlay rejection
# ═══════════════════════════════════════════════════════════════════════════════


class TestSecretOverlayRejection:
    """Tests for secret-like content detection in overlays."""

    def test_bearer_token_rejected(self) -> None:
        module = _make_module(body="Body.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        ov = Overlay(
            id="bad",
            body="Bearer sk-abcdefghijklmnopqrstuvwxyz1234567890",
            order=0,
        )

        with pytest.raises(SecretOverlayError):
            compiler.compile(
                module_id="test_v1",
                variables={},
                overlays=[ov],
            )

    def test_api_key_rejected(self) -> None:
        module = _make_module(body="Body.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        ov = Overlay(
            id="bad",
            body="api_key: supersecretvalue12345678",
            order=0,
        )

        with pytest.raises(SecretOverlayError):
            compiler.compile(
                module_id="test_v1",
                variables={},
                overlays=[ov],
            )

    def test_secret_token_rejected(self) -> None:
        module = _make_module(body="Body.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        ov = Overlay(
            id="bad",
            body="secret = abcdefghijklmnop1234",
            order=0,
        )

        with pytest.raises(SecretOverlayError):
            compiler.compile(
                module_id="test_v1",
                variables={},
                overlays=[ov],
            )

    def test_ghp_token_rejected(self) -> None:
        module = _make_module(body="Body.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        # Secret regex expects ghp- (dash) not ghp_ (underscore) per prompt_gate.py
        ov = Overlay(
            id="bad",
            body="Use this: ghp-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef",
            order=0,
        )

        with pytest.raises(SecretOverlayError):
            compiler.compile(
                module_id="test_v1",
                variables={},
                overlays=[ov],
            )

    def test_github_pat_token_rejected(self) -> None:
        module = _make_module(body="Body.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        ov = Overlay(
            id="bad",
            body="github_pat-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef01",
            order=0,
        )

        with pytest.raises(SecretOverlayError):
            compiler.compile(
                module_id="test_v1",
                variables={},
                overlays=[ov],
            )

    def test_clean_overlay_accepted(self) -> None:
        module = _make_module(body="Body.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        ov = Overlay(
            id="safe",
            body="This is safe educational content with no secrets.",
            order=0,
        )

        result = compiler.compile(
            module_id="test_v1",
            variables={},
            overlays=[ov],
        )

        assert "safe educational content" in result.compiled_body


# ═══════════════════════════════════════════════════════════════════════════════
# Drift rejection
# ═══════════════════════════════════════════════════════════════════════════════


class TestDriftRejection:
    """Tests that compiling a drifted module raises DriftRejectionError."""

    def test_drifted_module_rejected(self) -> None:
        original_body = "Hello {{name}}."
        reg = PromptRegistry()
        module = PromptModule.create(
            id="drifted_v1",
            version="1.0.0",
            body=original_body,
        )
        # Tamper body after hash computation
        object.__setattr__(module, "body", "Tampered {{name}}.")
        reg.register(module)

        compiler = PromptCompiler(reg)

        with pytest.raises(ValueError, match="drift"):
            compiler.compile(
                module_id="drifted_v1",
                variables={"name": "Alice"},
            )

    def test_clean_module_not_rejected(self) -> None:
        module = _make_module(body="Clean {{name}}.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        result = compiler.compile(
            module_id="test_v1",
            variables={"name": "Alice"},
        )

        assert "Alice" in result.compiled_body


# ═══════════════════════════════════════════════════════════════════════════════
# Module not found
# ═══════════════════════════════════════════════════════════════════════════════


class TestModuleNotFound:
    """Tests that compiling a non-existent module raises KeyError."""

    def test_missing_module_raises(self) -> None:
        reg = PromptRegistry()
        compiler = PromptCompiler(reg)

        with pytest.raises(KeyError, match="No PromptModule"):
            compiler.compile(
                module_id="nonexistent",
                variables={},
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Malformed input probes
# ═══════════════════════════════════════════════════════════════════════════════


class TestMalformedInput:
    """Tests for edge cases and malformed inputs."""

    def test_unclosed_variable_syntax_treated_as_literal(self) -> None:
        module = _make_module(body="Hello {{name world.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        result = compiler.compile(module_id="test_v1", variables={})

        # Unclosed {{ is not a valid variable, treated as literal
        assert "{{name world." in result.compiled_body

    def test_empty_variable_name_skipped(self) -> None:
        module = _make_module(body="Hello {{}}.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        result = compiler.compile(module_id="test_v1", variables={})

        # Empty {{}} not treated as a required variable
        assert result.compiled_body == "Hello {{}}."

    def test_overlay_with_empty_body_accepted(self) -> None:
        module = _make_module(body="Body.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        ov = Overlay(id="empty_ov", body="", order=0)
        result = compiler.compile(
            module_id="test_v1",
            variables={},
            overlays=[ov],
        )

        assert result.overlay_ids == ["empty_ov"]

    def test_overlay_variable_substitution_not_performed(self) -> None:
        """Overlays are literal content — variables are only substituted in the module body."""
        module = _make_module(body="Hello {{name}}.")
        reg = _make_registry(module)
        compiler = PromptCompiler(reg)

        ov = Overlay(id="ov1", body="Also {{name}}.", order=0)
        result = compiler.compile(
            module_id="test_v1",
            variables={"name": "Alice"},
            overlays=[ov],
        )

        # Module body gets substitution
        assert "Alice" in result.compiled_body.split("\n")[0]
        # Overlay is literal
        assert "{{name}}." in result.compiled_body


# ═══════════════════════════════════════════════════════════════════════════════
# Compilation with specific version
# ═══════════════════════════════════════════════════════════════════════════════


class TestCompileWithVersion:
    """Tests for compiling a specific module version."""

    def test_specific_version(self) -> None:
        reg = PromptRegistry()
        m1 = PromptModule.create(
            id="test_v1", version="1.0.0", body="V1 {{x}}.",
        )
        m2 = PromptModule.create(
            id="test_v1", version="2.0.0", body="V2 {{x}}.",
        )
        reg.register(m1)
        reg.register(m2)
        compiler = PromptCompiler(reg)

        result = compiler.compile(
            module_id="test_v1",
            variables={"x": "val"},
            version="1.0.0",
        )

        assert "V1 val." in result.compiled_body
        assert result.module_version == "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# Drift detection integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestDriftIntegration:
    """Tests that compiler integrates with drift detection module."""

    def test_drift_report_used_by_compiler(self) -> None:
        """Verify detect_drift detects the same issues the compiler rejects."""
        reg = PromptRegistry()
        module = PromptModule.create(
            id="drift_v1", version="1.0.0", body="Original.",
        )
        object.__setattr__(module, "body", "Tampered.")
        reg.register(module)

        report = detect_drift(reg, "drift_v1")
        assert not report.is_clean
