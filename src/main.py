import os
import json
from datetime import datetime
from collect_news import collect_news


def main():
    today = datetime.now().strftime("%Y-%m-%d")

    os.makedirs("data", exist_ok=True)

    news_list = collect_news(max_per_source=10)

    output_path = f"data/{today}-news.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    print(f"Collected {len(news_list)} news articles.")
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()