# 퀴즈 생성 프롬프트 및 LLM 출제 로직

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 상위 폴더(multi-agent-trading)의 .env 파일 로드
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def generate_ox_quiz(article_body: str, title: str) -> dict | None:
    """뉴스 본문을 바탕으로 O/X 투자 퀴즈를 생성합니다."""
    
    # 기사가 너무 길면 토큰 절약을 위해 자름
    clipped_body = article_body[:3000]
    
    prompt = f"""
    너는 일반인과 초보 투자자의 '금융 문해력(Financial Literacy)'을 길러주는 1타 경제 강사다.
    아래 경제 기사를 읽고, 단순한 사실 확인이 아닌 경제 원리와 시장의 인과관계를 묻는 깊이 있는 O/X 퀴즈 딱 1개를 출제하세요.

    [절대 금지 사항]
    기사에 나온 수치(예: 56% 감소, 20조원 돌파), 고유명사, 날짜 등을 단순히 맞추거나 틀리게 꼬는 '단답형 팩트 체크' 문제는 절대 출제하지 마세요. 
    (예: "HMM의 1분기 영업이익은 56% 감소했다."와 같은 문제 -> 금지)

    [정답 설계 핵심 지시사항]
    - 기본적으로 정답이 'X'가 되는 문제를 우선적으로(80% 이상의 확률로) 출제하세요. 사람들이 흔히 가지고 있는 경제적 착각이나 편견을 찌르는 문제가 가장 좋습니다.
    - 단, 'X' 문제를 만들 때 기사의 팩트를 단순히 반대로 뒤집거나(예: 증가했다 -> 감소했다) 숫자를 바꾸는 유치한 함정 문제는 절대 금지입니다.
    - 정답이 'O'인 문제를 낼 때는 정말 중요한 경제 원리여서 반드시 짚고 넘어가야 할 때만 제한적으로 출제하세요.

    [출제 규칙 (Good Examples)]
    1. question: 기사의 핵심 사건과 관련된 '경제/투자 기본 개념'이나, 그 사건이 '시장에 미치는 영향(인과관계)'을 묻는 문장으로 구성하고, '-다'체의 평서문이나 의문문으로 출제하세요.
       - 좋은 예 (개념): "홍콩 ELS는 기초자산이 되는 주가지수가 아무리 하락해도 원금이 100% 보장되는 안전 자산이다." (정답: X)
       - 좋은 예 (인과): "해상 운임 지수(SCFI)가 지속적으로 하락하면 HMM과 같은 해운사들의 수익성은 일반적으로 개선된다." (정답: X)
       - 좋은 예 (영향): "미국 연준이 금리를 인하하면, 일반적으로 달러 가치가 하락하고 주식 시장에는 호재로 작용한다." (정답: O)
    2. answer: 정답이 맞으면 "O", 틀리면 "X"를 반환한다. (초보자들이 흔히 착각하기 쉬운 오해를 'X' 문제로 출제하는 것을 매우 권장합니다.)
    3. explanation: 
       - 1단계: 먼저 퀴즈에 나온 '경제 개념이나 원리'를 아주 쉽게 풀어서 설명합니다.
       - 2단계: 그 원리를 바탕으로 "따라서 이번 기사에서 ~했던 것입니다." 라며 뉴스 내용과 자연스럽게 연결합니다.
       - 어투는 친절하고 명확한 '-습니다/-ㅂ니다' 체를 사용하며 2~3문장으로 작성합니다.

    뉴스 제목: {title}
    뉴스 본문: {clipped_body}
    """

    schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "investment_quiz",
            "schema": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string", "enum": ["O", "X"]},
                    "explanation": {"type": "string"}
                },
                "required": ["question", "answer", "explanation"],
                "additionalProperties": False
            },
            "strict": True
        }
    }

    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format=schema,
            temperature=0.2 
        )
        result_text = response.choices[0].message.content
        return json.loads(result_text)
    except Exception as e:
        print(f"⚠️ 퀴즈 생성 실패: {e}")
        return None