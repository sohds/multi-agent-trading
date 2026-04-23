"""
불/베어 에이전트 공통 LLM 호출 레이어

두 에이전트의 API 호출·JSON 파싱·오류 처리 로직을 공유합니다.
"""

import json
import os

from openai import OpenAI
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())


def _call_llm(
    system_prompt: str,
    input_package: dict,
    opponent_argument: dict | None,
    opponent_label: str,
    model: str,
) -> dict:
    """
    OpenAI API를 호출하고 JSON 응답을 파싱합니다.

    Args:
        system_prompt:      에이전트별 시스템 프롬프트 (불/베어 구분)
        input_package:      불/베어 공통 입력 패키지 (spec §5)
        opponent_argument:  직전 라운드 상대방 출력 dict (없으면 None)
        opponent_label:     상대방 역할명 (예: "Bear", "Bull")
        model:              OpenAI 모델 ID

    Returns:
        dict: 에이전트 출력 JSON
              오류 시 {"error": str, "raw_response": str (있을 경우)}
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요."}

    opponent_section = (
        json.dumps(opponent_argument, ensure_ascii=False, indent=2)
        if opponent_argument
        else "없음 (첫 번째 라운드)"
    )

    user_message = (
        f"[분석 대상]\n{input_package.get('topic', '종목 분석')}\n\n"
        f"[입력 데이터 패키지]\n"
        f"{json.dumps(input_package, ensure_ascii=False, indent=2)}\n\n"
        f"[상대방({opponent_label}) 논거]\n{opponent_section}\n\n"
        f"위 데이터를 분석하여 지정된 JSON 형식으로 출력하세요."
    )

    raw = ""
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            max_completion_tokens=1024,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        raw = response.choices[0].message.content.strip()

        # 모델이 마크다운 코드블록으로 감쌀 경우 제거
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        return json.loads(raw)

    except json.JSONDecodeError as e:
        return {"error": f"JSON 파싱 실패: {e}", "raw_response": raw}
    except Exception as e:
        return {"error": str(e)}
