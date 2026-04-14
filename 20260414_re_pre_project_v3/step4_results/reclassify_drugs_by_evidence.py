#!/usr/bin/env python3
"""
카테고리 재분류 - 실제 유방암 연구 근거 기반
ClinicalTrials.gov + PubMed 검색
"""
import json
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
import csv

OUTPUT_DIR = Path(__file__).parent / "drug_reclassification"
OUTPUT_DIR.mkdir(exist_ok=True)

# All 15 drugs
ALL_DRUGS = [
    # Category 1: Current use
    "Entinostat", "Cediranib", "Vinblastine", "ML323",
    # Category 2: Under research
    "YK-4-279", "AZ6102", "SB590885", "BMS-345541", "PFI3", "AT13148",
    # Category 3: Not applied
    "AZD2014", "Bicalutamide", "Nutlin-3a", "GSK2801", "AZD1332"
]

def search_clinicaltrials(drug_name):
    """Search ClinicalTrials.gov for breast cancer trials"""
    try:
        # ClinicalTrials.gov API v2
        base_url = "https://clinicaltrials.gov/api/v2/studies"
        query = f"{drug_name} AND breast cancer"

        params = {
            'query.term': query,
            'format': 'json',
            'pageSize': 100
        }

        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        print(f"  Searching ClinicalTrials: {drug_name}")

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')

        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            total = data.get('totalCount', 0)
            studies = data.get('studies', [])

            print(f"    Found: {total} trials")
            return {'count': total, 'studies': studies[:5]}  # Top 5

    except Exception as e:
        print(f"    Error: {e}")
        return {'count': 0, 'studies': [], 'error': str(e)}

def search_pubmed(drug_name):
    """Search PubMed for breast cancer articles"""
    try:
        # PubMed E-utilities API
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        query = f'"{drug_name}" AND "breast cancer"'

        params = {
            'db': 'pubmed',
            'term': query,
            'retmax': 100,
            'retmode': 'json'
        }

        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        print(f"  Searching PubMed: {drug_name}")

        req = urllib.request.Request(url)

        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            result = data.get('esearchresult', {})
            count = int(result.get('count', 0))
            ids = result.get('idlist', [])

            print(f"    Found: {count} articles")
            return {'count': count, 'pmids': ids[:10]}  # Top 10

    except Exception as e:
        print(f"    Error: {e}")
        return {'count': 0, 'pmids': [], 'error': str(e)}

def classify_drug(drug_name, trials_count, pubmed_count):
    """Classify drug based on evidence"""
    # Category 1: FDA approved for breast cancer (manually set)
    fda_approved_brca = ["Vinblastine"]  # Known approved

    if drug_name in fda_approved_brca:
        return "Category 1: 유방암 치료제 (FDA 승인)"

    # Category 2: Any breast cancer research
    if trials_count > 0 or pubmed_count > 0:
        return "Category 2: 유방암 연구 중"

    # Category 3: No breast cancer research
    return "Category 3: 유방암 미적용"

def main():
    print("="*80)
    print("카테고리 재분류 - 실제 유방암 연구 근거 기반")
    print("="*80)
    print(f"\n총 {len(ALL_DRUGS)}개 약물 검색 시작...")

    results = []

    for idx, drug in enumerate(ALL_DRUGS, 1):
        print(f"\n{'='*80}")
        print(f"{idx}/{len(ALL_DRUGS)}: {drug}")
        print(f"{'='*80}")

        # Search ClinicalTrials
        ct_result = search_clinicaltrials(drug)
        time.sleep(1)  # Rate limiting

        # Search PubMed
        pm_result = search_pubmed(drug)
        time.sleep(1)  # Rate limiting

        # Classify
        category = classify_drug(drug, ct_result['count'], pm_result['count'])

        result = {
            '약물명': drug,
            '유방암_임상시험_수': ct_result['count'],
            '유방암_논문_수': pm_result['count'],
            '재분류_카테고리': category,
            'clinicaltrials_data': ct_result,
            'pubmed_data': pm_result,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        results.append(result)

        # Save individual result
        drug_json = OUTPUT_DIR / f"{drug.replace(' ', '_').replace('(', '').replace(')', '')}_evidence.json"
        with open(drug_json, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n  분류: {category}")
        print(f"  저장: {drug_json}")

    # Save summary CSV
    csv_path = OUTPUT_DIR / "reclassification_summary.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=[
            '약물명', '유방암_임상시험_수', '유방암_논문_수', '재분류_카테고리'
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                '약물명': r['약물명'],
                '유방암_임상시험_수': r['유방암_임상시험_수'],
                '유방암_논문_수': r['유방암_논문_수'],
                '재분류_카테고리': r['재분류_카테고리']
            })

    print(f"\n{'='*80}")
    print("✓ 재분류 완료!")
    print(f"{'='*80}")
    print(f"\n저장된 파일:")
    print(f"  - 개별 약물 JSON: {len(results)}개")
    print(f"  - 요약 CSV: {csv_path}")

    # Print summary table
    print(f"\n{'='*80}")
    print("재분류 결과 요약")
    print(f"{'='*80}\n")
    print(f"{'약물명':<20} {'임상시험':<10} {'논문':<8} {'카테고리'}")
    print("-"*80)

    for r in results:
        print(f"{r['약물명']:<20} {r['유방암_임상시험_수']:<10} {r['유방암_논문_수']:<8} {r['재분류_카테고리']}")

    # Count by category
    cat1 = sum(1 for r in results if 'Category 1' in r['재분류_카테고리'])
    cat2 = sum(1 for r in results if 'Category 2' in r['재분류_카테고리'])
    cat3 = sum(1 for r in results if 'Category 3' in r['재분류_카테고리'])

    print(f"\n{'='*80}")
    print(f"Category 1 (FDA 승인): {cat1}개")
    print(f"Category 2 (연구 중): {cat2}개")
    print(f"Category 3 (미적용): {cat3}개")
    print(f"{'='*80}")

    return results

if __name__ == "__main__":
    results = main()
