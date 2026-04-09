#!/usr/bin/env python3
"""
국립암센터 (cancer.go.kr) 문서 API → LLM 실시간 조회 모듈

엔드포인트:
  - /api/cancer.do           : 암 종류별 상세 정보 (유방암 menu_seq=217)
  - /api/prevention.do       : 암 예방·검진 교육 콘텐츠
  - /api/data.do             : 암환자 생활백서 갤러리
  - /api/dictionaryworks.do  : 암 의학용어 한/영 사전 (3500+ 항목)

Neo4j 저장 안 함 — 채팅 어시스턴트에서 import해서 실시간 조회용

사용법:
  python ncis_content.py              # 전체 테스트
  python ncis_content.py --save       # JSON 저장
"""
import json
import re
import urllib.parse
import urllib.request

BASE_URL = "https://www.cancer.go.kr"

ENDPOINTS = {
    "cancer": f"{BASE_URL}/api/cancer.do",
    "prevention": f"{BASE_URL}/api/prevention.do",
    "data": f"{BASE_URL}/api/data.do",
    "dictionary": f"{BASE_URL}/api/dictionaryworks.do",
}

BREAST_KEYWORDS = [
    "유방", "breast", "BRCA", "HER2", "삼중음성", "triple negative",
    "mammary", "mastectomy", "유선",
]


# ── 내부 유틸 ──────────────────────────────────────────────

def _fetch_json(url: str) -> dict | None:
    """GET → JSON 파싱."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"  [ERROR] {url}: {e}")
        return None


def _strip_html(html: str) -> str:
    """HTML 태그 제거 → 순수 텍스트."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", text).strip()


def _is_breast_related(text: str) -> bool:
    lower = text.lower()
    return any(kw.lower() in lower for kw in BREAST_KEYWORDS)


# ── 공개 API 함수 ──────────────────────────────────────────


def get_brca_info() -> dict:
    """
    /api/cancer.do → 유방암 상세 정보 (정의/증상/진단/치료).

    Returns:
        {title: content_text, ...}  카테고리별 텍스트
    """
    data = _fetch_json(ENDPOINTS["cancer"])
    if not data:
        return {}

    results = {}
    for item in data.get("result", []):
        conts = item.get("conts", "")
        title = item.get("title", "")
        navi = item.get("page_navi", "")

        if not conts or len(conts) < 50:
            continue

        text = _strip_html(conts)
        if not text or len(text) < 20:
            continue

        searchable = f"{title} {navi} {text}"
        if _is_breast_related(searchable):
            results[title] = text

    return results


def get_prevention_info() -> dict:
    """
    /api/prevention.do → 암 예방/검진 정보 (유방암 관련 필터링).

    Returns:
        {title: content_text, ...}
    """
    data = _fetch_json(ENDPOINTS["prevention"])
    if not data:
        return {}

    results = {}
    for item in data.get("result", []):
        conts = item.get("conts", "")
        title = item.get("title", "")
        navi = item.get("page_navi", "")

        if not conts or len(conts) < 50:
            continue

        text = _strip_html(conts)
        if not text or len(text) < 20:
            continue

        searchable = f"{title} {navi} {text}"
        if _is_breast_related(searchable):
            results[title] = text

    return results


def get_patient_guide() -> dict:
    """
    /api/data.do → 암환자 생활백서 (유방암 관련 필터링).

    Returns:
        {title: content_or_description, ...}
    """
    data = _fetch_json(ENDPOINTS["data"])
    if not data:
        return {}

    results = {}
    for item in data.get("result", []):
        title = item.get("title", "")
        conts = item.get("conts", "")
        text = _strip_html(conts) if conts else ""

        searchable = f"{title} {text}"
        if _is_breast_related(searchable):
            results[title] = text if text else "(이미지 자료)"

    return results


