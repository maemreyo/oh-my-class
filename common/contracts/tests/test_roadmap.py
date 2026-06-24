"""Tests for RoadmapContent model."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.roadmap import (
    RoadmapContent,
    RoadmapSection,
    RoadmapHero,
    RoadmapSidebar,
    NavItem,
    LegendItem,
)
from common.contracts.components import StatCard, PhaseTimeline


class TestNavItem:
    def test_valid(self):
        n = NavItem(label="Phase 1", href="#phase-1")
        assert n.group == "a"

    def test_custom_group(self):
        n = NavItem(label="P2", href="#p2", group="b")
        assert n.group == "b"


class TestLegendItem:
    def test_valid(self):
        li = LegendItem(color="#33508F", label="Grammar")
        assert li.color == "#33508F"


class TestRoadmapHero:
    def test_defaults(self):
        h = RoadmapHero(title="My Roadmap")
        assert h.eyebrow == ""
        assert h.lede == ""
        assert h.stamp == ""
        assert h.stats == []

    def test_with_stats(self):
        h = RoadmapHero(
            title="English Roadmap",
            eyebrow="Personalized Plan",
            lede="Based on your diagnostic results",
            stamp="6 months",
            stats=[StatCard(label="Current", value="65%"), StatCard(label="Target", value="85%", variant="target")],
        )
        assert len(h.stats) == 2


class TestRoadmapSidebar:
    def test_minimal(self):
        sb = RoadmapSidebar(title="My Plan", subtitle="Learning Journey")
        assert sb.stats == []
        assert sb.nav == []
        assert sb.legend == []

    def test_with_all_fields(self):
        sb = RoadmapSidebar(
            title="Plan",
            subtitle="6-month English",
            stats=[StatCard(label="Score", value="65%")],
            nav=[NavItem(label="Phase 1", href="#p1")],
            legend=[LegendItem(color="#33508F", label="Grammar")],
        )
        assert len(sb.stats) == 1
        assert len(sb.nav) == 1
        assert len(sb.legend) == 1


class TestRoadmapSection:
    def test_minimal(self):
        s = RoadmapSection(id="s1", title="Phase 1")
        assert s.subtitle is None
        assert s.tag_num is None
        assert s.components == []

    def test_with_timeline(self):
        pt = PhaseTimeline(phases=[])
        s = RoadmapSection(
            id="phase-1",
            title="Foundation",
            subtitle="Month 1-2",
            tag_num="01",
            components=[pt],
        )
        assert len(s.components) == 1


class TestRoadmapContent:
    def _make_hero(self):
        return RoadmapHero(title="My Plan")

    def _make_sidebar(self):
        return RoadmapSidebar(title="Plan", subtitle="6 months")

    def test_minimal(self):
        rc = RoadmapContent(
            title="Learning Roadmap",
            hero=self._make_hero(),
            sidebar=self._make_sidebar(),
        )
        assert rc.artifact_type == "roadmap"
        assert rc.theme == "default"
        assert rc.sections == []

    def test_accessibility_default(self):
        rc = RoadmapContent(
            title="Test",
            hero=self._make_hero(),
            sidebar=self._make_sidebar(),
        )
        assert rc.accessibility.get("language") == "vi"

    def test_artifact_type_locked(self):
        rc = RoadmapContent(
            title="Test",
            hero=self._make_hero(),
            sidebar=self._make_sidebar(),
        )
        assert rc.artifact_type == "roadmap"

    def test_invalid_artifact_type_rejected(self):
        with pytest.raises(ValidationError):
            RoadmapContent(
                title="Test",
                hero=self._make_hero(),
                sidebar=self._make_sidebar(),
                artifact_type="lesson",
            )

    def test_with_sections(self):
        rc = RoadmapContent(
            title="Plan",
            hero=self._make_hero(),
            sidebar=self._make_sidebar(),
            sections=[
                RoadmapSection(id="s1", title="Phase 1"),
                RoadmapSection(id="s2", title="Phase 2"),
            ],
        )
        assert len(rc.sections) == 2

    def test_json_roundtrip(self):
        rc = RoadmapContent(
            title="Roundtrip",
            hero=self._make_hero(),
            sidebar=self._make_sidebar(),
        )
        data = rc.model_dump()
        rc2 = RoadmapContent.model_validate(data)
        assert rc2.title == rc.title
        assert rc2.artifact_type == "roadmap"
