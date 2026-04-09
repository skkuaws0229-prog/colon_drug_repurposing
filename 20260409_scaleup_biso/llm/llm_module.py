#!/usr/bin/env python3
"""
LLM 보조 모듈 — 뉴스 검색, 생활 가이드, 유명인 사례

채팅 어시스턴트에서 import해서 실시간 조회용
Neo4j 저장 안 함
"""
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime


# ── 1. 뉴스/기사 검색 ──────────────────────────────────────


def search_news(query: str = "유방암", max_results: int = 5) -> list[dict]:
    """
    Google News RSS로 최신 뉴스 검색.

    Args:
        query: 검색어 (예: '유방암', 'breast cancer treatment')
        max_results: 최대 결과 수

    Returns:
        [{title, url, date, summary}, ...]
    """
    encoded = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko"

    req = urllib.request.Request(rss_url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return [{"error": f"뉴스 검색 실패: {e}"}]

    root = ET.fromstring(data)
    channel = root.find("channel")
    if channel is None:
        return []

    results = []
    for item in channel.findall("item")[:max_results]:
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        pub_date = item.findtext("pubDate", "")
        description = item.findtext("description", "")

        # HTML 태그 제거
        summary = re.sub(r"<[^>]+>", "", description).strip()
        if len(summary) > 200:
            summary = summary[:200] + "..."

        results.append({
            "title": title,
            "url": link,
            "date": pub_date,
            "summary": summary,
        })

    return results


# ── 2. 생활 가이드 ──────────────────────────────────────────

# 국립암센터 + 의학 가이드라인 기반 정적 데이터
_LIFESTYLE_GUIDES = {
    "음식": {
        "cancer_type": "유방암",
        "recommendations": [
            "균형 잡힌 식단 유지: 과일, 채소, 통곡물, 저지방 단백질 중심",
            "항산화 식품 섭취: 블루베리, 브로콜리, 시금치, 토마토, 녹차",
            "오메가-3 지방산: 연어, 고등어, 아마씨, 호두",
            "콩류/두부: 이소플라본 함유 (적정량 섭취 권장)",
            "충분한 수분 섭취: 하루 1.5~2L 물",
            "제한 권고: 가공육, 붉은 고기(주 500g 이하), 알코올, 고당분 음료",
            "항암치료 중 식욕 저하 시: 소량 자주 식사, 고칼로리 간식 활용",
            "면역력 강화: 버섯류(표고, 상황), 마늘, 생강",
        ],
        "source": "국립암센터 생활백서 + 대한암학회 영양 가이드라인",
    },
    "운동": {
        "cancer_type": "유방암",
        "recommendations": [
            "주 150분 이상 중등도 유산소 운동 (빠른 걷기, 자전거)",
            "주 2~3회 근력 운동 (밴드, 가벼운 덤벨)",
            "유방암 수술 후: 팔 림프부종 예방 스트레칭 필수",
            "항암치료 중: 가벼운 산책부터 시작, 무리하지 않기",
            "요가/필라테스: 유연성 + 정신건강에 도움",
            "수영: 관절 부담 적고 전신 운동 효과",
            "운동 전후 충분한 수분 섭취",
            "피로감 심할 때는 휴식 우선, 컨디션에 맞게 조절",
        ],
        "source": "대한암학회 운동 권고안 + ACSM 암환자 운동 가이드라인",
    },
    "수면": {
        "cancer_type": "유방암",
        "recommendations": [
            "규칙적인 수면-기상 시간 유지 (하루 7~8시간)",
            "취침 전 1시간 스마트폰/TV 자제 (블루라이트 차단)",
            "카페인은 오후 2시 이전까지만",
            "침실 환경: 어둡고 시원하게 (18~22도)",
            "취침 전 이완 요법: 명상, 복식호흡, 가벼운 스트레칭",
            "불면증 지속 시 담당의와 상담 (호르몬치료 부작용 가능)",
            "낮잠은 30분 이내로 제한",
            "수면일기 작성으로 패턴 파악",
        ],
        "source": "국립암센터 + 대한수면학회 권고",
    },
    "스트레스": {
        "cancer_type": "유방암",
        "recommendations": [
            "감정 표현하기: 가족/친구/환우회와 대화",
            "전문 상담: 암 경험자 심리상담 프로그램 활용",
            "마음챙김 명상: 하루 10~15분",
            "규칙적 운동: 스트레스 호르몬 감소 효과",
            "취미 활동: 그림, 음악, 원예 등",
            "정보 과잉 주의: 신뢰할 수 있는 정보원만 확인 (국립암센터, 주치의)",
            "암 환자 자조 모임/환우회 참여",
            "불안/우울 증상 지속 시 정신건강의학과 상담",
        ],
        "source": "국립암센터 심리지원 프로그램 + 대한정신종양학회",
    },
}


def get_lifestyle_guide(topic: str, cancer_type: str = "유방암") -> dict:
    """
    암환자 생활 가이드 반환.

    Args:
        topic: '음식' | '운동' | '수면' | '스트레스'
        cancer_type: 암 종류 (현재 유방암만 지원)

    Returns:
        {topic, cancer_type, recommendations: [...], source}
    """
    # 키워드 매핑
    topic_map = {
        "음식": "음식", "식단": "음식", "식사": "음식", "영양": "음식",
        "먹을": "음식", "food": "음식", "diet": "음식", "nutrition": "음식",
        "운동": "운동", "exercise": "운동", "fitness": "운동", "걷기": "운동",
        "수면": "수면", "잠": "수면", "sleep": "수면", "불면": "수면",
        "스트레스": "스트레스", "stress": "스트레스", "불안": "스트레스",
        "우울": "스트레스", "마음": "스트레스", "심리": "스트레스",
    }

    matched_topic = None
    topic_lower = topic.lower()
    for keyword, mapped in topic_map.items():
        if keyword in topic_lower:
            matched_topic = mapped
            break

    if not matched_topic:
        return {
            "topic": topic,
            "cancer_type": cancer_type,
            "recommendations": [
                f"'{topic}'에 대한 가이드를 찾을 수 없습니다.",
                "지원 주제: 음식, 운동, 수면, 스트레스",
            ],
            "source": "N/A",
        }

    guide = _LIFESTYLE_GUIDES[matched_topic]
    return {
        "topic": matched_topic,
        "cancer_type": cancer_type,
        "recommendations": guide["recommendations"],
        "source": guide["source"],
    }


# ── 3. 유명인 치료 사례 ─────────────────────────────────────

# 공개된 사례만 수록 (언론 보도 기반)
_CELEBRITY_CASES = [
    {
        "name": "앤젤리나 졸리 (Angelina Jolie)",
        "story": "BRCA1 유전자 변이 보유 확인 후 2013년 예방적 양측 유방절제술 시행. "
                 "2015년 난소·난관 절제술 추가. 뉴욕타임스 기고로 'BRCA 검사' 인식 확산에 기여.",
        "treatment": "예방적 양측 유방절제술, 난소·난관 절제술",
        "outcome": "건강 유지 중",
        "year": "2013",
    },
    {
        "name": "셰릴 크로우 (Sheryl Crow)",
        "story": "2006년 초기 유방암(0기 관내암) 진단. 유방보존술 + 방사선치료 후 완치. "
                 "유방암 조기 검진 캠페인에 적극 참여.",
        "treatment": "유방보존술, 방사선치료",
        "outcome": "완치 (2006~현재 건강)",
        "year": "2006",
    },
    {
        "name": "카일리 미노그 (Kylie Minogue)",
        "story": "2005년 유방암 진단. 수술 + 항암화학요법 시행. "
                 "치료 후 복귀하여 활발히 활동 중. 조기 검진의 중요성 강조.",
        "treatment": "유방절제술, 항암화학요법",
        "outcome": "완치 후 활동 복귀",
        "year": "2005",
    },
    {
        "name": "줄리아 루이스-드레이퍼스 (Julia Louis-Dreyfus)",
        "story": "2017년 유방암 진단 공개. 수술 + 항암치료 후 2018년 복귀. "
                 "미국 의료보험 접근성 문제에 대해 목소리를 냄.",
        "treatment": "수술, 항암화학요법",
        "outcome": "완치 후 활동 복귀",
        "year": "2017",
    },
    {
        "name": "윤정희 (한국 배우)",
        "story": "2000년대 초 유방암 투병 사실이 알려짐. "
                 "한국 유방암 인식 제고에 기여.",
        "treatment": "수술, 항암치료",
        "outcome": "투병 후 회복",
        "year": "2000s",
    },
    {
        "name": "산드라 리 (Sandra Lee)",
        "story": "2015년 유방암 진단. 양측 유방절제술 시행. "
                 "치료 과정을 공개하며 유방암 검진 캠페인 진행.",
        "treatment": "양측 유방절제술",
        "outcome": "완치 후 건강",
        "year": "2015",
    },
]


def search_celebrity_cases(cancer_type: str = "유방암") -> list[dict]:
    """
    공개된 유명인 유방암 치료 사례 반환.

    Args:
        cancer_type: 암 종류 (현재 유방암만 지원)

    Returns:
        [{name, story, treatment, outcome, year}, ...]
    """
    return _CELEBRITY_CASES


# ── 통합 인터페이스 ─────────────────────────────────────────


def get_llm_info(query_type: str, **kwargs) -> dict:
    """
    통합 인터페이스.

    Args:
        query_type: 'news' | 'lifestyle' | 'celebrity'
        **kwargs:
            query: 뉴스 검색어 (news)
            max_results: 뉴스 최대 결과 (news)
            topic: 생활 가이드 주제 (lifestyle)

    Returns:
        dict
    """
    if query_type == "news":
        query = kwargs.get("query", "유방암")
        max_results = kwargs.get("max_results", 5)
        return {"news": search_news(query, max_results)}
    elif query_type == "lifestyle":
        topic = kwargs.get("topic", "음식")
        return get_lifestyle_guide(topic)
    elif query_type == "celebrity":
        return {"cases": search_celebrity_cases()}
    else:
        return {"error": f"Unknown query_type: {query_type}. Use: news/lifestyle/celebrity"}


# ── 테스트 ─────────────────────────────────────────────────


def main():
    print("=" * 60)
    print("LLM 보조 모듈 테스트")
    print("=" * 60)

    # 1) 뉴스 검색
    print("\n[1] search_news('유방암')")
    news = search_news("유방암", max_results=3)
    print(f"  → {len(news)}건")
    for n in news[:3]:
        if "error" in n:
            print(f"  [ERROR] {n['error']}")
        else:
            print(f"  {n['title'][:60]}...")
            print(f"    {n['date']}")

    # 2) 생활 가이드
    for topic in ["음식", "운동", "수면", "스트레스"]:
        print(f"\n[2] get_lifestyle_guide('{topic}')")
        guide = get_lifestyle_guide(topic)
        print(f"  주제: {guide['topic']}")
        print(f"  권고 {len(guide['recommendations'])}개:")
        for r in guide["recommendations"][:3]:
            print(f"    - {r}")
        print(f"  출처: {guide['source']}")

    # 3) 유명인 사례
    print(f"\n[3] search_celebrity_cases()")
    cases = search_celebrity_cases()
    print(f"  → {len(cases)}건")
    for c in cases[:3]:
        print(f"  {c['name']} ({c['year']}): {c['treatment']}")

    # 4) 통합 테스트
    print(f"\n[4] get_llm_info() 통합 테스트")
    for qt in ["news", "lifestyle", "celebrity"]:
        kwargs = {"topic": "운동"} if qt == "lifestyle" else {}
        r = get_llm_info(qt, **kwargs)
        if qt == "news":
            print(f"  get_llm_info('news'): {len(r.get('news', []))}건")
        elif qt == "lifestyle":
            print(f"  get_llm_info('lifestyle'): {r.get('topic', '')}")
        else:
            print(f"  get_llm_info('celebrity'): {len(r.get('cases', []))}건")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