def get_medical_term(term: str) -> dict:
    """
    /api/dictionaryworks.do → 의학 용어 사전 조회.

    Args:
        term: 검색어 (예: '타목시펜', 'BRCA', '유방암')

    Returns:
        {korean_term: {english: ..., definition: ...}, ...}
    """
    data = _fetch_json(ENDPOINTS["dictionary"])
    if not data:
        return {}

    term_lower = term.lower()
    results = {}
    for item in data.get("result", []):
        kor = item.get("work_kor", "")
        eng = item.get("work_eng", "")
        defn = item.get("sense_kor", "")
        defn_text = _strip_html(defn) if defn else ""

        searchable = f"{kor} {eng} {defn_text}".lower()
        if term_lower in searchable:
            results[kor] = {
                "english": eng,
                "definition": defn_text,
            }

    return results


def get_ncis_info(query_type: str, **kwargs) -> dict:
    """
    통합 인터페이스 — 채팅에서 호출하는 단일 진입점.

    Args:
        query_type: 'brca' | 'prevention' | 'guide' | 'term'
        **kwargs:
            term: 사전 검색어 (query_type='term' 일 때 필수)

    Returns:
        dict — 각 함수의 반환값
    """
    if query_type == "brca":
        return get_brca_info()
    elif query_type == "prevention":
        return get_prevention_info()
    elif query_type == "guide":
        return get_patient_guide()
    elif query_type == "term":
        term = kwargs.get("term", "유방암")
        return get_medical_term(term)
    else:
        return {"error": f"Unknown query_type: {query_type}. Use: brca/prevention/guide/term"}


# ── 테스트 ─────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="국립암센터 문서 API 테스트")
    parser.add_argument("--save", action="store_true", help="결과 JSON 저장")
    args = parser.parse_args()

    print("=" * 60)
    print("국립암센터 (cancer.go.kr) 문서 API 테스트")
    print("=" * 60)

    all_results = {}

    # 1) 유방암 상세 정보
    print("\n[1] get_brca_info()")
    brca = get_brca_info()
    all_results["brca"] = brca
    print(f"  → {len(brca)}개 항목")
    for title, content in list(brca.items())[:3]:
        print(f"  {title}: {content[:80]}...")

    # 2) 예방/검진 정보
    print("\n[2] get_prevention_info()")
    prev = get_prevention_info()
    all_results["prevention"] = prev
    print(f"  → {len(prev)}개 항목")
    for title, content in list(prev.items())[:3]:
        print(f"  {title}: {content[:80]}...")

    # 3) 생활백서
    print("\n[3] get_patient_guide()")
    guide = get_patient_guide()
    all_results["guide"] = guide
    print(f"  → {len(guide)}개 항목")
    for title, content in list(guide.items())[:3]:
        print(f"  {title}: {content[:80]}...")

    # 4) 용어 사전
    test_terms = ["타목시펜", "BRCA", "유방암"]
    all_results["terms"] = {}
    for term in test_terms:
        print(f"\n[4] get_medical_term('{term}')")
        terms = get_medical_term(term)
        all_results["terms"][term] = terms
        print(f"  → {len(terms)}개 결과")
        for kor, info in list(terms.items())[:2]:
            print(f"  {kor} ({info['english']})")
            print(f"    {info['definition'][:80]}...")

    # 5) 통합 인터페이스 테스트
    print("\n[5] get_ncis_info() 통합 테스트")
    for qt in ["brca", "prevention", "guide"]:
        r = get_ncis_info(qt)
        print(f"  get_ncis_info('{qt}'): {len(r)}개")
    r = get_ncis_info("term", term="HER2")
    print(f"  get_ncis_info('term', term='HER2'): {len(r)}개")

    # 저장
    if args.save:
        out_path = "ncis_content_result.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n결과 저장: {out_path}")

    # 통계
    print("\n" + "=" * 60)
    print("반환 데이터 구조:")
    print(f"  get_brca_info()        → dict  {{title: text}}         {len(brca)}개")
    print(f"  get_prevention_info()  → dict  {{title: text}}         {len(prev)}개")
    print(f"  get_patient_guide()    → dict  {{title: text}}         {len(guide)}개")
    print(f"  get_medical_term(str)  → dict  {{term: {{eng, def}}}}  (검색어별)")
    print(f"  get_ncis_info(type)    → dict  (통합 진입점)")
    print("=" * 60)


if __name__ == "__main__":
    main()
