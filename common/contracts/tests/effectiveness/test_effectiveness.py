from common.contracts.effectiveness.feedback import (
    EffectivenessEvent,
    aggregate_item_observations,
    propose_policy_review,
    pseudonymize_actor,
    signals_from_observations,
)


def _event(index: int, *, version: int = 1, opted_out: bool = False) -> EffectivenessEvent:
    return EffectivenessEvent(
        event_id=f"event-{version}-{index}",
        tenant_id="org-a",
        pseudonymous_actor_id=pseudonymize_actor("org-a", f"student-{index}", salt="secret"),
        document_id="quiz-1",
        document_version=version,
        item_id="question-1",
        answer_set_version=version,
        event_kind="response",
        correct=index % 2 == 0,
        distractor_id="B" if index % 2 else None,
        timing_band="typical",
        opted_out=opted_out,
    )


def test_item_statistics_are_withheld_below_privacy_threshold() -> None:
    observations = aggregate_item_observations(tuple(_event(index) for index in range(5)), minimum_sample=10)

    assert observations[0].status == "insufficient_sample"
    assert observations[0].difficulty is None


def test_item_versions_are_never_aggregated_together() -> None:
    events = tuple(_event(index, version=1) for index in range(10)) + tuple(_event(index, version=2) for index in range(10))
    observations = aggregate_item_observations(events, minimum_sample=10)

    assert len(observations) == 2
    assert {item.document_version for item in observations} == {1, 2}
    assert {item.answer_set_version for item in observations} == {1, 2}


def test_opted_out_events_do_not_enter_aggregates() -> None:
    events = tuple(_event(index) for index in range(9)) + (_event(10, opted_out=True),)
    observations = aggregate_item_observations(events, minimum_sample=10)

    assert observations[0].sample_size == 9
    assert observations[0].status == "insufficient_sample"


def test_signals_create_review_proposals_not_hidden_mutations() -> None:
    observations = aggregate_item_observations(tuple(_event(index) for index in range(10)), minimum_sample=10)
    signals = signals_from_observations(observations)
    proposal = propose_policy_review(signals, change="review distractor B for ambiguity")

    assert proposal.review_required is True
    assert proposal.automatically_applied is False
    assert signals[0].causal_claim is False
