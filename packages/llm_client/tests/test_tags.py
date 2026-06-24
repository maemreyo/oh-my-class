"""Tests for build_tags() cost attribution metadata."""
from __future__ import annotations

import pytest

from packages.llm_client.tags import build_tags


def test_build_tags_structure():
    tags = build_tags("content_creator", "content_generation", "run-123")
    assert "metadata" in tags
    assert "tags" in tags["metadata"]
    assert isinstance(tags["metadata"]["tags"], list)


def test_build_tags_with_run_id():
    tags = build_tags("content_creator", "content_generation", "run-123")
    tag_list = tags["metadata"]["tags"]
    assert "agent:content_creator" in tag_list
    assert "task:content_generation" in tag_list
    assert "run_id:run-123" in tag_list
    assert "pipeline:oh-my-class" in tag_list


def test_build_tags_no_run_id():
    tags = build_tags("llm_judge", "quality_gate")
    tag_list = tags["metadata"]["tags"]
    assert "agent:llm_judge" in tag_list
    assert "task:quality_gate" in tag_list
    assert "pipeline:oh-my-class" in tag_list
    assert not any(t.startswith("run_id:") for t in tag_list)


def test_build_tags_run_id_none():
    tags = build_tags("researcher", "fact_verification", run_id=None)
    tag_list = tags["metadata"]["tags"]
    assert not any(t.startswith("run_id:") for t in tag_list)


def test_build_tags_pipeline_always_present():
    for agent in ["content_creator", "planner", "researcher", "llm_judge"]:
        tags = build_tags(agent, "some_task")
        assert "pipeline:oh-my-class" in tags["metadata"]["tags"]
