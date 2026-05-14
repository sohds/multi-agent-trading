import argparse
import sys
import json
from pathlib import Path

# 1. 상위 폴더(multi-agent-trading)를 거쳐 news-translator 폴더를 파이썬 경로에 추가
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
    parser.add_argument("--limit", type=int, default=1, help="퀴즈를 생성할 최신 뉴스의 개수")
    parser.add_argument("--output", type=str, help="결과를 저장할 JSON 파일 경로 (예: data/quizzes.json)")
    parser.add_argument("--pretty", action="store_true", help="결과를 터미널에 보기 좋게 출력")
    args = parser.parse_args()

    print(f"📰 네이버 경제 뉴스 {args.limit}개를 가져오는 중...")
    articles = fetch_economy_news(limit=args.limit)
    
    if not articles:
        print("❌ 기사 데이터를 불러오지 못했습니다.")
        return

    quiz_results = []

    for idx, item in enumerate(articles, 1):
        if item["error"] or not item["article"]:
            continue

        article_data = item["article"]
        title = article_data["title"]
        body = article_data["body"]
        url = article_data["url"]

        print(f"\n[{idx}] 분석 중: {title}")
        quiz = generate_ox_quiz(body, title)
        
        if quiz:
            # 결과 저장을 위한 데이터 구조 생성
            quiz_entry = {
                "title": title,
                "url": url,
                "quiz": quiz
            }
            quiz_results.append(quiz_entry)

            if args.pretty:
                print("====================================")
                print(f"Q. {quiz['question']}")
                print(f"정답: {quiz['answer']}")
                print(f"해설: {quiz['explanation']}")
                print("====================================")

    # 파일 저장 로직
    if args.output and quiz_results:
        output_path = Path(args.output)
        
        # 저장할 폴더가 없다면 생성
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(quiz_results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 총 {len(quiz_results)}개의 퀴즈가 '{args.output}'에 저장되었다.")

if __name__ == "__main__":
    main()