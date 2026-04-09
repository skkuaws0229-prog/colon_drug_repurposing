#!/usr/bin/env python3
"""
CRIS 한국 임상시험 정보 수집 -> JSON 저장 + Neo4j 적재

실제 엔드포인트: https://cris.nih.go.kr/cris/search/selectBasic.do
  - AJAX GET 요청, XML 응답 (프론트엔드 listDetail.do 페이지가 호출)
  - 주요 파라미터:
      searchWord    : 자유 검색어 (제목/약물/질환 등 전체 대상)
      all_type      : "Y" (전체 검색)
      search_page   : "L" (리스트 페이지)
      search_lang   : "K" (한국어)
      page          : 페이지 번호 (1부터)
      pageSize      : 페이지당 항목 수 (기본 20)
  - 필드별 상세 검색 파라미터:
      research_title : 연구 제목
      arm_desc_kr    : 중재 설명 (약물명 검색에 유용)
      cp_contents    : 대상 질환
      system_number  : KCT 등록번호
      sponsor_agency : 후원기관
      iv_type        : 중재 유형 (의약품(Drug), 의료기구, 시술 등)
      clinical_step  : 임상 단계 (Phase0~Phase4)
      research_step  : 모집 상태
      icd10_code     : ICD-10 질병분류 (2308=신생물)
  - 키 불필요

사용법:
  python load_cris.py              # 유방암 필터 수집 (JSON 저장)
  python load_cris.py --all        # 약물 관련 전체 수집
  python load_cris.py --neo4j      # 수집 + Neo4j 적재
"""
import argparse
import json
import math
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

CRIS_AJAX_URL = "https://cris.nih.go.kr/cris/search/selectBasic.do"
PAGE_SIZE = 20  # CRIS 기본 페이지 크기

# 최종 15개 약물
DRUG_NAMES = [
    "Romidepsin", "Sepantronium bromide", "Dactinomycin", "Staurosporine",
    "Vinblastine", "Bortezomib", "SN-38", "Docetaxel", "Vinorelbine",
    "Dinaciclib", "Paclitaxel", "Rapamycin", "Camptothecin", "Luminespib",
    "Epirubicin",
]

# 한글 약물명 매핑 (CRIS 검색용)
DRUG_NAME_KR = {
    "Docetaxel": "도세탁셀",
    "Paclitaxel": "파클리탁셀",
    "Vinblastine": "빈블라스틴",
    "Vinorelbine": "비노렐빈",
    "Epirubicin": "에피루비신",
    "Bortezomib": "보르테조밉",
    "Rapamycin": "라파마이신",
    "Dactinomycin": "닥티노마이신",
    "Romidepsin": "로미뎁신",
    "Camptothecin": "캄프토테신",
}


def _fetch_cris_xml(params: dict) -> ET.Element | None:
    """CRIS selectBasic.do에 GET 요청 -> XML Element 반환.

    CRIS XML 응답에 &#xd; (U+000D) 등 XML 1.0에서 파서가 거부하는
    제어 문자 참조가 포함될 수 있어 파싱 전 정리 필요.
    """
    url = f"{CRIS_AJAX_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/xml,application/xml",
        "Accept-Language": "ko-KR,ko;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://cris.nih.go.kr/cris/search/listDetail.do",
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read().decode("utf-8", errors="replace")
    if not data.strip():
        return None
    # CRIS XML에 포함된 &#xd; 등 유효하지 않은 제어 문자 참조 제거
    data = re.sub(r"&#xd;", "\n", data, flags=re.IGNORECASE)
    data = re.sub(
        r"&#x([0-9a-fA-F]+);",
        lambda m: "" if int(m.group(1), 16) < 0x20
                       and int(m.group(1), 16) not in (0x09, 0x0A, 0x0D)
                  else m.group(0),
        data,
    )
    return ET.fromstring(data)


