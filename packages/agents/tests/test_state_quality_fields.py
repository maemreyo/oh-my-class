from packages.agents.teaching_pack.nodes import TeachingPackState


def test_state_has_fail_layer():
    state = TeachingPackState(run_id="r1", fail_layer="schema", fail_count=1)
    assert state["fail_layer"] == "schema"
    assert state["fail_count"] == 1

def test_state_has_escalate():
    state = TeachingPackState(run_id="r1", escalate=True, escalate_reason="Too many retries")
    assert state["escalate"] is True
