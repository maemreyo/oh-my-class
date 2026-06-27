"""Version drift detection for prompt modules.

Compares a module's declared ``content_hash`` against a recomputed hash of its
``body`` to detect tampering or un-bumped edits.  Also checks whether version
numbers were bumped after body changes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from packages.agents.prompts.registry import PromptModule, PromptRegistry


def _sha256(content: str) -> str:
    """Return hex-encoded SHA-256 of *content*."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class DriftReport:
    """Result of a drift check on a single prompt module.

    Attributes:
        module_id: The checked module identifier.
        issues: Human-readable issue descriptions.  Empty means clean.
        is_clean: ``True`` when no drift was detected.
    """

    module_id: str
    issues: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return len(self.issues) == 0


def detect_drift(registry: PromptRegistry, module_id: str) -> DriftReport:
    """Check a single module for content drift.

    Checks performed:

    1. **Hash mismatch** — recomputed SHA-256 of the body does not match the
       declared ``content_hash``.
    2. **Un-bumped version** — the body changed (hash mismatch) but the version
       was not incremented compared to the previous registered version.

    Args:
        registry: The prompt registry to inspect.
        module_id: Identifier of the module to check.

    Returns:
        A :class:`DriftReport` listing all detected issues.
    """
    issues: list[str] = []

    try:
        module = registry.get(module_id)
    except KeyError:
        return DriftReport(module_id=module_id, issues=[f"Module '{module_id}' not found in registry"])

    # 1. Hash mismatch
    recomputed = _sha256(module.body)
    if recomputed != module.content_hash:
        issues.append(
            f"Hash mismatch: declared={module.content_hash[:16]}… "
            f"recomputed={recomputed[:16]}…"
        )

    # 2. Version bump check — only meaningful when body was actually changed
    #    (i.e. when there IS a hash mismatch).
    if recomputed != module.content_hash:
        # If we have at least one prior version registered, check that the
        # version was bumped.  We can't truly compare against the *previous*
        # version's body (it's in the same module dataclass), so we check
        # whether version is "1.0.0" with a mismatched hash (common mistake).
        try:
            versions = registry.list_versions(module_id)
        except KeyError:
            versions = []

        if len(versions) == 1 and versions[0] == "1.0.0":
            issues.append(
                "Body changed without version bump: still at 1.0.0 "
                "with a hash mismatch",
            )

    return DriftReport(module_id=module_id, issues=issues)


def detect_drift_all(registry: PromptRegistry) -> list[DriftReport]:
    """Run drift detection across every module in the registry.

    Returns:
        List of :class:`DriftReport` for all registered module ids.
    """
    reports: list[DriftReport] = []
    # Collect unique module ids.
    seen: set[str] = set()
    for module in registry.list_all():
        if module.id not in seen:
            seen.add(module.id)
            reports.append(detect_drift(registry, module.id))
    return reports
