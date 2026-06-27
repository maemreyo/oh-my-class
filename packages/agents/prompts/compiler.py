"""Prompt compiler with overlay governance and provenance.

Compiles a registered :class:`PromptModule` by:

1. Extracting declared ``{{variable}}`` placeholders from the module body.
2. Substituting typed variables into the body.
3. Applying approved overlays in deterministic order (sorted by ``(order, id)``).
4. Rejecting drift, missing/unknown variables, duplicate overlay IDs, and
   secret-like content in overlays.
5. Emitting a :class:`CompiledPrompt` with full provenance metadata.

No ad-hoc string concatenation — all assembly uses explicit ``str.join``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from packages.agents.llm.prompt_metadata import PromptMetadata, build_prompt_metadata
from packages.agents.prompts.drift import detect_drift

if TYPE_CHECKING:
    from packages.agents.prompts.registry import PromptModule, PromptRegistry

# ── Variable pattern ────────────────────────────────────────────────────────

_VAR_PATTERN: re.Pattern[str] = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}")


def _extract_variables(body: str) -> set[str]:
    """Return the set of declared variable names in *body*."""
    return set(_VAR_PATTERN.findall(body))


def _substitute_variables(body: str, variables: dict[str, str]) -> str:
    """Replace ``{{name}}`` placeholders with their values."""
    return _VAR_PATTERN.sub(lambda m: variables[m.group(1)], body)


# ── Secret detection (mirrors prompt_gate.py) ───────────────────────────────

_SECRET_PATTERN: re.Pattern[str] = re.compile(
    r"(?i)(Bearer\s+[A-Za-z0-9._~+/=-]{16,}|"
    r"(?:api[_-]?key|authorization|token|secret|password)\s*[:=]\s*[^\s,;]{8,}|"
    r"\b(?:sk|pk|rk|xoxb|ghp|github_pat)-[A-Za-z0-9_-]{20,}\b)",
)


def _has_secret_like_content(text: str) -> bool:
    """Return ``True`` if *text* matches any secret-like pattern."""
    return _SECRET_PATTERN.search(text) is not None


# ── Error types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class MissingVariableError(ValueError):
    """Raised when the module body declares variables not provided."""

    missing: frozenset[str]

    def __str__(self) -> str:
        sorted_names = sorted(self.missing)
        return f"Missing variables: {', '.join(sorted_names)}"


@dataclass(frozen=True, slots=True)
class UnknownVariableError(ValueError):
    """Raised when provided variables are not declared in the module body."""

    unknown: frozenset[str]

    def __str__(self) -> str:
        sorted_names = sorted(self.unknown)
        return f"Unknown variables: {', '.join(sorted_names)}"


@dataclass(frozen=True, slots=True)
class DuplicateOverlayError(ValueError):
    """Raised when two overlays share the same ``id``."""

    overlay_id: str

    def __str__(self) -> str:
        return f"Duplicate overlay id: '{self.overlay_id}'"


@dataclass(frozen=True, slots=True)
class SecretOverlayError(ValueError):
    """Raised when an overlay contains secret-like content."""

    overlay_id: str

    def __str__(self) -> str:
        return f"Secret-like content in overlay '{self.overlay_id}'"


@dataclass(frozen=True, slots=True)
class DriftRejectionError(ValueError):
    """Raised when the module has content drift."""

    module_id: str
    issues: list[str]

    def __str__(self) -> str:
        return f"Drift rejected for '{self.module_id}': {'; '.join(self.issues)}"


# ── Value objects ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Overlay:
    """An approved overlay to append to the compiled prompt body.

    Attributes:
        id: Stable, unique identifier for this overlay.
        body: Literal text content (no variable substitution).
        order: Sort key for deterministic application (lower = earlier).
    """

    id: str
    body: str
    order: int = 0


@dataclass(frozen=True, slots=True)
class CompiledPrompt:
    """Output of prompt compilation — the ready-to-send prompt plus provenance.

    Attributes:
        module_id: Identifier of the source module.
        module_version: Semver of the source module.
        compiled_body: Final prompt string (body with variables substituted,
            overlays appended in deterministic order).
        metadata: Provenance metadata for Langfuse tracing.
        overlay_ids: Ordered list of applied overlay identifiers.
    """

    module_id: str
    module_version: str
    compiled_body: str
    metadata: PromptMetadata
    overlay_ids: list[str] = field(default_factory=list)


# ── Compiler ─────────────────────────────────────────────────────────────────


class PromptCompiler:
    """Compiles registered prompt modules into ready-to-send prompts.

    Validates variables, overlay governance, and drift before compilation.
    Emits :class:`CompiledPrompt` with full provenance.

    Args:
        registry: The prompt registry to draw modules from.
    """

    def __init__(self, registry: PromptRegistry) -> None:
        self._registry = registry

    def compile(
        self,
        *,
        module_id: str,
        variables: dict[str, str],
        overlays: list[Overlay] | None = None,
        version: str | None = None,
    ) -> CompiledPrompt:
        """Compile a prompt module with variable substitution and overlay application.

        Steps:
            1. Fetch the module (drift check).
            2. Validate overlays (duplicates, secrets).
            3. Extract and validate variables.
            4. Substitute variables into the module body.
            5. Apply overlays in deterministic ``(order, id)`` order.
            6. Build provenance metadata.

        Args:
            module_id: Registry key of the prompt module.
            variables: Variable values keyed by declared name.
            overlays: Optional list of approved overlays.
            version: Optional specific module version.

        Returns:
            A :class:`CompiledPrompt` with the final body and provenance.

        Raises:
            KeyError: If *module_id* is not registered.
            DriftRejectionError: If the module has content drift.
            MissingVariableError: If the body declares variables not in *variables*.
            UnknownVariableError: If *variables* contains names not in the body.
            DuplicateOverlayError: If two overlays share an id.
            SecretOverlayError: If an overlay contains secret-like content.
        """
        # 1. Fetch and drift-check the module.
        module = self._registry.get(module_id, version)
        self._reject_drift(module)

        # 2. Validate overlays.
        overlay_list = overlays or []
        self._reject_duplicate_overlays(overlay_list)
        self._reject_secret_overlays(overlay_list)

        # 3. Extract and validate variables.
        declared = _extract_variables(module.body)
        self._reject_missing_variables(declared, variables)
        self._reject_unknown_variables(declared, variables)

        # 4. Substitute variables into the module body.
        compiled_body = _substitute_variables(module.body, variables)

        # 5. Apply overlays in deterministic order.
        sorted_overlays = sorted(overlay_list, key=lambda ov: (ov.order, ov.id))
        applied_ids: list[str] = []
        if sorted_overlays:
            overlay_bodies = [ov.body for ov in sorted_overlays]
            applied_ids = [ov.id for ov in sorted_overlays]
            compiled_body = "\n".join([compiled_body, *overlay_bodies])

        # 6. Build provenance metadata.
        metadata = build_prompt_metadata(module, compiled_body)

        return CompiledPrompt(
            module_id=module.id,
            module_version=module.version,
            compiled_body=compiled_body,
            metadata=metadata,
            overlay_ids=applied_ids,
        )

    # ── private validation helpers ──────────────────────────────────────────

    def _reject_drift(self, module: PromptModule) -> None:
        """Raise :class:`DriftRejectionError` if module has content drift."""
        report = detect_drift(self._registry, module.id)
        if not report.is_clean:
            raise DriftRejectionError(
                module_id=module.id,
                issues=report.issues,
            )

    @staticmethod
    def _reject_missing_variables(
        declared: set[str],
        provided: dict[str, str],
    ) -> None:
        """Raise :class:`MissingVariableError` for undeclared-supplied vars."""
        missing = declared - set(provided.keys())
        if missing:
            raise MissingVariableError(missing=frozenset(missing))

    @staticmethod
    def _reject_unknown_variables(
        declared: set[str],
        provided: dict[str, str],
    ) -> None:
        """Raise :class:`UnknownVariableError` for extra variables."""
        unknown = set(provided.keys()) - declared
        if unknown:
            raise UnknownVariableError(unknown=frozenset(unknown))

    @staticmethod
    def _reject_duplicate_overlays(overlays: list[Overlay]) -> None:
        """Raise :class:`DuplicateOverlayError` if any overlay id is repeated."""
        seen: set[str] = set()
        for ov in overlays:
            if ov.id in seen:
                raise DuplicateOverlayError(overlay_id=ov.id)
            seen.add(ov.id)

    @staticmethod
    def _reject_secret_overlays(overlays: list[Overlay]) -> None:
        """Raise :class:`SecretOverlayError` if overlay has secret-like content."""
        for ov in overlays:
            if _has_secret_like_content(ov.body):
                raise SecretOverlayError(overlay_id=ov.id)
