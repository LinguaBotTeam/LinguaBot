"""Describe proposed English edits faithfully without generating grammar rules."""

from dataclasses import dataclass
from difflib import SequenceMatcher
import json
import re


class FeedbackError(ValueError):
    """The complete correction cannot be represented by the public contract."""


@dataclass(frozen=True)
class _Edit:
    start: int
    end: int
    before: str
    after: str


def _find_edits(original: str, corrected: str) -> list[_Edit]:
    """Keep word, whitespace and punctuation tokens plus exact source offsets."""
    source = list(re.finditer(r"\w+|\s+|[^\w\s]", original))
    target = re.findall(r"\w+|\s+|[^\w\s]", corrected)
    offsets = [token.start() for token in source] + [len(original)]
    matcher = SequenceMatcher(
        a=[token.group() for token in source], b=target, autojunk=False
    )
    return [
        _Edit(
            start=offsets[first], end=offsets[last],
            before=original[offsets[first]:offsets[last]],
            after="".join(target[target_first:target_last]),
        )
        for operation, first, last, target_first, target_last in matcher.get_opcodes()
        if operation != "equal"
    ]


def build_correction(original: str, corrected: str | None) -> str | None:
    """Render the entire proposal and every edit; do not certify its grammar."""
    if corrected is None or corrected == original:
        return None

    lines = [
        f"Предлагаемое исправление: {json.dumps(corrected, ensure_ascii=False)}",
        "Изменения:",
    ]
    for number, edit in enumerate(_find_edits(original, corrected), start=1):
        before = json.dumps(edit.before, ensure_ascii=False)
        after = json.dumps(edit.after, ensure_ascii=False)
        if edit.before and edit.after:
            description = f"Заменено {before} на {after}."
        elif edit.before:
            description = f"Удалено {before}."
        else:
            description = f"Добавлено {after}."
        lines.append(f"{number}. {description}")
    feedback = "\n".join(lines)
    if len(feedback) > 3000:
        raise FeedbackError("Complete correction exceeds the feedback length limit.")
    try:
        feedback.encode("utf-8")
    except UnicodeEncodeError:
        raise FeedbackError("Complete correction is not valid Unicode text.") from None
    return feedback
