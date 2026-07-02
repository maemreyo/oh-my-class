from __future__ import annotations

from pathlib import Path

import pytest

from services.gateway.vocabulary_batch_export import (
    VocabularyBatchExportRequest,
    export_vocabulary_batch_package,
)


@pytest.mark.asyncio
async def test_gateway_invokes_vocabulary_batch_cli_and_returns_zip_path(tmp_path: Path) -> None:
    cli = tmp_path / "vocab-cli.js"
    zip_path = tmp_path / "batch.vocabulary-batch.zip"
    cli.write_text(
        "const fs = require('node:fs');"
        "let raw = '';"
        "process.stdin.on('data', chunk => raw += chunk);"
        "process.stdin.on('end', () => {"
        " const payload = JSON.parse(raw);"
        f" fs.writeFileSync({str(zip_path)!r}, 'zip');"
        f" process.stdout.write(JSON.stringify({{ path: {str(zip_path)!r}, batchId: payload.batchId }}));"
        "});",
        encoding="utf-8",
    )

    result = await export_vocabulary_batch_package(
        VocabularyBatchExportRequest(
            batch_id="batch-runtime",
            title="Runtime Batch",
            output_dir=tmp_path,
            formats=["html"],
            clusters=[{"cluster": {"cluster_id": "c1"}}],
        ),
        cli_path=cli,
    )

    assert result == zip_path
    assert result.read_text(encoding="utf-8") == "zip"


@pytest.mark.asyncio
async def test_gateway_fails_closed_when_vocabulary_batch_cli_is_missing(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Vocabulary batch export CLI not built"):
        await export_vocabulary_batch_package(
            VocabularyBatchExportRequest(
                batch_id="batch-missing",
                title="Missing Batch",
                output_dir=tmp_path,
                formats=["html"],
                clusters=[],
            ),
            cli_path=tmp_path / "missing.js",
        )
