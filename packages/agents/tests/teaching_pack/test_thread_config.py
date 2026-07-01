from __future__ import annotations

from packages.agents.teaching_pack.graph import teaching_pack_thread_config


def test_thread_config_adds_default_max_concurrency(monkeypatch) -> None:
    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)

    config = teaching_pack_thread_config("run-1")

    assert config == {"configurable": {"thread_id": "run-1"}, "max_concurrency": 2}


def test_thread_config_respects_parallelism_cap(monkeypatch) -> None:
    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    monkeypatch.setenv("TEACHING_PACK_DEFAULT_ARTIFACT_PARALLELISM", "3")

    config = teaching_pack_thread_config("run-2")

    assert config == {"configurable": {"thread_id": "run-2"}, "max_concurrency": 3}
