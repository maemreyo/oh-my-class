from __future__ import annotations

from packages.agents.tools.fs import write_file as sandboxed_write_file


async def write_file(
    path: str,
    content: str,
    encoding: str = "utf-8",
    *,
    overwrite: bool = False,
) -> bool:
    return await sandboxed_write_file(
        path,
        content,
        encoding=encoding,
        overwrite=overwrite,
    )
