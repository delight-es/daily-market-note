import feedparser
import re
from datetime import datetime
from urllib.parse import quote_plus
from difflib import SequenceMatcher


# =========================
# 1. 제외 키워드
# =========================

EXCLUDE_KEYWORDS = [
    # 증권/경제 공부에 도움 적은 기사
    "부고", "모친상", "부친상", "별세", "상주",
    "인사", "동정", "게시판",
    "포토", "사진", "영상", "카드뉴스",
    "채용", "공모전", "박람회",

    # 기업공시와 헷갈리는 행정/부동산 공시 제거
    "공동주택 공시가", "개별공시지가", "공시지가", "이의신청",

    # 경제/증권 공부와 직접 관련 낮은 사건성 뉴스
    "불법 고용", "해경", "적발", "선원", "어선",
    "교통사고", "화재", "범죄", "검거", "구속", "재판"
]


# =========================
# 2. 관심 키워드
# =========================

KEYWORDS = [
    # 국내 증시
    "코스피", "코스닥", "증시", "주식", "증권", "개미", "외국인", "기관",
    "거래대금", "상한가", "하한가", "급등", "급락", "랠리",
    "특징주", "급등주", "주도주", "강세", "약세", "목표가", "신고가", "신저가",

    # 글로벌 시장
    "뉴욕증시", "미국증시", "미국 증시", "나스닥", "다우", "S&P500", "S&P",
    "월가", "연준", "Fed", "FOMC", "금리", "국채금리", "환율", "달러", "엔화",
    "유가", "원유", "금값", "인플레이션", "CPI", "PPI",

    # 국내경제/생활경제
    "한국경제", "국내경제", "물가", "소비", "소비심리", "체감경기",
    "가계부채", "고용", "취업자", "실업률", "수출", "수입", "무역수지",
    "식량가격", "곡물", "육류", "유지류", "농산물",
    "부동산", "아파트", "전세", "월세",

    # 산업/섹터
    "반도체", "AI", "인공지능", "데이터센터",
    "전력", "전력기기", "전선", "변압기", "전력망",
    "2차전지", "배터리", "전기차",
    "조선", "방산", "로봇", "바이오",
    "은행", "보험", "금융", "증권사", "카드",

    # 기업 이벤트
    "실적", "공시", "수주", "공급계약", "유상증자", "무상증자",
    "자사주", "배당", "합병", "분할", "상장폐지", "관리종목"
]


# =========================
# 3. Google News RSS 검색어
# =========================

SEARCH_QUERIES = {
    # 시장 흐름
    "국내증시": "코스피 OR 코스닥 OR 국내증시 OR 주식시장 OR 개인투자자",
    "미국증시": "뉴욕증시 OR 나스닥 OR 다우 OR S&P500 OR 미국증시",

    # 거시경제
    "금리환율": "연준 OR FOMC OR 금리 OR 환율 OR 달러 OR 국채금리 OR 한국은행",
    "세계경제": "세계경제 OR 글로벌경제 OR 유가 OR 인플레이션 OR CPI OR 식량가격 OR 원유",
    "국내경제": "한국경제 OR 국내경제 OR 물가 OR 소비심리 OR 체감경기 OR 가계부채 OR 고용 OR 수출입",

    # 산업/섹터
    "반도체_AI": "반도체 OR AI OR 인공지능 OR 데이터센터",
    "전력기기": "전력기기 OR 전선 OR 변압기 OR 전력망",
    "2차전지": "2차전지 OR 배터리 OR 전기차",
    "조선방산": "조선 OR 방산 OR 수주",
    "금융증권": "은행 OR 보험 OR 증권사 OR 금융지주 OR 카드사",

    # 기업 이벤트
    "기업이슈": "실적 OR 공급계약 OR 유상증자 OR 자사주 OR 배당 OR 합병 OR 분할"
}


# =========================
# 4. 오늘의 관심 종목 검색어
# =========================

STOCK_SPOTLIGHT_QUERIES = {
    "오늘의종목_특징주": "특징주 급등 이유 OR 특징주 강세 OR 특징주 약세",
    "오늘의종목_상한가": "상한가 이유 OR 오늘 상한가 OR 급등주",
    "오늘의종목_거래대금": "거래대금 상위 종목 OR 증시 주도주 OR 오늘 주도주",
    "오늘의종목_실적공시": "실적 발표 주가 급등 OR 공급계약 공시 주가 급등 OR 수주 공시 주가"
}


# =========================
# 5. 언론사 RSS 보완
# =========================

