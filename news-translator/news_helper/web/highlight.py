from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from news_helper.llm import DifficultTerm
from news_helper.text_match import find_term, startswith_term


@dataclass(frozen=True)
class TextSegment:
    text: str
    term: str | None = None
    canonical_term: str | None = None
    variants: tuple[str, ...] = ()
    explanation: str | None = None
    difficulty_score: float | None = None
    source: str | None = None
    term_type: str | None = None
    highlight_decision: str | None = None
    is_minimal_term: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"text": self.text}
        if self.term is not None:
            payload.update(
                {
                    "term": self.term,
                    "canonical_term": self.canonical_term or self.term,
                    "variants": list(self.variants),
                    "explanation": self.explanation,
                    "difficulty_score": self.difficulty_score,
                    "source": self.source,
                    "term_type": self.term_type,
                    "highlight_decision": self.highlight_decision,
                    "is_minimal_term": self.is_minimal_term,
                }
            )
        return payload


def build_highlight_segments(body: str, terms: list[DifficultTerm]) -> list[dict[str, Any]]:
    """Split article body into plain and highlighted text segments."""
    if not body or not terms:
        return [TextSegment(text=body).to_dict()] if body else []

    lookup = _term_lookup(terms)
    ordered_terms = sorted(lookup.keys(), key=len, reverse=True)
    segments: list[TextSegment] = []
    index = 0

    while index < len(body):
        match = _first_match(body, index, ordered_terms)
        if match is None:
            next_index = _next_match_index(body, index + 1, ordered_terms)
            if next_index is None:
                segments.append(TextSegment(text=body[index:]))
                break
            segments.append(TextSegment(text=body[index:next_index]))
            index = next_index
            continue

        term = match
        info = lookup[term]
        segments.append(
            TextSegment(
                text=body[index : index + len(term)],
                term=term,
                canonical_term=info.canonical_term or info.term,
                variants=info.variants,
                explanation=info.explanation,
                difficulty_score=info.difficulty_score,
                source=info.source,
                term_type=info.term_type,
                highlight_decision=info.highlight_decision,
                is_minimal_term=info.is_minimal_term,
            )
        )
        index += len(term)

    return [segment.to_dict() for segment in _merge_plain_segments(segments)]


def _term_lookup(terms: list[DifficultTerm]) -> dict[str, DifficultTerm]:
    lookup: dict[str, DifficultTerm] = {}
    for term in terms:
        candidates = [term.term, term.canonical_term or "", *term.variants]
        for candidate in candidates:
            if candidate and candidate not in lookup:
                lookup[candidate] = term
    return lookup


def _first_match(body: str, index: int, ordered_terms: list[str]) -> str | None:
    for term in ordered_terms:
        if startswith_term(body, term, index):
            return term
    return None


def _next_match_index(body: str, start: int, ordered_terms: list[str]) -> int | None:
    found: int | None = None
    for term in ordered_terms:
        index = find_term(body, term, start)
        if index == -1:
            continue
        if found is None or index < found:
            found = index
    return found


def _merge_plain_segments(segments: list[TextSegment]) -> list[TextSegment]:
    merged: list[TextSegment] = []
    for segment in segments:
        if not segment.text:
            continue
        if segment.term is None and merged and merged[-1].term is None:
            previous = merged.pop()
            merged.append(TextSegment(text=previous.text + segment.text))
            continue
        merged.append(segment)
    return merged