def _parse_item(item: ET.Element, drug_name: str) -> dict:
    """XML <item> 요소에서 Trial 정보 추출."""
    return {
        "kct_id": (item.findtext("system_number", "") or "").strip(),
        "title_kr": (item.findtext("research_title_kr", "") or "").strip()[:300],
        "title_en": (item.findtext("research_title_en", "") or "").strip()[:300],
        "research_step": (item.findtext("research_step", "") or "").strip(),
        "clinical_step": (item.findtext("clinical_step", "") or "").strip(),
        "research_kind": (item.findtext("research_kind", "") or "").strip(),
        "intervention_type": (item.findtext("intervention_type", "") or "").strip(),
        "sponsor": (item.findtext("resrc_spp", "") or "").strip(),
        "sponsor_en": (item.findtext("resrc_spp_en", "") or "").strip(),
        "institution": (item.findtext("resrc_ref", "") or "").strip(),
        "institution_en": (item.findtext("resrc_ref_en", "") or "").strip(),
        "start_date": (item.findtext("study_start_date", "") or "").strip(),
        "end_date": (item.findtext("study_complete_date", "") or "").strip(),
        "target_sex": (item.findtext("target_in_sex", "") or "").strip(),
        "conditions": (item.findtext("cp_contents", "") or "").strip()[:300],
        "arm_description": (item.findtext("arm_desc_kr", "") or "").strip()[:500],
        "disease_class": (item.findtext("my_code", "") or "").strip(),
        "primary_outcome": (item.findtext("outcome", "") or "").strip()[:300],
        "drug_name": drug_name,
        "source": "CRIS",
    }


def search_cris_pages(search_word: str, drug_name: str,
                       extra_params: dict | None = None) -> list[dict]:
    """CRIS에서 검색어로 모든 페이지 수집, 파싱된 결과 리스트 반환."""
    base_params = {
        "all_type": "Y",
        "search_page": "L",
        "search_lang": "K",
        "searchWord": search_word,
        "pageSize": str(PAGE_SIZE),
        "page": "1",
    }
    if extra_params:
        base_params.update(extra_params)

    # 첫 페이지 조회
    root = _fetch_cris_xml(base_params)
    if root is None:
        return []

    total = int(root.findtext("totalDataCnt", "0"))
    if total == 0:
        return []

    total_pages = math.ceil(total / PAGE_SIZE)
    items = [_parse_item(it, drug_name) for it in root.findall("item")]

    # 나머지 페이지 수집
    for page_num in range(2, total_pages + 1):
        time.sleep(0.5)
        base_params["page"] = str(page_num)
        page_root = _fetch_cris_xml(base_params)
        if page_root is not None:
            items.extend(_parse_item(it, drug_name) for it in page_root.findall("item"))

    return items


def search_drug(drug_name: str) -> list[dict]:
    """약물 영문명 + 한글명으로 CRIS 검색, 전 페이지 수집, 중복 제거."""
    search_terms = [drug_name]
    if drug_name in DRUG_NAME_KR:
        search_terms.append(DRUG_NAME_KR[drug_name])

    seen_ids = set()
    all_results = []

    for term in search_terms:
        try:
            items = search_cris_pages(term, drug_name)
            new_count = 0
            for item in items:
                if item["kct_id"] and item["kct_id"] not in seen_ids:
                    seen_ids.add(item["kct_id"])
                    all_results.append(item)
                    new_count += 1
            print(f"    '{term}': {len(items)}건 조회, {new_count}건 신규")
        except Exception as e:
            print(f"    [ERROR] '{term}' 검색 실패: {e}")
        time.sleep(1)

    return all_results


def filter_breast_cancer(trials: list[dict]) -> list[dict]:
    """유방암 관련 임상시험만 필터링.

    '유방', 'breast', 'mammary' 등 유방 특이적 키워드로 필터링.
    HER2/BRCA는 위암/난소암 등에도 해당하므로 단독 키워드로 사용하지 않음.
    """
    # 유방 특이적 키워드 (이것만으로도 매칭)
    breast_specific = [
        "유방", "breast", "mammary", "유선",
    ]
    # 유방암 맥락에서 의미있는 복합 키워드
    breast_compound = [
        "삼중음성", "triple negative", "tnbc",
    ]

    filtered = []
    for trial in trials:
        searchable = " ".join([
            trial.get("title_kr", ""),
            trial.get("title_en", ""),
            trial.get("conditions", ""),
        ]).lower()

        is_breast = (
            any(kw.lower() in searchable for kw in breast_specific)
            or any(kw.lower() in searchable for kw in breast_compound)
        )

        if is_breast:
            trial["disease_code"] = "BRCA"
            filtered.append(trial)
    return filtered


