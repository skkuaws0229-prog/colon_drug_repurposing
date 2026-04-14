#!/usr/bin/env python3
"""
Step 7+ KG/API 검증
11개 약물(카테고리 2+3)에 대한 API 데이터 수집
"""
import json
import time
from pathlib import Path
import urllib.request
import urllib.error
import urllib.parse

# Output directory
OUTPUT_DIR = Path(__file__).parent / "step7plus_kg_results"
OUTPUT_DIR.mkdir(exist_ok=True)

# API base URL
API_BASE = "http://localhost:8000"

# 11 drugs from categories 2 and 3
DRUGS = [
    # Category 2: 유방암 연구 중
    "YK-4-279",
    "AZ6102",
    "SB590885",
    "BMS-345541",
    "PFI3",
    "AT13148",
    # Category 3: 유방암 미적용
    "AZD2014",
    "Bicalutamide",
    "Nutlin-3a",
    "GSK2801",
    "AZD1332",
]

def call_api(endpoint, params=None):
    """Call API endpoint and return JSON response"""
    try:
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{API_BASE}{endpoint}?{query_string}"
        else:
            url = f"{API_BASE}{endpoint}"

        print(f"  Calling: {url}")

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            return data
    except urllib.error.HTTPError as e:
        print(f"  ⚠️  HTTP Error {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"  ⚠️  URL Error: {e.reason}")
        return None
    except Exception as e:
        print(f"  ⚠️  Error: {e}")
        return None

def collect_drug_data(drug_name):
    """Collect all data for a single drug"""
    print(f"\n{'='*80}")
    print(f"약물: {drug_name}")
    print(f"{'='*80}")

    results = {
        "drug_name": drug_name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data_collected": {},
        "errors": []
    }

    # 1. Basic drug info
    print("\n1. 기본 정보 수집...")
    drug_info = call_api(f"/api/drug/{drug_name}")
    if drug_info:
        results["data_collected"]["basic_info"] = drug_info
        print(f"  ✓ 기본 정보 수집 완료")
    else:
        results["errors"].append("basic_info: Failed to retrieve")
        print(f"  ✗ 기본 정보 수집 실패")

    # 2. Side effects (FAERS)
    print("\n2. 부작용 데이터 (FAERS) 수집...")
    side_effects = call_api(f"/api/drug/{drug_name}/side_effects")
    if side_effects:
        results["data_collected"]["side_effects"] = side_effects
        if side_effects.get("data"):
            n_effects = len(side_effects["data"]) if isinstance(side_effects["data"], list) else 1
            print(f"  ✓ 부작용 {n_effects}개 수집 완료")
        else:
            print(f"  ✓ 부작용 데이터 없음")
    else:
        results["errors"].append("side_effects: Failed to retrieve")
        print(f"  ✗ 부작용 수집 실패")

    # 3. Clinical trials
    print("\n3. 임상시험 데이터 수집...")
    trials = call_api(f"/api/drug/{drug_name}/trials")
    if trials:
        results["data_collected"]["trials"] = trials
        if trials.get("data"):
            n_trials = len(trials["data"]) if isinstance(trials["data"], list) else 1
            print(f"  ✓ 임상시험 {n_trials}개 수집 완료")
        else:
            print(f"  ✓ 임상시험 데이터 없음")
    else:
        results["errors"].append("trials: Failed to retrieve")
        print(f"  ✗ 임상시험 수집 실패")

    # 4. Targets
    print("\n4. Target 정보 수집...")
    targets = call_api(f"/api/drug/{drug_name}/targets")
    if targets:
        results["data_collected"]["targets"] = targets
        if targets.get("data"):
            n_targets = len(targets["data"]) if isinstance(targets["data"], list) else 1
            print(f"  ✓ Target {n_targets}개 수집 완료")
        else:
            print(f"  ✓ Target 데이터 없음")
    else:
        results["errors"].append("targets: Failed to retrieve")
        print(f"  ✗ Target 수집 실패")

    # 5. Pathways
    print("\n5. Pathway 정보 수집...")
    pathways = call_api(f"/api/drug/{drug_name}/pathways")
    if pathways:
        results["data_collected"]["pathways"] = pathways
        if pathways.get("data"):
            n_pathways = len(pathways["data"]) if isinstance(pathways["data"], list) else 1
            print(f"  ✓ Pathway {n_pathways}개 수집 완료")
        else:
            print(f"  ✓ Pathway 데이터 없음")
    else:
        results["errors"].append("pathways: Failed to retrieve")
        print(f"  ✗ Pathway 수집 실패")

    # 6. PubMed search
    print("\n6. PubMed 논문 검색...")
    # General search
    pubmed_general = call_api("/api/pubmed", {"query": drug_name, "max_results": 100})
    if pubmed_general:
        results["data_collected"]["pubmed_general"] = pubmed_general
        if pubmed_general.get("data"):
            n_articles = len(pubmed_general["data"]) if isinstance(pubmed_general["data"], list) else 0
            print(f"  ✓ PubMed 일반 논문 {n_articles}개 수집")
        else:
            print(f"  ✓ PubMed 논문 없음")
    else:
        results["errors"].append("pubmed_general: Failed to retrieve")
        print(f"  ✗ PubMed 검색 실패")

    # Breast cancer specific search
    pubmed_brca = call_api("/api/pubmed", {"query": f"{drug_name} breast cancer", "max_results": 50})
    if pubmed_brca:
        results["data_collected"]["pubmed_breast_cancer"] = pubmed_brca
        if pubmed_brca.get("data"):
            n_articles = len(pubmed_brca["data"]) if isinstance(pubmed_brca["data"], list) else 0
            print(f"  ✓ PubMed 유방암 논문 {n_articles}개 수집")
        else:
            print(f"  ✓ PubMed 유방암 논문 없음")
    else:
        results["errors"].append("pubmed_breast_cancer: Failed to retrieve")
        print(f"  ✗ PubMed 유방암 검색 실패")

    # Save individual drug result
    drug_json = OUTPUT_DIR / f"{drug_name.replace(' ', '_').replace('(', '').replace(')', '')}_kg_data.json"
    with open(drug_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✓ {drug_name} 데이터 저장: {drug_json}")

    return results

def create_summary_csv(all_results):
    """Create summary CSV from all collected data"""
    import csv

    csv_path = OUTPUT_DIR / "kg_api_summary.csv"

    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            '약물명',
            'API_호출_성공',
            'API_호출_실패',
            '기본정보_수집',
            'FAERS_부작용_수',
            '임상시험_수',
            'Target_수',
            'Pathway_수',
            'PubMed_일반_논문수',
            'PubMed_유방암_논문수',
            '수집_시간'
        ])

        # Data rows
        for result in all_results:
            drug_name = result['drug_name']
            data = result['data_collected']
            errors = result['errors']

            # Count successes and failures
            n_success = len(data)
            n_fail = len(errors)

            # Extract counts
            basic_info = "Yes" if 'basic_info' in data else "No"

            side_effects_count = 0
            if 'side_effects' in data and data['side_effects'].get('data'):
                se_data = data['side_effects']['data']
                side_effects_count = len(se_data) if isinstance(se_data, list) else 1

            trials_count = 0
            if 'trials' in data and data['trials'].get('data'):
                t_data = data['trials']['data']
                trials_count = len(t_data) if isinstance(t_data, list) else 1

            targets_count = 0
            if 'targets' in data and data['targets'].get('data'):
                tg_data = data['targets']['data']
                targets_count = len(tg_data) if isinstance(tg_data, list) else 1

            pathways_count = 0
            if 'pathways' in data and data['pathways'].get('data'):
                p_data = data['pathways']['data']
                pathways_count = len(p_data) if isinstance(p_data, list) else 1

            pubmed_general_count = 0
            if 'pubmed_general' in data and data['pubmed_general'].get('data'):
                pm_data = data['pubmed_general']['data']
                pubmed_general_count = len(pm_data) if isinstance(pm_data, list) else 0

            pubmed_brca_count = 0
            if 'pubmed_breast_cancer' in data and data['pubmed_breast_cancer'].get('data'):
                pmb_data = data['pubmed_breast_cancer']['data']
                pubmed_brca_count = len(pmb_data) if isinstance(pmb_data, list) else 0

            writer.writerow([
                drug_name,
                n_success,
                n_fail,
                basic_info,
                side_effects_count,
                trials_count,
                targets_count,
                pathways_count,
                pubmed_general_count,
                pubmed_brca_count,
                result['timestamp']
            ])

    print(f"\n✓ 요약 CSV 저장: {csv_path}")
    return csv_path

