"""Schema versioning for Teaching Pack JSON contracts.

Every JSON contract emitted by the pipeline is tagged with a
``schema_version`` string.  This module provides validation and
migration helpers so that older contract versions can be upgraded to the
current version.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from services.gateway.teaching_pack_types import JsonObject

SCHEMA_VERSION: str = "1.0"
SUPPORTED_VERSIONS: frozenset[str] = frozenset({"0.9", "1.0"})


@runtime_checkable
class VersionedContract(Protocol):
    """Any object that carries a ``schema_version`` attribute."""

    @property
    def schema_version(self) -> str: ...


def validate_schema_version(version: str) -> bool:
    """Return ``True`` if *version* is the current or one previous version.

    Accepts:
      - ``SCHEMA_VERSION`` (current)
      - The immediately prior version (if one exists in ``SUPPORTED_VERSIONS``)

    Rejects:
      - Any version not in ``SUPPORTED_VERSIONS``
      - Any version string that is not a valid ``MAJOR.MINOR`` format
    """
    major_minor = version.split(".")
    if len(major_minor) != 2:
        return False
    if not all(part.isdecimal() for part in major_minor):
        return False
    return version in SUPPORTED_VERSIONS


def migrate_contract(
    data: JsonObject,
    from_version: str,
    to_version: str = SCHEMA_VERSION,
) -> JsonObject:
    """Migrate *data* from *from_version* to *to_version*.

    Handles the previous V2 draft shape ``0.9`` and the current ``1.0``.

    Raises:
        ValueError: If the source or target version is not supported.
    """
    if from_version not in SUPPORTED_VERSIONS:
        raise ValueError(f"Unsupported source version: {from_version}")
    if to_version not in SUPPORTED_VERSIONS:
        raise ValueError(f"Unsupported target version: {to_version}")

    migrated: JsonObject = dict(data)

    if from_version == "1.0" and to_version == "1.0":
        return migrated

    if from_version == "0.9" and to_version == "1.0":
        artifact_types = migrated.get("artifacts")
        if "artifact_types" not in migrated and isinstance(artifact_types, list):
            migrated["artifact_types"] = artifact_types
        language = migrated.get("language")
        if "instruction_language" not in migrated and isinstance(language, str):
            migrated["instruction_language"] = language
        migrated["schema_version"] = "1.0"
        return migrated

    # Future migrations go here, e.g.:
    # if from_version == "1.0" and to_version == "1.1":
    #     migrated["new_field"] = migrated.pop("old_field", None)
    #     migrated["schema_version"] = "1.1"
    #     return migrated

    return migrated
