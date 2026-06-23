"""Read file tool — stub implementation.

Allows agents to read files from the workspace. Used by all sub-agents
for reading templates, configs, and reference materials.
"""

from __future__ import annotations


async def read_file(
    path: str,
    encoding: str = "utf-8",
) -> str:
    """Read a file from the workspace.

    Args:
        path: Relative or absolute file path.
        encoding: File encoding (default: utf-8).

    Returns:
        File contents as a string.
    """
    # TODO: Implement with sandboxed file system access
    raise NotImplementedError("read_file stub — implement with filesystem access")
