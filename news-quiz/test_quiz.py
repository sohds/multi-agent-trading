import argparse
import sys
import json
from pathlib import Path
from datetime import datetime  

# 1. 상위 폴더(multi-agent-trading) 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. 통합 크롤러가 있는 debate 폴더를 파이썬 경로에 추가
DEBATE_DIR = BASE_DIR / "debate"
sys.path.append(str(DEBATE_DIR))

try:
    # 3. 새로운 통합 크롤러에서 crawl 함수 가져오기
    from naver_headline_crawler import crawl
except Exception as e:
    print("❌ 통합 크롤러 모듈을 찾을 수 없습니다. 경로 또는 패키지를 확인해주세요.")
    print(f"🔍 상세 에러: {e}")
    sys.exit(1)

from quiz_engine import generate_ox_quiz

def main():
    parser = argparse.ArgumentParser(description="AI 뉴스 투자 퀴즈 출제 엔진")
    parser.add_argument("--limit", type=int, default=10, help="퀴즈를 생성할 최신 뉴스의 개수")
    parser.add_argument("--output", type=str, help="직접 지정할 저장 경로 (생략 시 output 폴더에 자동 저장)")
    parser.add_argument("--pretty", action="store_true", help="결과를 터미널에 보기 좋게 출력")
    args = parser.parse_args()

    print("📰 통합 크롤러를 통해 네이버 경제 헤드라인 데이터를 가져오는 중...")
    
    # 4. 통합 크롤러 실행
    crawl_result = crawl()
    
    if not crawl_result or "all_headlines" not in crawl_result:
        print("❌ 기사 데이터를 불러오지 못했습니다.")
        return

    # 5. 수집된 전체 헤드라인 목록에서 요청한 개수(--limit)만큼만 자르기
    articles = crawl_result["all_headlines"][:args.limit]
    quiz_results = []

    for idx, item in enumerate(articles, 1):
        title = item.get("title", "제목 없음")
        body = item.get("body", "")
        url = item.get("url", "")

        if not body:
            print(f"\n[{idx}] ⚠️ 기사 본문이 비어있어 건너뜁니다: {title}")
            continue

        print(f"\n[{idx}] 분석 중: {title}")
        quiz = generate_ox_quiz(body, title)
        
        if quiz:
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

    # 자동 저장 로직 
    if quiz_results:
        if args.output:
            # 사용자가 직접 경로를 입력한 경우
            output_path = Path(args.output)
        else:
            # 사용자가 입력하지 않은 경우 -> 자동 시간 이름 생성
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"news_quiz_{current_time}.json"
            
            output_dir = BASE_DIR / "output" / "news"
            output_path = output_dir / filename
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(quiz_results, f, ensure_ascii=False, indent=2)
            
        print(f"\n✅ 총 {len(quiz_results)}개의 퀴즈가 '{output_path}'에 저장되었습니다! 🎉")

if __name__ == "__main__":
    main()