def load_to_neo4j(all_trials: list[dict]):
    """Neo4j에 Trial 노드 MERGE + 엣지 생성."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("[ERROR] neo4j 패키지가 설치되지 않았습니다.")
        return

    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "password"

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("  Neo4j 연결 성공")

    with driver.session() as session:
        for trial in all_trials:
            session.run(
                """
                MERGE (t:Trial {kct_id: $kct_id})
                ON CREATE SET t.title_kr = $title_kr,
                              t.title_en = $title_en,
                              t.research_step = $research_step,
                              t.clinical_step = $clinical_step,
                              t.research_kind = $research_kind,
                              t.intervention_type = $intervention_type,
                              t.sponsor = $sponsor,
                              t.institution = $institution,
                              t.conditions = $conditions,
                              t.start_date = $start_date,
                              t.end_date = $end_date,
                              t.source = 'CRIS'
                ON MATCH SET  t.title_kr = $title_kr,
                              t.research_step = $research_step,
                              t.clinical_step = $clinical_step
                """,
                **{k: trial[k] for k in [
                    "kct_id", "title_kr", "title_en", "research_step",
                    "clinical_step", "research_kind", "intervention_type",
                    "sponsor", "institution", "conditions",
                    "start_date", "end_date",
                ]},
            )
            session.run(
                """
                MATCH (d:Drug {name: $drug_name})
                MATCH (t:Trial {kct_id: $kct_id})
                MERGE (d)-[:IN_TRIAL]->(t)
                """,
                drug_name=trial["drug_name"],
                kct_id=trial["kct_id"],
            )
            session.run(
                """
                MATCH (t:Trial {kct_id: $kct_id})
                MATCH (dis:Disease {disease_code: 'BRCA'})
                MERGE (t)-[:FOR_DISEASE]->(dis)
                """,
                kct_id=trial["kct_id"],
            )

    driver.close()
    print(f"  Neo4j 적재 완료: {len(all_trials)}건")


def main():
    parser = argparse.ArgumentParser(description="CRIS 한국 임상시험 수집")
    parser.add_argument("--neo4j", action="store_true", help="Neo4j에 적재")
    parser.add_argument("--all", action="store_true",
                        help="유방암 필터 없이 약물 관련 전체 임상시험 수집")
    args = parser.parse_args()

    print("=" * 60)
    print("CRIS 한국 임상시험 수집 (AJAX XML)")
    print(f"엔드포인트: {CRIS_AJAX_URL}")
    print("=" * 60)

    all_trials = []
    drugs_with_trials = 0

    for i, drug in enumerate(DRUG_NAMES, 1):
        print(f"\n[{i}/{len(DRUG_NAMES)}] {drug} 검색 중...")
        trials = search_drug(drug)

        if not args.all:
            before = len(trials)
            trials = filter_breast_cancer(trials)
            if before > 0:
                print(f"    유방암 필터: {before}건 -> {len(trials)}건")

        if trials:
            drugs_with_trials += 1
            all_trials.extend(trials)
            print(f"  => {len(trials)}건 발견")
            for t in trials[:5]:
                print(f"    {t['kct_id']}: {t['title_kr'][:50]}...")
            if len(trials) > 5:
                print(f"    ... 외 {len(trials) - 5}건")
        else:
            print(f"  => 결과 없음")

        time.sleep(0.5)

    # 전체 중복 제거
    seen = set()
    unique_trials = []
    for t in all_trials:
        key = (t["kct_id"], t["drug_name"])
        if key not in seen:
            seen.add(key)
            unique_trials.append(t)
    all_trials = unique_trials

    # JSON 저장
    out_path = "cris_trials_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_trials, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")

    # Neo4j 적재 (옵션)
    if args.neo4j:
        print("\n[Neo4j 적재]")
        load_to_neo4j(all_trials)

    # 통계
    print("\n" + "=" * 60)
    print("완료 통계:")
    print(f"  검색 약물: {len(DRUG_NAMES)}개")
    print(f"  임상시험 발견 약물: {drugs_with_trials}개")
    print(f"  총 Trial: {len(all_trials)}건")
    unique_kct = len(set(t["kct_id"] for t in all_trials))
    print(f"  고유 KCT: {unique_kct}건")
    print(f"  소스: CRIS (cris.nih.go.kr)")
    mode = "전체" if args.all else "유방암 필터"
    print(f"  검색 모드: {mode}")
    print("=" * 60)


if __name__ == "__main__":
    main()