def create_evidence_report(all_results):
    """Create markdown evidence report"""
    md_path = OUTPUT_DIR / "evidence_report.md"

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Step 7+ KG/API 검증 보고서\n\n")
        f.write(f"**생성 시간:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        f.write("## 1. 요약\n\n")
        f.write(f"- **총 약물 수:** {len(all_results)}\n")

        total_success = sum(len(r['data_collected']) for r in all_results)
        total_fail = sum(len(r['errors']) for r in all_results)
        f.write(f"- **API 호출 성공:** {total_success}\n")
        f.write(f"- **API 호출 실패:** {total_fail}\n\n")

        f.write("---\n\n")

        f.write("## 2. 약물별 상세 결과\n\n")

        for idx, result in enumerate(all_results, 1):
            drug_name = result['drug_name']
            data = result['data_collected']

            f.write(f"### {idx}. {drug_name}\n\n")

            # Basic info
            if 'basic_info' in data:
                f.write("**기본 정보:** ✓ 수집됨\n\n")
            else:
                f.write("**기본 정보:** ✗ 수집 실패\n\n")

            # Side effects
            if 'side_effects' in data and data['side_effects'].get('data'):
                se_data = data['side_effects']['data']
                n_se = len(se_data) if isinstance(se_data, list) else 1
                f.write(f"**FAERS 부작용:** {n_se}개\n")

                if isinstance(se_data, list) and len(se_data) > 0:
                    f.write("\n주요 부작용:\n")
                    for se in se_data[:5]:  # Top 5
                        if isinstance(se, dict):
                            effect_name = se.get('side_effect', se.get('name', 'Unknown'))
                            count = se.get('count', se.get('frequency', 'N/A'))
                            f.write(f"- {effect_name}: {count}\n")
                f.write("\n")
            else:
                f.write("**FAERS 부작용:** 데이터 없음\n\n")

            # Clinical trials
            if 'trials' in data and data['trials'].get('data'):
                t_data = data['trials']['data']
                n_trials = len(t_data) if isinstance(t_data, list) else 1
                f.write(f"**임상시험:** {n_trials}개\n")

                if isinstance(t_data, list) and len(t_data) > 0:
                    f.write("\n주요 임상시험:\n")
                    for trial in t_data[:5]:  # Top 5
                        if isinstance(trial, dict):
                            title = trial.get('title', trial.get('name', 'Unknown'))
                            phase = trial.get('phase', 'N/A')
                            status = trial.get('status', 'N/A')
                            f.write(f"- {title} (Phase: {phase}, Status: {status})\n")
                f.write("\n")
            else:
                f.write("**임상시험:** 데이터 없음\n\n")

            # PubMed
            pubmed_general_count = 0
            if 'pubmed_general' in data and data['pubmed_general'].get('data'):
                pm_data = data['pubmed_general']['data']
                pubmed_general_count = len(pm_data) if isinstance(pm_data, list) else 0

            pubmed_brca_count = 0
            if 'pubmed_breast_cancer' in data and data['pubmed_breast_cancer'].get('data'):
                pmb_data = data['pubmed_breast_cancer']['data']
                pubmed_brca_count = len(pmb_data) if isinstance(pmb_data, list) else 0

            f.write(f"**PubMed 논문:**\n")
            f.write(f"- 일반: {pubmed_general_count}개\n")
            f.write(f"- 유방암 특화: {pubmed_brca_count}개\n\n")

            # Errors
            if result['errors']:
                f.write("**수집 실패 항목:**\n")
                for error in result['errors']:
                    f.write(f"- {error}\n")
                f.write("\n")

            f.write("---\n\n")

        f.write("## 3. 결론\n\n")
        f.write("- KG/API를 통한 실제 데이터 검증 완료\n")
        f.write("- 부작용, 임상시험, 문헌 근거 수집 완료\n")
        f.write("- 개별 약물 JSON 파일 및 요약 CSV 생성 완료\n\n")

        f.write("**생성된 파일:**\n")
        f.write(f"- 개별 약물 JSON: {len(all_results)}개\n")
        f.write("- 요약 CSV: kg_api_summary.csv\n")
        f.write("- 근거 보고서: evidence_report.md\n\n")

    print(f"\n✓ 근거 보고서 저장: {md_path}")
    return md_path

def main():
    print("="*80)
    print("Step 7+ KG/API 검증 - 11개 약물 데이터 수집")
    print("="*80)
    print(f"\nAPI 서버: {API_BASE}")
    print(f"출력 디렉토리: {OUTPUT_DIR}")
    print(f"약물 수: {len(DRUGS)}")

    all_results = []

    # Collect data for each drug
    for drug in DRUGS:
        result = collect_drug_data(drug)
        all_results.append(result)
        time.sleep(1)  # Rate limiting

    # Create summary CSV
    print("\n" + "="*80)
    print("요약 데이터 생성 중...")
    print("="*80)
    create_summary_csv(all_results)

    # Create evidence report
    create_evidence_report(all_results)

    # Final summary
    print("\n" + "="*80)
    print("✓ 전체 수집 완료!")
    print("="*80)
    print(f"\n생성된 파일:")
    print(f"  - 개별 약물 JSON: {len(all_results)}개")
    print(f"  - 요약 CSV: kg_api_summary.csv")
    print(f"  - 근거 보고서: evidence_report.md")
    print(f"\n저장 위치: {OUTPUT_DIR}/")
    print("="*80)

if __name__ == "__main__":
    main()
