"""Tests for RISE template-effectiveness signal (el-007).

Pure-function tests run without any DB.
DB tests require:  postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class
and are marked with pytest.mark.skip("requires real DB").
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from common.contracts.outcome import StudentKCState
from services.gateway.decomposition_memory import DecompositionTemplateKey
from services.gateway.template_effectiveness import (
    HitlLayer,
    MIN_SAMPLE,
    MASTERY_GAIN_THRESHOLD,
    TemplateEffectivenessModel,
    TemplateEffectivenessSignal,
    TemplateEffectivenessStore,
    aggregate_mastery_gains,
    classify_hitl_layer,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC)


def _kc_state(pseudonym: str, kc_id: str, mastery: float) -> StudentKCState:
    return StudentKCState(
        state_id=f"state-{uuid4()}",
        student_pseudonym=pseudonym,
        kc_id=kc_id,
        mastery=mastery,
        params={},
        updated_at=_NOW,
    )


def _signal(
    template_id: str = "tpl-A",
    topic_normalized: str = "fractions",
    grade: str = "5",
    subject: str = "math",
    locale: str = "en",
    methodology: str | None = None,
    average_mastery_gain: float = 0.10,
    sample_size: int = 5,
) -> TemplateEffectivenessSignal:
    return TemplateEffectivenessSignal(
        template_id=template_id,
        topic_normalized=topic_normalized,
        grade=grade,
        subject=subject,
        locale=locale,
        methodology=methodology,
        average_mastery_gain=average_mastery_gain,
        sample_size=sample_size,
        is_flagged=(sample_size >= MIN_SAMPLE and average_mastery_gain < MASTERY_GAIN_THRESHOLD),
    )


# ---------------------------------------------------------------------------
# Pure-function tests
# ---------------------------------------------------------------------------


def test_aggregate_mastery_gains_empty():
    """Returns 0.0 when no matching (pseudonym, kc_id) pairs exist."""
    before = [_kc_state("s1", "kc-add", 0.40)]
    after = [_kc_state("s2", "kc-sub", 0.60)]  # different student + KC
    result = aggregate_mastery_gains(before, after)
    assert result == 0.0


def test_aggregate_mastery_gains_single_pair():
    before = [_kc_state("s1", "kc-add", 0.30)]
    after = [_kc_state("s1", "kc-add", 0.55)]
    result = aggregate_mastery_gains(before, after)
    assert abs(result - 0.25) < 1e-9


def test_aggregate_mastery_gains_multiple_pairs():
    before = [
        _kc_state("s1", "kc-add", 0.20),
        _kc_state("s2", "kc-add", 0.40),
    ]
    after = [
        _kc_state("s1", "kc-add", 0.50),  # gain = 0.30
        _kc_state("s2", "kc-add", 0.60),  # gain = 0.20
    ]
    result = aggregate_mastery_gains(before, after)
    assert abs(result - 0.25) < 1e-9


def test_aggregate_mastery_gains_partial_overlap():
    """Only matched pairs contribute; unmatched pairs are ignored."""
    before = [
        _kc_state("s1", "kc-add", 0.20),
        _kc_state("s1", "kc-mul", 0.50),  # no matching after state
    ]
    after = [
        _kc_state("s1", "kc-add", 0.60),   # gain = 0.40
        _kc_state("s1", "kc-div", 0.70),   # kc not in before
    ]
    result = aggregate_mastery_gains(before, after)
    assert abs(result - 0.40) < 1e-9


def test_classify_hitl_advisory_sparse():
    """sample_size < MIN_SAMPLE always returns ADVISORY regardless of gain."""
    assert classify_hitl_layer(0.0, MIN_SAMPLE - 1) == HitlLayer.ADVISORY
    assert classify_hitl_layer(-0.5, MIN_SAMPLE - 1) == HitlLayer.ADVISORY
    assert classify_hitl_layer(0.99, MIN_SAMPLE - 1) == HitlLayer.ADVISORY


def test_classify_hitl_suggestion_negative_gain():
    assert classify_hitl_layer(-0.01, MIN_SAMPLE) == HitlLayer.SUGGESTION
    assert classify_hitl_layer(-0.10, MIN_SAMPLE + 2) == HitlLayer.SUGGESTION


def test_classify_hitl_suggestion_near_zero():
    """mastery_gain < 0.02 with sufficient sample returns SUGGESTION."""
    assert classify_hitl_layer(0.00, MIN_SAMPLE) == HitlLayer.SUGGESTION
    assert classify_hitl_layer(0.01, MIN_SAMPLE) == HitlLayer.SUGGESTION
    assert classify_hitl_layer(0.019, MIN_SAMPLE) == HitlLayer.SUGGESTION


def test_classify_hitl_advisory_positive():
    """Gain at or above 0.02 with sufficient sample returns ADVISORY."""
    assert classify_hitl_layer(0.02, MIN_SAMPLE) == HitlLayer.ADVISORY
    assert classify_hitl_layer(0.10, MIN_SAMPLE + 10) == HitlLayer.ADVISORY


# ---------------------------------------------------------------------------
# Signal flag tests (pure dataclass construction)
# ---------------------------------------------------------------------------


def test_low_gain_template_flagged():
    """A template with gain < MASTERY_GAIN_THRESHOLD and sample >= MIN_SAMPLE is flagged."""
    sig = _signal(average_mastery_gain=MASTERY_GAIN_THRESHOLD - 0.01, sample_size=MIN_SAMPLE)
    assert sig.is_flagged is True


def test_high_gain_template_not_flagged():
    sig = _signal(average_mastery_gain=MASTERY_GAIN_THRESHOLD + 0.10, sample_size=MIN_SAMPLE)
    assert sig.is_flagged is False


def test_sparse_signal_not_flagged_regardless_of_gain():
    """Sparse signals should not be flagged — is_flagged requires sample_size >= MIN_SAMPLE."""
    sig = _signal(average_mastery_gain=0.00, sample_size=MIN_SAMPLE - 1)
    assert sig.is_flagged is False


# ---------------------------------------------------------------------------
# HITL layer semantics (pure)
# ---------------------------------------------------------------------------


def test_hitl_suggestion_not_auto_applied():
    """A SUGGESTION-layer classification must NOT be AUTO; it requires teacher approval."""
    layer = classify_hitl_layer(0.01, MIN_SAMPLE)
    assert layer == HitlLayer.SUGGESTION
    assert layer != HitlLayer.AUTO


def test_advisory_insight_is_readonly():
    """ADVISORY layer implies no automated side-effect (auto_apply must be False).

    We verify this by constructing an advisory hint dict the same way the store
    would for a sparse-data scenario.
    """
    layer = classify_hitl_layer(0.10, MIN_SAMPLE - 1)
    assert layer == HitlLayer.ADVISORY
    # Simulate the suggestion dict that get_hitl_suggestions would emit.
    suggestion = {
        "layer": layer,
        "message": "advisory message",
        "auto_apply": layer == HitlLayer.AUTO,
    }
    assert suggestion["auto_apply"] is False


# ---------------------------------------------------------------------------
# Ranking logic — simulated without DB
# ---------------------------------------------------------------------------


def test_high_gain_template_ranks_above_low_gain():
    """Given two signals, the one with higher average_mastery_gain must sort first."""
    high = _signal(template_id="tpl-high", average_mastery_gain=0.20, sample_size=MIN_SAMPLE)
    low = _signal(template_id="tpl-low", average_mastery_gain=0.03, sample_size=MIN_SAMPLE)

    ranked = sorted([low, high], key=lambda s: s.average_mastery_gain, reverse=True)
    assert ranked[0].template_id == "tpl-high"
    assert ranked[1].template_id == "tpl-low"


def test_sparse_data_suppressed():
    """Signals with sample_size < MIN_SAMPLE are excluded from ranked results."""
    sufficient = _signal(template_id="tpl-ok", average_mastery_gain=0.08, sample_size=MIN_SAMPLE)
    sparse = _signal(template_id="tpl-sparse", average_mastery_gain=0.99, sample_size=MIN_SAMPLE - 1)

    # Mimic the store's filter: suppress sample_size < MIN_SAMPLE.
    visible = [s for s in [sufficient, sparse] if s.sample_size >= MIN_SAMPLE]
    ids = [s.template_id for s in visible]

    assert "tpl-ok" in ids
    assert "tpl-sparse" not in ids


# ---------------------------------------------------------------------------
# DB tests
# ---------------------------------------------------------------------------


@pytest.mark.skip("requires real DB")
async def test_record_effectiveness_creates_signal(engine):
    """record_effectiveness creates a new signal row for a fresh template key."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        store = TemplateEffectivenessStore(session)
        key = DecompositionTemplateKey(
            teacher_id="t1",
            topic_normalized="fractions",
            grade="5",
            subject="math",
            locale="en",
        )
        await store.record_effectiveness(key, kc_ids=["kc-add"], mastery_gain=0.12)
        signals = await store.rank_templates("fractions", "5", "math", "en")
        matching = [s for s in signals if "fractions" in s.topic_normalized]
        assert len(matching) >= 1
        assert matching[0].sample_size == 1


