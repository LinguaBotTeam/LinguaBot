"""Deterministic feedback uses synthetic text and never supplies model grammar prose."""

import json

import pytest


def _build(original, corrected):
    from linguabot.ai.feedback import build_correction

    return build_correction(original, corrected)


@pytest.mark.parametrize("original,corrected", [
    ("I am ready.", None), ("I am ready.", "I am ready."),
    ("  I am ready.\n", "  I am ready.\n"), ("", None), ("", ""),
])
def test_null_or_exactly_unchanged_input_has_no_correction(original, corrected):
    assert _build(original, corrected) is None


@pytest.mark.parametrize("original,corrected,expected", [
    ("These shoes is too small.", "These shoes are too small.", [(12, 14, "is", "are")]),
    ("I have a coffee.", "I have a coffee and a cake.", [(15, 15, "", " and a cake")]),
    ("I\tlike  tea.\r\n", "I like tea!\n", [(1, 2, "\t", " "), (6, 8, "  ", " "),
                                                     (11, 14, ".\r\n", "!\n")]),
    ('He said "café" 🙂.', 'He said «кафе» 🙃!', [(8, 14, '"café"', '«кафе»'),
                                                     (15, 17, '🙂.', '🙃!')]),
    ("I has a bag and she have shoes.", "I have a bag and she has shoes.",
     [(2, 5, "has", "have"), (20, 24, "have", "has")]),
    ("I like tea.", "Yesterday, I liked tea.", [(0, 0, "", "Yesterday, "),
                                                   (2, 6, "like", "liked")]),
    ("", "Hello!", [(0, 0, "", "Hello!")]),
    ("Hello!", "", [(0, 6, "Hello!", "")]),
])
def test_reported_edits_preserve_all_text_and_reconstruct_the_complete_correction(
    original, corrected, expected
):
    from linguabot.ai.feedback import _find_edits

    feedback = _build(original, corrected)
    assert feedback is not None
    assert feedback.splitlines()[0] == f"Предлагаемое исправление: {json.dumps(corrected, ensure_ascii=False)}"
    edits = _find_edits(original, corrected)
    # Literal examples catch lost punctuation/whitespace and ambiguous repeated words.
    assert [(edit.start, edit.end, edit.before, edit.after) for edit in edits] == expected
    # Every edit must also be visible to the learner, without implementation offsets.
    assert len(feedback.splitlines()) == len(expected) + 2
    for number, (_, _, old, new) in enumerate(expected, start=1):
        quoted_old = json.dumps(old, ensure_ascii=False)
        quoted_new = json.dumps(new, ensure_ascii=False)
        if old and new:
            assert f"{number}. Заменено {quoted_old} на {quoted_new}." in feedback
        elif old:
            assert f"{number}. Удалено {quoted_old}." in feedback
        else:
            assert f"{number}. Добавлено {quoted_new}." in feedback
    rebuilt = original
    for edit in reversed(edits):
        assert original[edit.start:edit.end] == edit.before
        rebuilt = rebuilt[:edit.start] + edit.after + rebuilt[edit.end:]
    assert rebuilt == corrected


def test_observed_shoes_correction_cannot_claim_have_is_required():
    feedback = _build("These shoes is too small.", "These shoes are too small.")
    assert feedback is not None
    assert 'Заменено "is" на "are".' in feedback
    assert "have" not in feedback
    assert "нужно" not in feedback
    assert "используется" not in feedback


def test_duplicated_word_deletion_is_lossless_without_requiring_one_diff_alignment():
    from linguabot.ai.feedback import _find_edits

    original = "I have have a bag."
    corrected = "I have a bag."
    edits = _find_edits(original, corrected)
    assert len(edits) == 1
    edit = edits[0]
    assert edit.before.strip() == "have"
    assert edit.after == ""
    assert original[edit.start:edit.end] == edit.before
    assert original[:edit.start] + original[edit.end:] == corrected
    feedback = _build(original, corrected)
    assert feedback is not None
    assert f"1. Удалено {json.dumps(edit.before, ensure_ascii=False)}." in feedback
    assert json.dumps(corrected, ensure_ascii=False) in feedback


@pytest.mark.parametrize("original,corrected", [
    ("These shoes have red laces.", None),
    ("These shoes have red laces.", "These shoes have red laces."),
    ("They have coffee.", "They have coffee."),
])
def test_valid_have_phrases_are_not_hardcoded_to_are(original, corrected):
    assert _build(original, corrected) is None


@pytest.mark.parametrize("original,corrected", [
    ("I buyed a cup.", "I bought a cup."),
    ("Yesterday, she have tea.", "Yesterday, she had tea."),
    ('"She have tea" is a quote.', '"She has tea" is a quote.'),
    ("She and I have tea.", "She and I had tea."),
    ("She have tea and I has coffee.", "She has tea and I have coffee."),
])
def test_unverified_grammar_patterns_get_only_a_faithful_edit_description(original, corrected):
    feedback = _build(original, corrected)
    assert feedback is not None
    assert "Правило:" not in feedback
    assert "Предлагаемое исправление:" in feedback


def test_oversized_feedback_is_rejected_instead_of_silently_clipped():
    from linguabot.ai.feedback import FeedbackError

    with pytest.raises(FeedbackError):
        _build("a", "b" * 3000)


def test_many_edits_cannot_overflow_the_public_feedback_limit():
    from linguabot.ai.feedback import FeedbackError

    original = " ".join(["bad", "keep"] * 80)
    corrected = " ".join(["good", "keep"] * 80)
    with pytest.raises(FeedbackError):
        _build(original, corrected)


def test_feedback_keeps_complete_text_when_it_fits_the_limit():
    corrected = "Tea " + "x" * 2500
    feedback = _build("Coffee " + "x" * 2500, corrected)
    assert feedback is not None
    assert json.dumps(corrected, ensure_ascii=False) in feedback
    assert len(feedback) <= 3000


def test_exact_public_limit_is_allowed_without_dropping_text():
    expected_fixed_text = (
        'Предлагаемое исправление: "Tea "\nИзменения:\n'
        '1. Заменено "Coffee" на "Tea".'
    )
    suffix = "x" * (3000 - len(expected_fixed_text))
    feedback = _build("Coffee " + suffix, "Tea " + suffix)
    assert feedback is not None
    assert len(feedback) == 3000
    assert json.dumps("Tea " + suffix, ensure_ascii=False) in feedback


@pytest.mark.parametrize("original,corrected", [
    ("Tea", "\ud800"), ("\udfff", "Tea"),
])
def test_unencodable_unicode_is_rejected_as_unrepresentable_feedback(original, corrected):
    from linguabot.ai.feedback import FeedbackError

    with pytest.raises(FeedbackError):
        _build(original, corrected)
