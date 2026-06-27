from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from packages.agents.pipeline_v2.checkpointing import open_pipeline_v2_postgres_checkpointer


class TestPipelineV2Checkpointing:
    def test_opens_postgres_checkpointer_context(self) -> None:
        checkpointer = MagicMock()
        context = MagicMock()
        context.__enter__.return_value = checkpointer
        postgres_saver = MagicMock()
        postgres_saver.from_conn_string.return_value = context
        postgres_module = MagicMock(PostgresSaver=postgres_saver)

        with (
            patch.dict(sys.modules, {"langgraph.checkpoint.postgres": postgres_module}),
            open_pipeline_v2_postgres_checkpointer("postgresql://db") as opened,
        ):
            assert opened is checkpointer

        postgres_saver.from_conn_string.assert_called_once_with("postgresql://db")
        checkpointer.setup.assert_called_once_with()
        context.__exit__.assert_called_once()

    def test_can_skip_setup_for_unit_tests(self) -> None:
        checkpointer = MagicMock()
        context = MagicMock()
        context.__enter__.return_value = checkpointer
        postgres_saver = MagicMock()
        postgres_saver.from_conn_string.return_value = context
        postgres_module = MagicMock(PostgresSaver=postgres_saver)

        with (
            patch.dict(sys.modules, {"langgraph.checkpoint.postgres": postgres_module}),
            open_pipeline_v2_postgres_checkpointer("postgresql://db", setup=False),
        ):
            pass

        checkpointer.setup.assert_not_called()
