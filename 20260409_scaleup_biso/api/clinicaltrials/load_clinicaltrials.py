"""
ClinicalTrials.gov 임상시험 데이터 수집 → Neo4j 적재

엔드포인트: https://clinicaltrials.gov/api/v2/studies
키 불필요 · 무료
"""

import os
import time
from pathlib import Path

import requests
from neo4j import GraphDatabase
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")

CT_URL = "https://clinicaltrials.gov/api/v2/studies"


def get_pipeline_drugs(driver) -> list[str]:
    with driver.session(database=DATABASE) as session:
        result = session.run(
            'MATCH (d:Drug) WHERE d.disease_code = "BRCA" '
            "RETURN d.name AS name ORDER BY d.rank"
        ).data()
    return [r["name"] for r in result]


def fetch_trials(drug_name: str, page_size: int = 5) -> list[dict] | None:
    params = {
        "query.intr": drug_name,
        "query.cond": "breast cancer",
        "filter.overallStatus": "RECRUITING|ACTIVE_NOT_RECRUITING",
        "fields": "NCTId,BriefTitle,Phase,OverallStatus,LeadSponsorName,StartDate,PrimaryCompletionDate",
        "pageSize": page_size,
    }
    try:
        resp = requests.get(CT_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("studies", [])
    except Exception as e:
        print(f"    ✗ API 에러: {e}")
        return None


def parse_study(study: dict) -> dict:
    proto = study.get("protocolSection", {})
    ident = proto.get("identificationModule", {})
    status_mod = proto.get("statusModule", {})
    design = proto.get("designModule", {})
    sponsor_mod = proto.get("sponsorCollaboratorsModule", {})

    nct_id = ident.get("nctId", "")
    title = ident.get("briefTitle", "")
    status = status_mod.get("overallStatus", "")
    start_date = status_mod.get("startDateStruct", {}).get("date", "")
    completion_date = status_mod.get("primaryCompletionDateStruct", {}).get("date", "")

    phases = design.get("phases", [])
    phase = phases[0] if phases else ""

    lead = sponsor_mod.get("leadSponsor", {})
    sponsor = lead.get("name", "")

    return {
        "nct_id": nct_id,
        "title": title,
        "phase": phase,
        "status": status,
        "sponsor": sponsor,
        "start_date": start_date,
        "completion_date": completion_date,
    }


def load_to_neo4j(driver, drug_name: str, trials: list[dict]):
    with driver.session(database=DATABASE) as session:
        for t in trials:
            session.run(
                """
                MERGE (tr:Trial {nct_id: $nct_id})
                SET tr.title           = $title,
                    tr.phase           = $phase,
                    tr.status          = $status,
                    tr.sponsor         = $sponsor,
                    tr.start_date      = $start_date,
                    tr.completion_date = $completion_date,
                    tr.disease_code    = 'BRCA'
                WITH tr
                MATCH (d:Drug {name: $drug_name})
                MERGE (d)-[r:IN_TRIAL]->(tr)
                SET r.phase  = $phase,
                    r.status = $status
                WITH tr
                MATCH (dis:Disease {code: 'BRCA'})
                MERGE (tr)-[:FOR_DISEASE]->(dis)
                """,
                nct_id=t["nct_id"],
                title=t["title"],
                phase=t["phase"],
                status=t["status"],
                sponsor=t["sponsor"],
                start_date=t["start_date"],
                completion_date=t["completion_date"],
                drug_name=drug_name,
            )


def main():
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print(f"Neo4j 연결: {URI}\n")

    drugs = get_pipeline_drugs(driver)
    print(f"대상 약물: {len(drugs)}개\n")

    for i, drug in enumerate(drugs, 1):
        print(f"  [{i}/{len(drugs)}] {drug} ... ", end="", flush=True)

        studies = fetch_trials(drug)
        if studies is None:
            print("건너뜀")
        elif len(studies) == 0:
            print("진행 중인 임상시험 없음")
        else:
            trials = [parse_study(s) for s in studies]
            trials = [t for t in trials if t["nct_id"]]  # nct_id 없는 것 제외
            load_to_neo4j(driver, drug, trials)
            ncts = [t["nct_id"] for t in trials]
            print(f"✓ {len(trials)}개 ({', '.join(ncts)})")

        if i < len(drugs):
            time.sleep(1)

    # 통계
    with driver.session(database=DATABASE) as session:
        trial_cnt = session.run("MATCH (t:Trial) RETURN count(t) AS cnt").single()["cnt"]
        in_trial = session.run("MATCH ()-[r:IN_TRIAL]->() RETURN count(r) AS cnt").single()["cnt"]
        for_dis = session.run("MATCH ()-[r:FOR_DISEASE]->() RETURN count(r) AS cnt").single()["cnt"]
        se_cnt = session.run("MATCH (s:SideEffect) RETURN count(s) AS cnt").single()["cnt"]
        hse_cnt = session.run("MATCH ()-[r:HAS_SIDE_EFFECT]->() RETURN count(r) AS cnt").single()["cnt"]

    print(f"\n{'='*50}")
    print(f"  ClinicalTrials 적재 완료")
    print(f"{'='*50}")
    print(f"  Trial 노드: {trial_cnt}개")
    print(f"  IN_TRIAL 엣지: {in_trial}개")
    print(f"  FOR_DISEASE 엣지: {for_dis}개")

    print(f"\n{'='*50}")
    print(f"  전체 외부 API 통계")
    print(f"{'='*50}")
    print(f"  SideEffect 노드: {se_cnt}개")
    print(f"  HAS_SIDE_EFFECT 엣지: {hse_cnt}개")
    print(f"  Trial 노드: {trial_cnt}개")
    print(f"  IN_TRIAL 엣지: {in_trial}개")
    print(f"  FOR_DISEASE 엣지: {for_dis}개")

    driver.close()


if __name__ == "__main__":
    main()
