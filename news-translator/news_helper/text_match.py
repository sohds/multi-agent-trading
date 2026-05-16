from __future__ import annotations

import re


_TERM_CHAR_RE = re.compile(r"[0-9A-Za-z가-힣]")
_KOREAN_PARTICLES = (
    "으로부터",
    "에서부터",
    "에게서",
    "으로서",
    "으로써",
    "까지",
    "부터",
    "처럼",
    "보다",
    "라도",
    "이나",
    "에게",
    "에서",
    "께",
    "로",
    "으로",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "과",
    "와",
    "에",
    "도",
    "만",
    "나",
)


def find_term(text: str, term: str, start: int = 0) -> int:
    """Find a term only when it is not embedded inside another word."""
    if not text or not term:
        return -1

    search_start = max(0, start)
    while True:
        index = text.find(term, search_start)
        if index == -1:
            return -1

        end = index + len(term)
        if has_term_boundary(text, index, end):
            return index

        search_start = index + 1


def startswith_term(text: str, term: str, index: int) -> bool:
    if not text.startswith(term, index):
        return False
    return has_term_boundary(text, index, index + len(term))


def has_term_boundary(text: str, start: int, end: int) -> bool:
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    if _is_term_char(before):
        return False
    if not _is_term_char(after):
        return True
    return _has_particle_after(text, end)


def _is_term_char(value: str) -> bool:
    return bool(value and _TERM_CHAR_RE.fullmatch(value))


def _has_particle_after(text: str, end: int) -> bool:
    for particle in _KOREAN_PARTICLES:
        particle_end = end + len(particle)
        if not text.startswith(particle, end):
            continue
        next_char = text[particle_end] if particle_end < len(text) else ""
        if not _is_term_char(next_char):
            return True
    return False
