from __future__ import annotations

import streamlit as st


PROGRESS_KEY = "quiz_progress"


def quiz_id(article: dict) -> str:
    meta = article.get("article_meta", {}) if isinstance(article, dict) else {}
    quiz = article.get("quiz", {}) if isinstance(article, dict) else {}
    url = str(meta.get("url") or "").strip()
    if url:
        return url

    title = str(meta.get("title") or "untitled").strip()
    question = str(quiz.get("question") or "unknown_question").strip()
    return f"{title}::{question}"


def quiz_progress() -> dict:
    if PROGRESS_KEY not in st.session_state:
        st.session_state[PROGRESS_KEY] = {}
    return st.session_state[PROGRESS_KEY]


def get_quiz_state(article: dict) -> dict:
    return quiz_progress().get(
        quiz_id(article),
        {"answered": False, "selected": None, "is_correct": None},
    )


def answer_quiz(article: dict, selected: str) -> None:
    quiz = article.get("quiz", {}) if isinstance(article, dict) else {}
    correct_answer = str(quiz.get("answer") or "").strip()
    quiz_progress()[quiz_id(article)] = {
        "answered": True,
        "selected": selected,
        "is_correct": selected == correct_answer,
    }


def reset_quiz(article: dict) -> None:
    quiz_progress().pop(quiz_id(article), None)


def quiz_stats(articles: list[dict]) -> dict:
    total = len(articles)
    progress = quiz_progress()
    quiz_ids = {quiz_id(article) for article in articles}
    answered = [
        state
        for qid, state in progress.items()
        if qid in quiz_ids and state.get("answered")
    ]
    answered_count = len(answered)
    correct_count = sum(1 for state in answered if state.get("is_correct"))
    remaining_count = max(0, total - answered_count)
    accuracy_text = "—" if answered_count == 0 else f"{round(correct_count / answered_count * 100)}%"
    return {
        "total_count": total,
        "answered_count": answered_count,
        "correct_count": correct_count,
        "remaining_count": remaining_count,
        "accuracy_text": accuracy_text,
    }
