from common.contracts.answer_set import derive_answer_set, verify_answer_set


def test_constructed_response_uses_accepted_answers_not_option_ids() -> None:
    artifact = {
        "artifact_type": "drill",
        "sections": [{"components": [{
            "type": "question_card",
            "id": "practice-worked-example-1",
            "text": "Explain why two fractions are equivalent.",
            "options": {"A": "Write a supported explanation.", "B": "", "C": "", "D": ""},
            "answer": "They represent the same value.",
            "explain": "Teacher reference only.",
        }]}],
    }

    answer_set = derive_answer_set(artifact, source_document_id="doc-1", source_version=1)

    assert answer_set.entries[0].correct_option_ids == []
    assert answer_set.entries[0].accepted_answers == ["They represent the same value."]
    verify_answer_set(artifact, answer_set)


def test_selected_response_still_uses_option_ids() -> None:
    artifact = {
        "artifact_type": "quiz",
        "sections": [{"components": [{
            "type": "question_card",
            "id": "q1",
            "text": "Which value equals one half?",
            "options": {"A": "2/4", "B": "1/3"},
            "answer": "A",
        }]}],
    }

    answer_set = derive_answer_set(artifact, source_document_id="doc-2", source_version=1)

    assert answer_set.entries[0].correct_option_ids == ["A"]
    assert answer_set.entries[0].accepted_answers == []
