from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

_PROJECT_ROOT: Final = Path(__file__).resolve().parents[3]
WRITE_AUDIT_LOG: list["FileWriteAuditEntry"] = []


@dataclass(frozen=True, slots=True)
class FileWriteAuditEntry:
    path: str
    bytes_written: int
    overwritten: bool


class ToolUnavailableError(Exception):
    fail_type = "tool_unavailable"

    def __init__(self, tool_name: str, reason: str) -> None:
        super().__init__(f"{tool_name}: {reason}")
        self.tool_name = tool_name
        self.reason = reason


def clear_write_audit_log() -> None:
    WRITE_AUDIT_LOG.clear()


def write_audit_log() -> tuple[FileWriteAuditEntry, ...]:
    return tuple(WRITE_AUDIT_LOG)


async def read_file(path: str, encoding: str = "utf-8") -> str:
    resolved = _sandbox_path(path)
    return resolved.read_text(encoding=encoding)


async def write_file(
    path: str,
    content: str,
    encoding: str = "utf-8",
    *,
    overwrite: bool = False,
) -> bool:
    resolved = _sandbox_path(path)
    existed = resolved.exists()
    if existed and not overwrite:
        return False
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding=encoding)
    WRITE_AUDIT_LOG.append(FileWriteAuditEntry(
        path=str(resolved.relative_to(_PROJECT_ROOT)) if resolved.is_relative_to(_PROJECT_ROOT) else str(resolved),
        bytes_written=len(content.encode(encoding)),
        overwritten=existed,
    ))
    return True


def _sandbox_path(path: str) -> Path:
    candidate = Path(path)
    resolved = candidate.resolve() if candidate.is_absolute() else (_PROJECT_ROOT / candidate).resolve()
    if resolved == _PROJECT_ROOT or _PROJECT_ROOT in resolved.parents:
        return resolved
    raise ToolUnavailableError("fs", "path outside workspace sandbox")
