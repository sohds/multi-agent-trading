# 실행 및 테스트용 스크립트
import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TRANSLATOR_DIR = BASE_DIR / "news-translator"
sys.path.append(str(TRANSLATOR_DIR))

try:
    from news_helper.crawler import fetch_economy_news
except ModuleNotFoundError:
    print("❌ 크롤러 모듈을 찾을 수 없습니다. 폴더 위치를 확인해주세요.")
    sys.exit(1)

from quiz_engine import generate_ox_quiz

def main():
    parser = argparse.ArgumentParser(description="AI 뉴스 투자 퀴즈 출제 엔진")
    parser.add_argument("--limit", type=int, default=1, help="퀴즈를 생성할 최신 뉴스의 개수 (기본값: 1)")
    args = parser.parse_args()

    print(f"📰 기존 크롤러를 사용해 네이버 경제 뉴스 {args.limit}개를 가져옵니다...")
    
    articles = fetch_economy_news(limit=args.limit)
    
    # 1. 크롤러가 데이터를 아예 못 가져왔는지 확인
    print(f"✅ 크롤러 완료! 총 {len(articles)}개의 기사 데이터를 확인했습니다.")
    
    if not articles:
        print("❌ 기사 본문을 아예 불러오지 못했습니다.")
        return

    for idx, item in enumerate(articles, 1):
        print(f"\n--- [{idx}]번째 데이터 처리 시작 ---")
        
        # 2. 크롤링 중 내부 에러가 있었는지 확인
        if item["error"] or not item["article"]:
            print(f"⚠️ 크롤링 내부 에러: {item['error']}")
            continue

        article_data = item["article"]
        title = article_data["title"]
        body = article_data["body"]

        print(f"📰 뉴스 제목: {title}")
        print("🤔 OpenAI API에 퀴즈 생성을 요청합니다.")
        
        # 3. LLM 호출
        quiz = generate_ox_quiz(body, title)
        
        # 4. LLM이 무엇을 뱉었는지 날것 그대로 확인
        print(f"🔍 API 응답 Raw Data: {quiz}")
        
        if quiz:
            print("====================================")
            print("💡 오늘의 투자 퀴즈")
            print("====================================")
            print(f"Q. {quiz['question']}\n")
            print(f"정답: {quiz['answer']}")
            print(f"해설: {quiz['explanation']}")
            print("====================================")
        else:
            print("❌ 퀴즈가 제대로 생성되지 않았습니다 (None 반환됨).")

if __name__ == "__main__":
    main()