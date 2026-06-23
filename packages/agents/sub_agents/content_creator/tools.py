"""Content Creator Agent tools — read_file and write_file.

Tools available to the Content Creator Agent for reading templates
and writing generated artifacts.
"""

from __future__ import annotations


async def read_file(path: str) -> str:
    """Read a file from the workspace (templates, reference materials).

    Args:
        path: File path to read.

    Returns:
        File contents as string.
    """
    with open(path) as f:
        return f.read()


async def write_file(path: str, content: str, *, overwrite: bool = False) -> bool:
    """Write generated artifact content to the workspace.

    Args:
        path: File path to write to.
        content: Content string to write.
        overwrite: If True, overwrite existing file.

    Returns:
        True on success.
    """
    import os

    if not overwrite and os.path.exists(path):
        return False
    with open(path, "w") as f:
        f.write(content)
    return True
