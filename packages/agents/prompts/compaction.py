from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

_HEADING_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
_DROPPABLE_SECTIONS: Final[frozenset[str]] = frozenset({"example", "examples", "few-shot examples"})


@dataclass(frozen=True, slots=True)
class PromptCompactionError(ValueError):
    max_chars: int
    actual_chars: int

    def __str__(self) -> str:
        return f"core prompt exceeds {self.max_chars} chars after compaction: {self.actual_chars}"


@dataclass(frozen=True, slots=True)
class CompactedPrompt:
    body: str
    dropped_sections: list[str]


@dataclass(frozen=True, slots=True)
class _SectionBlock:
    title: str
    body: str


def compact_prompt(body: str, max_chars: int) -> CompactedPrompt:
    if len(body) <= max_chars:
        return CompactedPrompt(body=body, dropped_sections=[])

    kept: list[str] = []
    dropped: list[str] = []
    for block in _section_blocks(body):
        if block.title.strip().lower() in _DROPPABLE_SECTIONS:
            dropped.append(block.title.strip())
        else:
            kept.append(block.body)

    compacted_body = "\n".join(part.strip("\n") for part in kept if part.strip()).strip()
    if len(compacted_body) > max_chars:
        raise PromptCompactionError(max_chars=max_chars, actual_chars=len(compacted_body))

    return CompactedPrompt(body=compacted_body, dropped_sections=dropped)


def _section_blocks(body: str) -> list[_SectionBlock]:
    matches = list(_HEADING_PATTERN.finditer(body))
    if not matches:
        return [_SectionBlock(title="", body=body)]

    blocks: list[_SectionBlock] = []
    if matches[0].start() > 0:
        blocks.append(_SectionBlock(title="", body=body[: matches[0].start()]))

    for index, match in enumerate(matches):
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        blocks.append(_SectionBlock(title=match.group(2), body=body[match.start() : next_start]))
    return blocks
