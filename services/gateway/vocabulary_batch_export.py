from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, assert_never

from services.gateway.teaching_pack_export_writer import ExportAdapterError
from services.gateway.teaching_pack_types import JsonObject

type VocabularyBatchFormat = Literal["html", "gift", "h5p"]

_VOCABULARY_BATCH_CLI_PATH = Path("packages/exporters/dist/vocabulary-batch/cli.js")
_VOCABULARY_BATCH_TIMEOUT = 30.0


@dataclass(frozen=True, slots=True)
class VocabularyBatchExportRequest:
    batch_id: str
    title: str
    clusters: list[JsonObject]
    output_dir: Path
    formats: list[VocabularyBatchFormat]


async def export_vocabulary_batch_package(
    request: VocabularyBatchExportRequest,
    cli_path: Path = _VOCABULARY_BATCH_CLI_PATH,
) -> Path:
    if not cli_path.exists():
        raise ExportAdapterError(
            f"Vocabulary batch export CLI not built — run: pnpm --filter @oh-my-class/exporters build"
            f" (expected: {cli_path})"
        )
    payload = json.dumps(_payload(request), ensure_ascii=False).encode("utf-8")
    process = await _start_node(cli_path)
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(input=payload),
            timeout=_VOCABULARY_BATCH_TIMEOUT,
        )
    except TimeoutError:
        process.kill()
        await process.wait()
        raise ExportAdapterError(
            f"Vocabulary batch export CLI timed out after {_VOCABULARY_BATCH_TIMEOUT}s"
        ) from None
    return _parse_cli_result(process.returncode, stdout_bytes, stderr_bytes)


def _payload(request: VocabularyBatchExportRequest) -> JsonObject:
    return {
        "batchId": request.batch_id,
        "title": request.title,
        "clusters": request.clusters,
        "outputDir": str(request.output_dir),
        "formats": [_format_value(value) for value in request.formats],
    }


async def _start_node(cli_path: Path) -> asyncio.subprocess.Process:
    try:
        return await asyncio.create_subprocess_exec(
            "node",
            str(cli_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except (OSError, ValueError) as exc:
        raise ExportAdapterError(f"Failed to start vocabulary batch export CLI: {exc}") from exc


def _parse_cli_result(exit_code: int | None, stdout_bytes: bytes, stderr_bytes: bytes) -> Path:
    stdout_text = stdout_bytes.decode("utf-8") if stdout_bytes else ""
    stderr_text = stderr_bytes.decode("utf-8") if stderr_bytes else ""
    if exit_code != 0:
        raise ExportAdapterError(
            f"Vocabulary batch export CLI exited {exit_code}",
            exit_code=exit_code,
            stderr=stderr_text or None,
        )
    try:
        result = json.loads(stdout_text)
    except json.JSONDecodeError as exc:
        raise ExportAdapterError(f"Vocabulary batch export CLI returned invalid JSON: {stdout_text!r}") from exc
    path = result.get("path") if isinstance(result, dict) else None
    if not isinstance(path, str) or path == "":
        raise ExportAdapterError("Vocabulary batch export CLI did not return a path")
    return Path(path)


def _format_value(value: VocabularyBatchFormat) -> str:
    match value:
        case "html" | "gift" | "h5p":
            return value
        case unreachable:
            assert_never(unreachable)
