from __future__ import annotations

import re
from dataclasses import dataclass

from common.contracts.vocabulary_batch import (
    AmbiguousVocabularyCluster,
    InputNormalizationReport,
    NormalizedVocabularyCluster,
)

_TITLE_PREFIXES = ("chủ đề:", "chu de:", "title:", "topic:")
_NOTE_PREFIXES = ("note:", "notes:", "ghi chú:", "ghi chu:")
_TERM_SPLIT_PATTERN = re.compile(r"\s*(?:[/,;|]+|\s{2,})\s*")


@dataclass(frozen=True, slots=True)
class _ClusterCandidate:
    raw_input_span: str
    terms: tuple[str, ...]
    title_hint: str | None
    notes: tuple[str, ...]


def normalize_vocabulary_input(raw_input: str) -> InputNormalizationReport:
    candidates = _parse_candidates(raw_input)
    seen_terms: dict[str, str] = {}
    ready_clusters: list[NormalizedVocabularyCluster] = []
    ambiguous_clusters: list[AmbiguousVocabularyCluster] = []
    clarifying_questions: list[str] = []
    skipped_spans: list[str] = []

    for index, candidate in enumerate(candidates, start=1):
        duplicate_terms = tuple(term for term in candidate.terms if candidate.terms.count(term) > 1)
        overlapping_terms = tuple(term for term in candidate.terms if term in seen_terms)
        if len(candidate.terms) < 2:
            ambiguous_clusters.append(_ambiguous(index, candidate, "Only one term was found.", 0.35))
            clarifying_questions.append(f"For ‘{candidate.raw_input_span}’, what terms should it be contrasted with?")
            continue
        if duplicate_terms:
            ambiguous_clusters.append(_ambiguous(index, candidate, f"Duplicate term detected: {duplicate_terms[0]}", 0.45))
            clarifying_questions.append(f"Should ‘{duplicate_terms[0]}’ appear once, or did you mean a different term?")
            continue
        if overlapping_terms:
            ambiguous_clusters.append(_ambiguous(index, _ClusterCandidate(candidate.raw_input_span, overlapping_terms, candidate.title_hint, ()), f"Overlaps with an earlier cluster: {overlapping_terms[0]}", 0.55))
            clarifying_questions.append(f"Should ‘{overlapping_terms[0]}’ stay in both clusters or be split into one contrast set?")
        cluster_id = f"cluster-{len(ready_clusters) + 1}"
        ready_clusters.append(NormalizedVocabularyCluster(
            cluster_id=cluster_id,
            terms=candidate.terms,
            raw_input_span=candidate.raw_input_span,
            title_hint=candidate.title_hint,
            notes=candidate.notes,
            confidence=0.82 if overlapping_terms else 0.94,
        ))
        for term in candidate.terms:
            seen_terms.setdefault(term, cluster_id)

    if not candidates:
        skipped_spans.append(raw_input.strip())

    return InputNormalizationReport(
        report_id="normalization-1",
        ready_clusters=tuple(ready_clusters),
        ambiguous_clusters=tuple(ambiguous_clusters),
        clarifying_questions=tuple(clarifying_questions),
        skipped_spans=tuple(span for span in skipped_spans if span),
        parse_confidence=_parse_confidence(ready_clusters, ambiguous_clusters),
    )


def _parse_candidates(raw_input: str) -> tuple[_ClusterCandidate, ...]:
    candidates: list[_ClusterCandidate] = []
    current_title: str | None = None
    current_notes: list[str] = []
    last_candidate_index: int | None = None
    for raw_line in raw_input.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        title = _strip_prefixed_value(line, lowered, _TITLE_PREFIXES)
        if title is not None:
            current_title = title
            continue
        note = _strip_prefixed_value(line, lowered, _NOTE_PREFIXES)
        if note is not None:
            if last_candidate_index is None:
                current_notes.append(note)
            else:
                previous = candidates[last_candidate_index]
                candidates[last_candidate_index] = _ClusterCandidate(
                    raw_input_span=previous.raw_input_span,
                    terms=previous.terms,
                    title_hint=previous.title_hint,
                    notes=(*previous.notes, note),
                )
            continue
        terms = _terms_from_line(line)
        if not terms:
            continue
        candidates.append(_ClusterCandidate(
            raw_input_span=line,
            terms=terms,
            title_hint=current_title,
            notes=tuple(current_notes),
        ))
        current_title = None
        current_notes = []
        last_candidate_index = len(candidates) - 1
    return tuple(candidates)


def _terms_from_line(line: str) -> tuple[str, ...]:
    if any(separator in line for separator in ("/", ",", ";", "|")):
        terms = _TERM_SPLIT_PATTERN.split(line)
    else:
        terms = line.split()
    return tuple(term.strip().lower() for term in terms if term.strip())


def _strip_prefixed_value(line: str, lowered: str, prefixes: tuple[str, ...]) -> str | None:
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return line[len(prefix):].strip()
    return None


def _ambiguous(
    index: int,
    candidate: _ClusterCandidate,
    reason: str,
    confidence: float,
) -> AmbiguousVocabularyCluster:
    return AmbiguousVocabularyCluster(
        span_id=f"ambiguous-{index}",
        raw_input_span=candidate.raw_input_span,
        terms=candidate.terms,
        reason=reason,
        confidence=confidence,
    )


def _parse_confidence(
    ready_clusters: list[NormalizedVocabularyCluster],
    ambiguous_clusters: list[AmbiguousVocabularyCluster],
) -> float:
    total = len(ready_clusters) + len(ambiguous_clusters)
    if total == 0:
        return 0.0
    confidence = sum(cluster.confidence for cluster in ready_clusters) + sum(cluster.confidence for cluster in ambiguous_clusters)
    return round(confidence / total, 2)
