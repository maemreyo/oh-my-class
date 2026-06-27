"""Template module registry with version tracking and content hash validation.

Manages versioned HTML template modules used by the Eta-based renderer to
produce standalone artifact HTML.  Each template carries a SHA-256 content
hash so integrity can be verified before rendering.
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


@dataclass(frozen=True, slots=True)
class TemplateModule:
    """A versioned, hash-validated template module.

    Attributes:
        id: Stable identifier, e.g. ``"lesson_v1"``.
        version: Semver string, e.g. ``"1.0.0"``.
        path: Relative path to the ``.html`` template file.
        content_hash: SHA-256 hex digest of the template file content.
        artifact_types: Which artifact types use this template.
        metadata: Arbitrary metadata (author, description, etc.).
    """

    id: str
    version: str
    path: str
    content_hash: str = ""
    artifact_types: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_semver(self.version)


class TemplateRegistry:
    """In-memory registry of :class:`TemplateModule` instances."""

    def __init__(self) -> None:
        self._modules: dict[str, dict[str, TemplateModule]] = {}

    def register(self, module: TemplateModule) -> None:
        """Register a template module.  Raises if id+version already exists."""
        versions = self._modules.setdefault(module.id, {})
        if module.version in versions:
            raise ValueError(
                f"TemplateModule '{module.id}' version '{module.version}' already registered",
            )
        versions[module.version] = module

    def get(self, module_id: str, version: str | None = None) -> TemplateModule:
        """Return a module by *module_id*.

        If *version* is ``None``, return the highest registered version.
        """
        versions = self._modules.get(module_id)
        if not versions:
            raise KeyError(f"No TemplateModule with id '{module_id}'")

        if version is not None:
            if version not in versions:
                raise KeyError(
                    f"TemplateModule '{module_id}' has no version '{version}'. "
                    f"Available: {sorted(versions)}",
                )
            return versions[version]

        latest_key = max(versions.keys(), key=_semver_sort_key)
        return versions[latest_key]

    def validate_hash(self, module_id: str, content: str, version: str | None = None) -> bool:
        """Check that *content* matches the registered hash for this module.

        Unlike prompt registry's validate_hash (which checks body against
        stored hash), this takes the actual file content since templates are
        loaded from disk.

        Args:
            module_id: Module identifier.
            content: The actual template file content to validate.
            version: Optional specific version.

        Returns:
            True if content hash matches the registered hash.
        """
        module = self.get(module_id, version)
        return module.content_hash == _sha256(content)


def _semver_sort_key(v: str) -> tuple[int, int, int]:
    """Parse ``"X.Y.Z"`` into ``(X, Y, Z)`` for sorting."""
    major, minor, patch = v.split(".")
    return (int(major), int(minor), int(patch))
