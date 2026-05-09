import os
import json
from datetime import datetime
from collect_news import collect_news


def save_json(data, file_path):
    """
    데이터를 JSON 파일로 저장하는 함수.
    한글이 깨지지 않도록 ensure_ascii=False로 저장한다.
    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    today = datetime.now().strftime("%Y-%m-%d")

    # 저장 폴더 생성
    os.makedirs("data", exist_ok=True)

    print(f"[INFO] Start collecting news for {today}")

    # 뉴스 수집
    news_list = collect_news(
        max_per_source=10,
        min_score=6,
        min_total=20,
        max_total=25,
        max_per_category=4,
        max_per_issue=2,
        min_spotlight=2,
        max_spotlight=5
    )

    # 저장 경로
    output_path = f"data/{today}-news.json"

    # JSON 저장
    save_json(news_list, output_path)

    print(f"[INFO] Collected news count: {len(news_list)}")
    print(f"[INFO] Saved to: {output_path}")

    # 터미널에서 간단히 확인할 수 있게 제목만 출력
    print("\n🔥 오늘의 관심 종목 뉴스")
    print("=" * 80)

    for item in news_list:
        if item["category"] == "오늘의관심종목":
            print(f"- {item['title']}")

    print("\n📰 시장/경제 주요 뉴스")
    print("=" * 80)

    for item in news_list:
        if item["category"] != "오늘의관심종목":
            print(f"- [{item['category']}] {item['title']}")


if __name__ == "__main__":
    main()