"""Prompt module registry with version tracking and content hash validation.

Provides typed dataclasses and a registry for managing versioned prompt modules
used by the LangGraph agent pipeline. Every prompt module carries a content hash
(SHA-256 of the body) so drift between the declared hash and the actual body can
be detected at runtime.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field


def _sha256(content: str) -> str:
    """Return hex-encoded SHA-256 of *content*."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _validate_semver(version: str) -> None:
    """Raise ValueError if *version* is not valid semver."""
    if not _SEMVER_RE.match(version):
        raise ValueError(
            f"Invalid semver '{version}'. Expected format: MAJOR.MINOR.PATCH (e.g. 1.0.0)",
        )


# ── PromptModule ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PromptModule:
    """A versioned, hash-validated prompt module.

    Attributes:
        id: Stable identifier, e.g. ``"planner_v1"``.
        version: Semver string, e.g. ``"1.2.0"``.
        body: Markdown template body of the prompt.
        output_schema: Expected JSON structure returned by the LLM, or None.
        content_hash: SHA-256 hex digest of *body*.  Computed automatically
            when using ``PromptModule.create()``.
        metadata: Arbitrary metadata (task, locale, subject, artifact_type, etc.).
    """

    id: str
    version: str
    body: str
    output_schema: dict[str, object] | None = None
    content_hash: str = ""
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_semver(self.version)
        # Auto-compute content_hash if not supplied.
        computed = _sha256(self.body)
        if not self.content_hash:
            # frozen dataclass → use object.__setattr__
            object.__setattr__(self, "content_hash", computed)
        elif self.content_hash != computed:
            raise ValueError(
                f"Content hash mismatch for '{self.id}': "
                f"declared={self.content_hash[:16]}… computed={computed[:16]}…",
            )

    # Convenience factory ------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        id: str,
        version: str,
        body: str,
        output_schema: dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> PromptModule:
        """Create a PromptModule with an auto-computed content hash."""
        return cls(
            id=id,
            version=version,
            body=body,
            output_schema=output_schema,
            content_hash=_sha256(body),
            metadata=metadata or {},
        )


# ── PromptRegistry ──────────────────────────────────────────────────────────


class PromptRegistry:
    """In-memory registry of :class:`PromptModule` instances.

    Modules are keyed by ``(id, version)``.  Calling :meth:`register` with the
    same *id* + *version* pair raises ``ValueError``.
    """

    def __init__(self) -> None:
        self._modules: dict[str, dict[str, PromptModule]] = {}

    # ── public API ───────────────────────────────────────────────────────

    def register(self, module: PromptModule) -> None:
        """Register a prompt module.  Raises if id+version already exists."""
        versions = self._modules.setdefault(module.id, {})
        if module.version in versions:
            raise ValueError(
                f"PromptModule '{module.id}' version '{module.version}' already registered",
            )
        versions[module.version] = module

    def get(self, module_id: str, version: str | None = None) -> PromptModule:
        """Return a module by *module_id*.

        If *version* is ``None``, return the highest registered version
        (by semver sort).
        """
        versions = self._modules.get(module_id)
        if not versions:
            raise KeyError(f"No PromptModule with id '{module_id}'")

        if version is not None:
            if version not in versions:
                raise KeyError(
                    f"PromptModule '{module_id}' has no version '{version}'. "
                    f"Available: {sorted(versions)}",
                )
            return versions[version]

        # Return the highest version.
        latest_key = max(versions.keys(), key=_semver_sort_key)
        return versions[latest_key]

    def list_versions(self, module_id: str) -> list[str]:
        """Return sorted version strings for *module_id*."""
        versions = self._modules.get(module_id)
        if not versions:
            raise KeyError(f"No PromptModule with id '{module_id}'")
        return sorted(versions.keys(), key=_semver_sort_key)

    def validate_hash(self, module_id: str, version: str | None = None) -> bool:
        """Check that the module's body matches its declared content_hash."""
        module = self.get(module_id, version)
        return module.content_hash == _sha256(module.body)

    def list_all(self) -> list[PromptModule]:
        """Return all registered modules (latest version per id)."""
        result: list[PromptModule] = []
        for mid in self._modules:
            result.append(self.get(mid))
        return result


# ── helpers ─────────────────────────────────────────────────────────────────


def _semver_sort_key(v: str) -> tuple[int, int, int]:
    """Parse ``"X.Y.Z"`` into ``(X, Y, Z)`` for sorting."""
    major, minor, patch = v.split(".")
    return (int(major), int(minor), int(patch))