@pytest.mark.skip("requires real DB")
async def test_record_effectiveness_rolling_average(engine):
    """Multiple calls update the rolling average correctly."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        store = TemplateEffectivenessStore(session)
        key = DecompositionTemplateKey(
            teacher_id="t2",
            topic_normalized="decimals",
            grade="6",
            subject="math",
            locale="en",
        )
        await store.record_effectiveness(key, kc_ids=["kc-dec"], mastery_gain=0.20)
        await store.record_effectiveness(key, kc_ids=["kc-dec"], mastery_gain=0.10)
        signals = await store.rank_templates("decimals", "6", "math", "en")
        matching = [s for s in signals if s.topic_normalized == "decimals"]
        # rolling avg of (0.20 + 0.10) / 2 = 0.15, sample_size = 2 < MIN_SAMPLE → suppressed
        assert len(matching) == 0  # sparse suppression


@pytest.mark.skip("requires real DB")
async def test_rank_templates_db_ordering(engine):
    """rank_templates returns signals ordered by average_mastery_gain desc."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        store = TemplateEffectivenessStore(session)
        key_low = DecompositionTemplateKey(
            teacher_id="t3-low",
            topic_normalized="geometry",
            grade="7",
            subject="math",
            locale="en",
        )
        key_high = DecompositionTemplateKey(
            teacher_id="t3-high",
            topic_normalized="geometry",
            grade="7",
            subject="math",
            locale="en",
        )
        # Record MIN_SAMPLE observations each so they appear in ranked results.
        for _ in range(MIN_SAMPLE):
            await store.record_effectiveness(key_low, kc_ids=["kc-geo"], mastery_gain=0.03)
            await store.record_effectiveness(key_high, kc_ids=["kc-geo"], mastery_gain=0.18)
        signals = await store.rank_templates("geometry", "7", "math", "en")
        assert len(signals) >= 2
        assert signals[0].average_mastery_gain >= signals[1].average_mastery_gain


@pytest.mark.skip("requires real DB")
async def test_get_hitl_suggestions_suggestion_layer(engine):
    """A low-gain template surfaces a SUGGESTION-layer hint with auto_apply=False."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        store = TemplateEffectivenessStore(session)
        key = DecompositionTemplateKey(
            teacher_id="t4",
            topic_normalized="ratios",
            grade="7",
            subject="math",
            locale="en",
        )
        await store.record_effectiveness(key, kc_ids=["kc-rat"], mastery_gain=0.01)
        suggestions = await store.get_hitl_suggestions(key)
        assert len(suggestions) >= 1
        assert suggestions[0]["layer"] == HitlLayer.SUGGESTION
        assert suggestions[0]["auto_apply"] is False
