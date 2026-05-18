import sys
import json
from pathlib import Path
from datetime import datetime  

BASE_DIR = Path(__file__).resolve().parent

# 필요한 모듈들 경로 추가
sys.path.append(str(BASE_DIR / "debate"))
sys.path.append(str(BASE_DIR / "news-translator"))
sys.path.append(str(BASE_DIR / "news-quiz"))

# 각 폴더의 핵심 함수들 불러오기
from naver_headline_crawler import crawl
from news_helper.llm import analyze_difficult_terms 
from quiz_engine import generate_ox_quiz                   

def run_daily_news_pipeline(limit=10):
    print(f"🚀 [STEP 1] 네이버 경제 헤드라인 크롤링 중...")
    crawl_result = crawl()
    
    if not crawl_result or "all_headlines" not in crawl_result:
        print("❌ 크롤러 실패")
        return None

    # 전체 기사 중 원하는 개수(limit)만큼 가져오기
    articles = crawl_result["all_headlines"][:limit]
    final_ui_data_list = [] # 10개 기사의 결과를 담을 큰 바구니

    print(f"\n✅ 총 {len(articles)}개 기사 데이터 통합 처리를 시작합니다.\n")

    # [STEP 2 & 3] 10개 기사를 하나씩 돌면서 번역 + 퀴즈 생성
    for idx, article in enumerate(articles, 1):
        title = article.get("title", "제목 없음")
        body = article.get("body", "")

        if not body:
            print(f"[{idx}/{len(articles)}] ⚠️ 본문이 비어있어 건너뜁니다: {title}")
            continue

        print(f"[{idx}/{len(articles)}] 🔄 처리 중: {title[:30]}...")

        # 1. 번역기 엔진 실행
        analysis_obj = analyze_difficult_terms(body)
        if hasattr(analysis_obj, "to_dict"):
            translated_terms = analysis_obj.to_dict()
        else:
            translated_terms = analysis_obj

        # 2. 퀴즈 엔진 실행
        quiz_data = generate_ox_quiz(body, title)

        # 3. 하나의 딕셔너리로 리스트에 추가
        final_ui_data_list.append({
            "article_meta": {
                "title": title,
                "url": article.get("url"),
                "published_at": article.get("published_at"),
                "press": article.get("press"),
                "cluster_num": article.get("cluster_num"),
                "image_url": article.get("image_url") or ""
            },
            "article_body": body,
            "translated_terms": translated_terms,
            "quiz": quiz_data
        })

    # ✨ [STEP 4] 완성된 10개 리스트를 시간 이름이 붙은 JSON 파일로 저장
    print("\n📦 [STEP 4] UI 전용 통합 데이터 패키징 완료!")
    
    # 현재 시간 가져오기
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 파일명 생성 (통합 데이터이므로 integrated_news 사용)
    filename = f"integrated_news_{current_time}.json"
    
    # 최상단 output/news 폴더로 경로 지정
    output_dir = BASE_DIR / "output" / "news"
    output_path = output_dir / filename
    
    # 폴더가 없으면 생성
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_ui_data_list, f, ensure_ascii=False, indent=2)

    print(f"🎉 성공! 총 {len(final_ui_data_list)}개 기사의 번역+퀴즈 통합 파일이 저장되었습니다: {output_path}")
    return final_ui_data_list

if __name__ == "__main__":
    run_daily_news_pipeline(limit=10)