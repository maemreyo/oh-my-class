"""Reviewer Agent tools — read_file for artifact inspection.

The Reviewer Agent has minimal tool access — read-only for
inspecting generated artifacts.
"""

from __future__ import annotations


async def read_file(path: str) -> str:
    """Read a file from the workspace for quality inspection.

    Args:
        path: File path to read.

    Returns:
        File contents as string.
    """
    # TODO: Delegate to packages.agents.tools.read_file
    raise NotImplementedError("reviewer read_file stub")
