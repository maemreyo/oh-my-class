"""Tests for ContentComponent discriminated union — all 14 component types."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.components import (
    ContentComponent,
    Heading,
    Paragraph,
    Callout,
    OrderedList,
    UnorderedList,
    Table,
    StatGrid,
    StatCard,
    PatternGrid,
    PatternCard,
    TraitGrid,
    TraitCard,
    TaxonomyGrid,
    TaxonomyItem,
    PhaseTimeline,
    RoadmapPhase,
    PhaseBlock,
    FlowStep,
    FlowItem,
    QuestionCard,
    QuestionList,
    ConceptMap,
    TimelineComponent,
)
from pydantic import TypeAdapter


_COMPONENT_ADAPTER = TypeAdapter(ContentComponent)


# ── Heading ───────────────────────────────────────────────────────────────────

class TestHeading:
    def test_valid_h2(self):
        h = Heading(level=2, text="Chapter One")
        assert h.type == "heading"
        assert h.level == 2
        assert h.text == "Chapter One"
        assert h.id is None

    def test_valid_with_id(self):
        h = Heading(level=1, text="Title", id="title-anchor")
        assert h.id == "title-anchor"

    def test_invalid_level_0(self):
        with pytest.raises(ValidationError):
            Heading(level=0, text="bad")

    def test_invalid_level_5(self):
        with pytest.raises(ValidationError):
            Heading(level=5, text="bad")

    def test_all_valid_levels(self):
        for lvl in (1, 2, 3, 4):
            h = Heading(level=lvl, text="ok")
            assert h.level == lvl

    def test_discriminated_union_roundtrip(self):
        raw = {"type": "heading", "level": 3, "text": "Hi"}
        parsed = _COMPONENT_ADAPTER.validate_python(raw)
        assert isinstance(parsed, Heading)


# ── Paragraph ─────────────────────────────────────────────────────────────────

class TestParagraph:
    def test_valid(self):
        p = Paragraph(text="Hello world")
        assert p.type == "paragraph"

    def test_discriminated_union(self):
        raw = {"type": "paragraph", "text": "Sample"}
        parsed = _COMPONENT_ADAPTER.validate_python(raw)
        assert isinstance(parsed, Paragraph)

    def test_empty_text_valid(self):
        p = Paragraph(text="")
        assert p.text == ""


# ── Callout ───────────────────────────────────────────────────────────────────

class TestCallout:
    def test_note_variant(self):
        c = Callout(variant="note", body="This is a note")
        assert c.type == "callout"
        assert c.variant == "note"
        assert c.title is None

    def test_all_variants(self):
        for v in ("note", "warning", "tip", "alert"):
            c = Callout(variant=v, body="body")
            assert c.variant == v

    def test_invalid_variant(self):
        with pytest.raises(ValidationError):
            Callout(variant="danger", body="body")

    def test_with_title(self):
        c = Callout(variant="tip", title="Pro tip", body="Do it this way")
        assert c.title == "Pro tip"

    def test_discriminated_union(self):
        raw = {"type": "callout", "variant": "warning", "body": "watch out"}
        parsed = _COMPONENT_ADAPTER.validate_python(raw)
        assert isinstance(parsed, Callout)


# ── OrderedList / UnorderedList ───────────────────────────────────────────────

class TestLists:
    def test_ordered_list(self):
        ol = OrderedList(items=["a", "b", "c"])
        assert ol.type == "ordered_list"
        assert len(ol.items) == 3

    def test_unordered_list(self):
        ul = UnorderedList(items=["x", "y"])
        assert ul.type == "unordered_list"

    def test_empty_items(self):
        ol = OrderedList(items=[])
        assert ol.items == []

    def test_discriminated_union_ol(self):
        raw = {"type": "ordered_list", "items": ["one"]}
        assert isinstance(_COMPONENT_ADAPTER.validate_python(raw), OrderedList)

    def test_discriminated_union_ul(self):
        raw = {"type": "unordered_list", "items": ["one"]}
        assert isinstance(_COMPONENT_ADAPTER.validate_python(raw), UnorderedList)


# ── Table ─────────────────────────────────────────────────────────────────────

class TestTable:
    def test_valid(self):
        t = Table(columns=["A", "B"], rows=[["1", "2"], ["3", "4"]])
        assert t.type == "table"
        assert len(t.columns) == 2

    def test_caption_optional(self):
        t = Table(columns=["X"], rows=[])
        assert t.caption is None

    def test_with_caption(self):
        t = Table(columns=["X"], rows=[], caption="My table")
        assert t.caption == "My table"

    def test_discriminated_union(self):
        raw = {"type": "table", "columns": ["C1"], "rows": []}
        assert isinstance(_COMPONENT_ADAPTER.validate_python(raw), Table)


# ── StatGrid ──────────────────────────────────────────────────────────────────

class TestStatGrid:
    def test_valid(self):
        sg = StatGrid(stats=[
            StatCard(label="Score", value="85%"),
            StatCard(label="Target", value="90%", variant="target"),
        ])
        assert sg.type == "stat_grid"
        assert len(sg.stats) == 2

    def test_stat_card_default_variant(self):
        sc = StatCard(label="L", value="V")
        assert sc.variant == "default"

    def test_stat_card_variants(self):
        for v in ("target", "now", "default"):
            sc = StatCard(label="L", value="V", variant=v)
            assert sc.variant == v

    def test_invalid_variant(self):
        with pytest.raises(ValidationError):
            StatCard(label="L", value="V", variant="bad")

    def test_discriminated_union(self):
        raw = {"type": "stat_grid", "stats": [{"label": "L", "value": "V"}]}
        assert isinstance(_COMPONENT_ADAPTER.validate_python(raw), StatGrid)


# ── PatternGrid ───────────────────────────────────────────────────────────────

class TestPatternGrid:
    def test_valid(self):
        pg = PatternGrid(patterns=[
            PatternCard(id="C1", group="a", title="Pattern", description="desc"),
        ])
        assert pg.type == "pattern_grid"

    def test_empty_patterns(self):
        pg = PatternGrid(patterns=[])
        assert pg.patterns == []

    def test_discriminated_union(self):
        raw = {"type": "pattern_grid", "patterns": []}
        assert isinstance(_COMPONENT_ADAPTER.validate_python(raw), PatternGrid)


# ── TraitGrid ─────────────────────────────────────────────────────────────────

class TestTraitGrid:
    def test_valid(self):
        tg = TraitGrid(traits=[
            TraitCard(icon="🎬", title="Film Learner", body="Prefers video"),
        ])
        assert tg.type == "trait_grid"

    def test_discriminated_union(self):
        raw = {"type": "trait_grid", "traits": []}
        assert isinstance(_COMPONENT_ADAPTER.validate_python(raw), TraitGrid)


# ── TaxonomyGrid ──────────────────────────────────────────────────────────────

class TestTaxonomyGrid:
    def test_valid(self):
        tx = TaxonomyGrid(items=[
            TaxonomyItem(icon="🧠", title="Remember", body="Recall facts", example="Who is..."),
        ])
        assert tx.type == "taxonomy_grid"

    def test_discriminated_union(self):
        raw = {"type": "taxonomy_grid", "items": []}
        assert isinstance(_COMPONENT_ADAPTER.validate_python(raw), TaxonomyGrid)


# ── PhaseTimeline ─────────────────────────────────────────────────────────────

class TestPhaseTimeline:
    def test_valid(self):
        pt = PhaseTimeline(phases=[
            RoadmapPhase(title="Phase 1", when="Month 1-2", goal="Foundation"),
        ])
        assert pt.type == "phase_timeline"
        assert len(pt.phases) == 1

    def test_phase_defaults(self):
        p = RoadmapPhase(title="P", when="now")
        assert p.group == "a"
        assert p.blocks == []
        assert p.goal is None
        assert p.output is None

    def test_phase_block(self):
        pb = PhaseBlock(label="Activities")
        assert pb.items is None
        assert pb.full is False

    def test_discriminated_union(self):
        raw = {"type": "phase_timeline", "phases": []}
        assert isinstance(_COMPONENT_ADAPTER.validate_python(raw), PhaseTimeline)


# ── FlowStep ──────────────────────────────────────────────────────────────────

class TestFlowStep:
    def test_valid(self):
        fs = FlowStep(steps=[
            FlowItem(time="5 min", title="Warm up", body="Review vocabulary"),
            FlowItem(time="15 min", title="Input", body="Grammar explanation"),
        ])
        assert fs.type == "flow_step"
        assert len(fs.steps) == 2

    def test_discriminated_union(self):
        raw = {"type": "flow_step", "steps": []}
        assert isinstance(_COMPONENT_ADAPTER.validate_python(raw), FlowStep)


# ── QuestionCard ──────────────────────────────────────────────────────────────

class TestQuestionCard:
    def test_valid_basic(self):
        qc = QuestionCard(
            id=1,
            text="What is the correct form?",
            options={"A": "has", "B": "have", "C": "had", "D": "having"},
            answer="A",
            explain="Third person singular uses 'has'",
        )
        assert qc.type == "question_card"
        assert qc.group == "a"
        assert qc.wrong_reasons is None
        assert qc.essence is None
        assert qc.tip is None

    def test_with_optional_fields(self):
        qc = QuestionCard(
            id="Q5",
            text="Choose the answer",
            options={"A": "opt1", "B": "opt2"},
            answer="B",
            explain="Because...",
            group="c",
            wrong_reasons={"A": "A is wrong because..."},
            essence="Core concept here",
            tip="Look for keywords",
        )
        assert qc.group == "c"
        assert qc.essence == "Core concept here"
        assert qc.tip == "Look for keywords"

    def test_string_id(self):
        qc = QuestionCard(id="Q12", text="t", options={"A": "a"}, answer="A", explain="e")
        assert qc.id == "Q12"

    def test_discriminated_union(self):
        raw = {
            "type": "question_card",
            "id": 1,
            "text": "Q?",
            "options": {"A": "a"},
            "answer": "A",
            "explain": "e",
        }
        assert isinstance(_COMPONENT_ADAPTER.validate_python(raw), QuestionCard)


# ── QuestionList ──────────────────────────────────────────────────────────────

class TestQuestionList:
    def test_valid(self):
        ql = QuestionList(
            questions=[],
            section_key="section_i",
            group="a",
            title="Section I",
        )
        assert ql.type == "question_list"
        assert ql.sub is None
        assert ql.instruction is None

    def test_with_all_fields(self):
        ql = QuestionList(
            questions=[],
            section_key="s1",
            group="b",
            title="Grammar",
            sub="Articles",
            instruction="Choose A, B, C, or D",
            summary="Focus on context",
            range="1-10",
        )
        assert ql.range == "1-10"

    def test_discriminated_union(self):
        raw = {
            "type": "question_list",
            "questions": [],
            "section_key": "s",
            "group": "a",
            "title": "T",
        }
        assert isinstance(_COMPONENT_ADAPTER.validate_python(raw), QuestionList)


# ── ConceptMap ────────────────────────────────────────────────────────────────

class TestConceptMap:
    def test_valid(self):
        cm = ConceptMap(nodes=[{"id": "n1", "label": "Node 1"}])
        assert cm.type == "concept_map"

    def test_discriminated_union(self):
        raw = {"type": "concept_map", "nodes": []}
        assert isinstance(_COMPONENT_ADAPTER.validate_python(raw), ConceptMap)


# ── TimelineComponent ─────────────────────────────────────────────────────────

class TestTimelineComponent:
    def test_valid(self):
        tc = TimelineComponent(events=[{"time": "2024", "label": "Event"}])
        assert tc.type == "timeline"

    def test_discriminated_union(self):
        raw = {"type": "timeline", "events": []}
        assert isinstance(_COMPONENT_ADAPTER.validate_python(raw), TimelineComponent)


# ── Unknown type rejection ────────────────────────────────────────────────────

class TestUnknownTypeRejection:
    def test_unknown_type_raises(self):
        with pytest.raises((ValidationError, KeyError, ValueError)):
            _COMPONENT_ADAPTER.validate_python({"type": "unknown_widget", "data": {}})

    def test_missing_type_raises(self):
        with pytest.raises((ValidationError, KeyError)):
            _COMPONENT_ADAPTER.validate_python({"text": "No type here"})
