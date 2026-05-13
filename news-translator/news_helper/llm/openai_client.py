from __future__ import annotations

import json
import os
from pathlib import Path
import re
import time
from typing import Any

import requests

from news_helper.config import get_bool_env, get_float_env, get_int_env


DEFAULT_OPENAI_MODEL = "gpt-5.4-mini-2026-03-17"
OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 180
DEFAULT_MAX_RETRIES = 1
DEFAULT_REASONING_EFFORT = "low"
DEBUG_LOG_PATH = Path("data/debug/openai_api.jsonl")


class LlmApiError(RuntimeError):
    """Raised when the LLM API request or response cannot be handled."""


def generate_json(
    prompt: str,
    response_schema: dict[str, Any],
    model: str | None = None,
    temperature: float | None = None,
) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LlmApiError(".env에 OPENAI_API_KEY를 입력해야 LLM 분석을 실행할 수 있습니다.")

    model_id = model or os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
    timeout_seconds = get_int_env("OPENAI_TIMEOUT_SECONDS", DEFAULT_REQUEST_TIMEOUT_SECONDS)
    max_retries = max(0, get_int_env("OPENAI_MAX_RETRIES", DEFAULT_MAX_RETRIES))
    reasoning_effort = os.getenv("OPENAI_REASONING_EFFORT", DEFAULT_REASONING_EFFORT).strip()

    payload: dict[str, Any] = {
        "model": model_id,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "difficult_terms_response",
                "schema": _strict_schema(response_schema),
                "strict": True,
            }
        },
    }
    if reasoning_effort:
        payload["reasoning"] = {"effort": reasoning_effort}

    resolved_temperature = temperature
    if resolved_temperature is None and os.getenv("OPENAI_TEMPERATURE"):
        resolved_temperature = get_float_env("OPENAI_TEMPERATURE", 0.0)
    if resolved_temperature is not None:
        payload["temperature"] = resolved_temperature

    response: requests.Response | None = None
    last_error: requests.RequestException | None = None

    for attempt in range(1, max_retries + 2):
        started_at = time.perf_counter()
        try:
            response = requests.post(
                OPENAI_RESPONSES_ENDPOINT,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=timeout_seconds,
            )
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            _debug_log(
                {
                    "event": "response",
                    "model": model_id,
                    "attempt": attempt,
                    "timeout_seconds": timeout_seconds,
                    "elapsed_ms": elapsed_ms,
                    "status_code": response.status_code,
                    "prompt_chars": len(prompt),
                    "reasoning_effort": reasoning_effort or None,
                    "temperature": resolved_temperature,
                }
            )
            break
        except requests.RequestException as exc:
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            last_error = exc
            _debug_log(
                {
                    "event": "request_error",
                    "model": model_id,
                    "attempt": attempt,
                    "timeout_seconds": timeout_seconds,
                    "elapsed_ms": elapsed_ms,
                    "prompt_chars": len(prompt),
                    "reasoning_effort": reasoning_effort or None,
                    "temperature": resolved_temperature,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            if attempt <= max_retries:
                time.sleep(min(2 * attempt, 5))

    if response is None:
        raise LlmApiError(
            "OpenAI API 요청에 실패했습니다: "
            f"{last_error}. timeout={timeout_seconds}s, retries={max_retries}. "
            "data/debug/openai_api.jsonl 로그를 확인하세요."
        ) from last_error

    if response.status_code >= 400:
        raise LlmApiError(_format_error_response(response, model_id))

    try:
        raw = response.json()
    except ValueError as exc:
        raise LlmApiError("OpenAI API 응답이 JSON 형식이 아닙니다.") from exc

    text = _extract_text(raw)
    if not text:
        raise LlmApiError(f"OpenAI API 응답에서 텍스트를 찾지 못했습니다: {raw}")

    return _parse_json_text(text)


def _debug_log(payload: dict[str, Any]) -> None:
    if not get_bool_env("DEBUG_LLM", True):
        return

    DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {"created_at": time.strftime("%Y-%m-%d %H:%M:%S"), **payload}
    with DEBUG_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def _strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    copied = json.loads(json.dumps(schema))

    def visit(node: Any) -> None:
        if not isinstance(node, dict):
            return
        if node.get("type") == "object":
            node.setdefault("additionalProperties", False)
            properties = node.get("properties")
            if isinstance(properties, dict):
                node["required"] = list(properties.keys())
                for child in properties.values():
                    visit(child)
        elif node.get("type") == "array":
            visit(node.get("items"))
        for keyword in ("anyOf", "oneOf", "allOf"):
            for child in node.get(keyword, []) if isinstance(node.get(keyword), list) else []:
                visit(child)

    visit(copied)
    return copied


def _extract_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"].strip()

    texts: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                texts.append(content["text"])
    return "\n".join(texts).strip()


def _parse_json_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LlmApiError(f"OpenAI API 응답 JSON 파싱에 실패했습니다: {cleaned[:500]}") from exc

    if not isinstance(payload, dict):
        raise LlmApiError("OpenAI API 응답 최상위 값이 객체가 아닙니다.")

    return payload


def _format_error_response(response: requests.Response, model_id: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = response.text[:500]

    return f"OpenAI API 오류가 발생했습니다. status={response.status_code}, model={model_id}, response={payload}"
