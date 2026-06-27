"""Theme module registry with version tracking and content hash validation.

Manages versioned theme modules backed by ``theme.json`` files in the branding
kits directory.  Each module carries hashes for both the source JSON and the
generated CSS so integrity can be verified before rendering.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field


def _sha256(content: str | bytes) -> str:
    """Return hex-encoded SHA-256 of *content*."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _validate_semver(version: str) -> None:
    """Raise ValueError if *version* is not valid semver."""
    if not _SEMVER_RE.match(version):
        raise ValueError(
            f"Invalid semver '{version}'. Expected format: MAJOR.MINOR.PATCH (e.g. 1.0.0)",
        )


@dataclass(frozen=True, slots=True)
class ThemeModule:
    """A versioned, hash-validated theme module.

    Attributes:
        id: Stable identifier, e.g. ``"default"``, ``"ocean"``, ``"forest"``.
        version: Semver string, e.g. ``"1.0.0"``.
        path: Relative path to the ``theme.json`` file.
        content_hash: SHA-256 hex digest of the ``theme.json`` content.
        css_hash: SHA-256 hex digest of the generated CSS content.
        metadata: Arbitrary metadata (author, description, etc.).
    """

    id: str
    version: str
    path: str
    content_hash: str = ""
    css_hash: str = ""
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_semver(self.version)


class ThemeRegistry:
    """In-memory registry of :class:`ThemeModule` instances."""

    def __init__(self) -> None:
        self._modules: dict[str, ThemeModule] = {}

    def register(self, module: ThemeModule) -> None:
        """Register a theme module.  Raises if id already exists.

        Themes are keyed by id alone (not id+version) because a theme id like
        ``"ocean"`` should have exactly one active version at a time.  Registering
        a new version replaces the previous one.
        """
        self._modules[module.id] = module

    def get(self, module_id: str) -> ThemeModule:
        """Return a theme module by id."""
        if module_id not in self._modules:
            raise KeyError(f"No ThemeModule with id '{module_id}'")
        return self._modules[module_id]

    def validate_hash(self, module_id: str, json_content: str) -> bool:
        """Check that *json_content* matches the registered content_hash.

        Args:
            module_id: Theme module identifier.
            json_content: The actual theme.json file content to validate.

        Returns:
            True if the hash matches.
        """
        module = self.get(module_id)
        return module.content_hash == _sha256(json_content)

    def validate_css_hash(self, module_id: str, css_content: str) -> bool:
        """Check that *css_content* matches the registered css_hash.

        Args:
            module_id: Theme module identifier.
            css_content: The actual generated CSS content to validate.

        Returns:
            True if the hash matches.
        """
        module = self.get(module_id)
        return module.css_hash == _sha256(css_content)

    def list_all(self) -> list[ThemeModule]:
        """Return all registered theme modules."""
        return list(self._modules.values())