RSS_SOURCES = {
    "연합뉴스_경제": "https://www.yna.co.kr/rss/economy.xml",
    "연합뉴스_증권": "https://www.yna.co.kr/rss/stock.xml",
    "매일경제_경제": "https://www.mk.co.kr/rss/30100041/",
}


# =========================
# 6. 기본 유틸 함수
# =========================

def make_google_news_rss_url(query: str) -> str:
    encoded_query = quote_plus(query)
    return (
        f"https://news.google.com/rss/search?"
        f"q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    )


def clean_title(title: str) -> str:
    """
    Google News 제목 뒤의 언론사명 제거.
    예: "고용 호조에 나스닥 상승 - 조선일보" → "고용 호조에 나스닥 상승"
    """
    title = " ".join(title.split())

    if " - " in title:
        title = title.rsplit(" - ", 1)[0]

    # [해외시황], [부고] 같은 앞쪽 태그 제거
    title = re.sub(r"^\[[^\]]+\]\s*", "", title)

    return title.strip()


def contains_exclude_keyword(text: str) -> bool:
    text_lower = text.lower()

    for keyword in EXCLUDE_KEYWORDS:
        if keyword.lower() in text_lower:
            return True

    return False


def match_keywords(title: str):
    """
    언론사명 제거 후 키워드 매칭.
    ex. '조선일보' 때문에 산업 키워드 '조선'이 잡히는 일을 줄일 수 있음.
    """
    cleaned = clean_title(title)
    title_lower = cleaned.lower()

    matched = []

    for keyword in KEYWORDS:
        if keyword.lower() in title_lower:
            matched.append(keyword)

    return matched


def normalize_for_duplicate(title: str) -> str:
    """
    정확 중복/유사 중복 판단용 정규화.
    """
    title = clean_title(title)
    title = title.lower()

    # 특수문자 제거
    title = re.sub(r"[^가-힣a-zA-Z0-9]", "", title)

    return title


def title_similarity(title1: str, title2: str) -> float:
    t1 = normalize_for_duplicate(title1)
    t2 = normalize_for_duplicate(title2)

    if not t1 or not t2:
        return 0.0

    return SequenceMatcher(None, t1, t2).ratio()


# =========================
# 7. 중요도 점수
# =========================

def calculate_importance_score(title: str, matched_keywords: list, category: str) -> int:
    score = 0
    cleaned = clean_title(title)
    title_lower = cleaned.lower()

    # 키워드가 많이 잡힐수록 기본 점수 상승
    score += len(matched_keywords) * 2

    # 시장 직접 관련 키워드
    market_keywords = [
        "코스피", "코스닥", "뉴욕증시", "나스닥", "S&P500", "S&P",
        "금리", "환율", "연준", "FOMC",
        "실적", "수주", "공급계약",
        "상한가", "급등", "급락", "랠리",
        "특징주", "강세", "약세", "신고가"
    ]

    for keyword in market_keywords:
        if keyword.lower() in title_lower:
            score += 5

    # 국내경제/세계경제 키워드
    economy_keywords = [
        "물가", "소비", "소비심리", "체감경기", "가계부채",
        "고용", "취업자", "실업률", "수출", "무역수지",
        "식량가격", "곡물", "유가", "원유", "인플레이션"
    ]

    for keyword in economy_keywords:
        if keyword.lower() in title_lower:
            score += 4

    # 섹터 키워드
    sector_keywords = [
        "반도체", "AI", "데이터센터", "전력기기", "전선", "변압기",
        "2차전지", "배터리", "조선", "방산", "로봇", "바이오"
    ]

    for keyword in sector_keywords:
        if keyword.lower() in title_lower:
            score += 3

    # 오늘의 관심 종목 카테고리 가중치
    if category.startswith("오늘의종목"):
        score += 12

    # 카테고리별 기본 가중치
    if category in ["국내증시", "미국증시", "금리환율"]:
        score += 6

    if category in ["세계경제", "국내경제", "국내경제_RSS"]:
        score += 4

    if category in ["기업이슈", "금융증권"]:
        score += 4

    return score


# =========================
# 8. 이슈 키 생성
# =========================

def get_issue_key(title: str, matched_keywords: list, category: str) -> str:
    """
    같은 이슈를 묶기 위한 key.
    단, 너무 많이 날아가지 않도록 넓은 이슈는 세분화한다.
    """
    text = clean_title(title).lower()
    keywords = set(matched_keywords)

    # 오늘의 관심 종목은 제목 기반으로 조금 더 세분화
    if category.startswith("오늘의종목") or category == "오늘의관심종목":
        return "STOCK_SPOTLIGHT_" + normalize_for_duplicate(title)[:30]

    # 미국 증시 상승/랠리
    if (
        any(word in text for word in ["뉴욕증시", "미국증시", "나스닥", "s&p500", "s&p"])
        and any(word in text for word in ["상승", "최고치", "경신", "랠리", "강세"])
    ):
        return "US_STOCK_RALLY"

    # 미국 고용과 금리 기대
    if (
        "고용" in keywords
        and any(word in text for word in ["금리", "인하", "연준", "fomc"])
    ):
        return "US_JOBS_RATE_EXPECTATION"

    # 달러-원 환율
    if (
        "환율" in keywords
        or "달러-원" in text
        or "달러원" in text
    ):
        return "USD_KRW_EXCHANGE_RATE"

    # 코스피 랠리/국내 증시 상승
    if (
        "코스피" in keywords
        and any(word in text for word in ["급등", "질주", "상승", "돌파", "최고", "1만", "7500", "7000"])
    ):
        return "KOSPI_RALLY"

    # 개인투자자 심리
    if (
        "개미" in keywords
        or "개인투자자" in text
        or "보험마저 깨고" in text
        or "초조한 개미" in text
    ):
        return "RETAIL_INVESTOR_SENTIMENT"

    # 세계 식량가격
    if (
        "식량가격" in keywords
        or "곡물" in keywords
        or "유지류" in keywords
        or "육류" in keywords
    ):
        return "GLOBAL_FOOD_PRICE"

    # 유가/중동/원유
    if (
        "유가" in keywords
        or "원유" in keywords
        or "호르무즈" in text
        or "중동" in text
    ):
        return "OIL_PRICE_MIDDLE_EAST"

    # 국내 물가/소비/체감경기
    if (
        "물가" in keywords
        or "체감경기" in keywords
        or "소비" in keywords
        or "소비심리" in keywords
    ):
        return "DOMESTIC_CONSUMER_ECONOMY"

    # 금융/은행/보험/카드
    if (
        "금융" in keywords
        or "은행" in keywords
        or "보험" in keywords
        or "카드" in keywords
        or "카드사" in text
    ):
        return "FINANCIAL_SECTOR"

    # 반도체/AI
    if (
        "반도체" in keywords
        or "AI" in keywords
        or "인공지능" in keywords
        or "데이터센터" in keywords
    ):
        return "SEMICONDUCTOR_AI"

    # 전력기기
    if (
        "전력기기" in keywords
        or "전선" in keywords
        or "변압기" in keywords
        or "전력망" in keywords
    ):
        return "POWER_INFRA"

    # 2차전지
    if (
        "2차전지" in keywords
        or "배터리" in keywords
        or "전기차" in keywords
    ):
        return "BATTERY_EV"

    # 조선/방산
    if (
        "조선" in keywords
        or "방산" in keywords
    ):
        return "SHIPBUILDING_DEFENSE"

    # 기업 실적
    if "실적" in keywords:
        return "CORPORATE_EARNINGS"

    # 기업 수주/공급계약
    if "수주" in keywords or "공급계약" in keywords:
        return "CORPORATE_CONTRACT"

    # 기타는 카테고리 + 제목 일부
    return category + "_" + normalize_for_duplicate(title)[:30]


# =========================
# 9. 중복 판단
# =========================

def is_exact_duplicate(new_item: dict, selected_items: list) -> bool:
    """
    완전 중복 제거.
    링크 동일 / 정규화 제목 동일이면 제거.
    """
    new_link = new_item.get("link", "")
    new_title = new_item.get("title", "")
    new_norm = normalize_for_duplicate(new_title)

    for item in selected_items:
        if new_link and new_link == item.get("link", ""):
            return True

        if new_norm and new_norm == normalize_for_duplicate(item.get("title", "")):
            return True

    return False


def is_too_similar_article(new_item: dict, selected_items: list, threshold=0.76) -> bool:
    """
    유사 기사 제거.
    threshold를 0.82로 둬서 너무 많이 날아가지 않게 완화.
    """
    new_title = new_item.get("title", "")

    for item in selected_items:
        sim = title_similarity(new_title, item.get("title", ""))

        if sim >= threshold:
            return True

    return False


# =========================
# 10. 오늘의 관심 종목 뉴스 수집
# =========================

def collect_stock_spotlight_news(max_per_source=8, min_score=7, max_total=5):
    """
    오늘 시장에서 관심받은 종목/특징주 뉴스를 별도로 수집.
    최종 블로그 상단 '오늘의 관심 종목 뉴스'에 사용.
    """
    spotlight_news = []
    seen_links = set()

    for category, query in STOCK_SPOTLIGHT_QUERIES.items():
        rss_url = make_google_news_rss_url(query)
        feed = feedparser.parse(rss_url)

        for entry in feed.entries[:max_per_source]:
            raw_title = entry.get("title", "")
            title = clean_title(raw_title)
            link = entry.get("link", "")
            published = entry.get("published", "")

            if not title:
                continue

            if contains_exclude_keyword(title):
                continue

            if link in seen_links:
                continue
            seen_links.add(link)

            matched_keywords = match_keywords(title)
            score = calculate_importance_score(title, matched_keywords, category)

            # 종목 뉴스에서 특히 중요하게 볼 키워드
            stock_keywords = [
                "특징주", "급등", "급락", "상한가", "하한가",
                "강세", "약세", "신고가", "실적", "수주",
                "공급계약", "자사주", "배당", "목표가"
            ]

            for keyword in stock_keywords:
                if keyword.lower() in title.lower():
                    score += 8

            if score < min_score:
                continue

            issue_key = get_issue_key(title, matched_keywords, category)

            item = {
                "category": "오늘의관심종목",
                "source": "GoogleNewsRSS",
                "title": title,
                "link": link,
                "published": published,
                "matched_keywords": matched_keywords,
                "importance_score": score,
                "issue_key": issue_key,
                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            spotlight_news.append(item)

    spotlight_news.sort(key=lambda x: x["importance_score"], reverse=True)

    # 너무 비슷한 종목 뉴스 제거
    selected = []

    for item in spotlight_news:
        if len(selected) >= max_total:
            break

        if is_exact_duplicate(item, selected):
            continue

        if is_too_similar_article(item, selected, threshold=0.82):
            continue

        selected.append(item)

    return selected


# =========================
# 11. 일반 시장/경제 뉴스 수집
# =========================

def collect_raw_news(max_per_source=10, min_score=6):
    raw_news = []
    seen_links = set()

    # 1. Google News RSS 수집
    for category, query in SEARCH_QUERIES.items():
        rss_url = make_google_news_rss_url(query)
        feed = feedparser.parse(rss_url)

        for entry in feed.entries[:max_per_source]:
            raw_title = entry.get("title", "")
            title = clean_title(raw_title)
            link = entry.get("link", "")
            published = entry.get("published", "")

            if not title:
                continue

            if contains_exclude_keyword(title):
                continue

            if link in seen_links:
                continue
            seen_links.add(link)

            matched_keywords = match_keywords(title)
            score = calculate_importance_score(title, matched_keywords, category)

            if score < min_score:
                continue

            issue_key = get_issue_key(title, matched_keywords, category)

            raw_news.append({
                "category": category,
                "source": "GoogleNewsRSS",
                "title": title,
                "link": link,
                "published": published,
                "matched_keywords": matched_keywords,
                "importance_score": score,
                "issue_key": issue_key,
                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    # 2. 언론사 경제/증권 RSS 보완 수집
    for source_name, rss_url in RSS_SOURCES.items():
        feed = feedparser.parse(rss_url)

        for entry in feed.entries[:max_per_source]:
            raw_title = entry.get("title", "")
            title = clean_title(raw_title)
            link = entry.get("link", "")
            published = entry.get("published", "")

            if not title:
                continue

            if contains_exclude_keyword(title):
                continue

            if link in seen_links:
                continue
            seen_links.add(link)

            matched_keywords = match_keywords(title)
            score = calculate_importance_score(title, matched_keywords, "국내경제_RSS")

            # RSS 보완 기사는 기준을 조금 낮게 둠
            if score < 5:
                continue

            issue_key = get_issue_key(title, matched_keywords, "국내경제_RSS")

            raw_news.append({
                "category": "국내경제_RSS",
                "source": source_name,
                "title": title,
                "link": link,
                "published": published,
                "matched_keywords": matched_keywords,
                "importance_score": score,
                "issue_key": issue_key,
                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    raw_news.sort(key=lambda x: x["importance_score"], reverse=True)
    return raw_news


# =========================
# 12. 최종 뉴스 선별
# =========================

def select_final_news(raw_news, min_total=20, max_total=25, max_per_category=4, max_per_issue=2):
    """
    최종 블로그 초안에 넣을 뉴스 선별.

    핵심:
    - 완전 중복은 제거
    - 너무 비슷한 제목은 제거
    - 같은 issue_key는 최대 2개까지 허용
    - 카테고리별 최대 4개
    - 전체 20~25개
    """
    selected = []
    category_count = {}
    issue_count = {}

    # 1차 선별
    for item in raw_news:
        category = item["category"]
        issue_key = item.get("issue_key", "")

        if len(selected) >= max_total:
            break

        if category_count.get(category, 0) >= max_per_category:
            continue

        if issue_count.get(issue_key, 0) >= max_per_issue:
            continue

        if is_exact_duplicate(item, selected):
            continue

        if is_too_similar_article(item, selected, threshold=0.82):
            continue

        selected.append(item)
        category_count[category] = category_count.get(category, 0) + 1
        issue_count[issue_key] = issue_count.get(issue_key, 0) + 1

    # 2차 보충: 20개 미만이면 기준 완화해서 채움
    if len(selected) < min_total:
        for item in raw_news:
            category = item["category"]
            issue_key = item.get("issue_key", "")

            if len(selected) >= min_total:
                break

            if item in selected:
                continue

            if category_count.get(category, 0) >= max_per_category + 1:
                continue

            if issue_count.get(issue_key, 0) >= max_per_issue + 1:
                continue

            if is_exact_duplicate(item, selected):
                continue

            if is_too_similar_article(item, selected, threshold=0.90):
                continue

            selected.append(item)
            category_count[category] = category_count.get(category, 0) + 1
            issue_count[issue_key] = issue_count.get(issue_key, 0) + 1

    selected.sort(key=lambda x: x["importance_score"], reverse=True)
    return selected[:max_total]


# =========================
# 13. 전체 뉴스 수집
# =========================

def collect_news(
    max_per_source=10,
    min_score=6,
    min_total=20,
    max_total=25,
    max_per_category=4,
    max_per_issue=2,
    min_spotlight=2,
    max_spotlight=5
):
    # 1. 오늘의 관심 종목 뉴스 별도 수집
    spotlight_news = collect_stock_spotlight_news(
        max_per_source=8,
        min_score=7,
        max_total=max_spotlight
    )

    # 2. 일반 시장/경제 뉴스 수집
    raw_news = collect_raw_news(
        max_per_source=max_per_source,
        min_score=min_score
    )

    final_news = select_final_news(
        raw_news=raw_news,
        min_total=min_total,
        max_total=max_total,
        max_per_category=max_per_category,
        max_per_issue=max_per_issue
    )

    # 3. 관심 종목 뉴스와 일반 뉴스 병합
    merged_news = []

    for item in spotlight_news:
        merged_news.append(item)

    for item in final_news:
        if len(merged_news) >= max_total:
            break

        if is_exact_duplicate(item, merged_news):
            continue

        if is_too_similar_article(item, merged_news, threshold=0.86):
            continue

        merged_news.append(item)

    # 4. 관심 종목 뉴스가 너무 적게 잡히면 안내
    selected_spotlight_count = len([item for item in merged_news if item["category"] == "오늘의관심종목"])

    if selected_spotlight_count < min_spotlight:
        print(f"[주의] 오늘의 관심 종목 뉴스가 {selected_spotlight_count}개만 수집되었습니다.")

    return merged_news[:max_total]


# =========================
# 14. 실행 테스트
# =========================

if __name__ == "__main__":
    news = collect_news(
        max_per_source=10,
        min_score=6,
        min_total=20,
        max_total=25,
        max_per_category=4,
        max_per_issue=2,
        min_spotlight=2,
        max_spotlight=5
    )

    print(f"최종 선택 뉴스 수: {len(news)}")
    print("=" * 80)

    print("🔥 오늘의 관심 종목 뉴스")
    print("=" * 80)

    spotlight_items = [n for n in news if n["category"] == "오늘의관심종목"]

    if not spotlight_items:
        print("오늘의 관심 종목 뉴스가 수집되지 않았습니다.")
        print("-" * 80)

    for item in spotlight_items:
        print(f"[{item['category']}] {item['title']}")
        print(f"이슈키: {item.get('issue_key')}")
        print(f"중요도: {item['importance_score']}")
        print(f"키워드: {item['matched_keywords']}")
        print(f"링크: {item['link']}")
        print("-" * 80)

    print()
    print("📰 시장/경제 주요 뉴스")
    print("=" * 80)

    market_items = [n for n in news if n["category"] != "오늘의관심종목"]

    for item in market_items:
        print(f"[{item['category']}] {item['title']}")
        print(f"이슈키: {item.get('issue_key')}")
        print(f"중요도: {item['importance_score']}")
        print(f"키워드: {item['matched_keywords']}")
        print(f"링크: {item['link']}")
        print("-" * 80)