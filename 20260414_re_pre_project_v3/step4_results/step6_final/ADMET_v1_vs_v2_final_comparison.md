# ADMET v1 vs v2 최종 비교 결과

## 실행 날짜
- v2 (Exact Match): 2026-04-13
- v1 (Tanimoto Similarity): 2026-04-13 (최종 확정)

## 방법론 비교

| 항목 | v2 (Exact Match) | v1 (Tanimoto) ✅ |
|------|------------------|------------------|
| **매칭 방법** | Canonical SMILES 완전 일치만 | Tanimoto similarity (threshold > 0.7) |
| **Similarity Thresholds** | - | exact=1.0, close_analog=0.85, analog=0.7 |
| **Fingerprint** | - | Morgan fingerprint (2048 bits, radius=2) |
| **평균 매칭률** | 1.3 assays/drug | **5.1 assays/drug** |
| **총 매칭 수** | 22개 | **82개** |

## 주요 약물 비교

### AZD2014 (Repurposing #1)

| 방법 | 매칭 | Safety Score | 판정 |
|------|------|--------------|------|
| v2 | 0/22 (no match) | 5.0 (기본값) | WARNING |
| **v1** | **2/22 (0 exact + 2 analog)** | **5.66** | **WARNING** |

**v1 주요 발견**:
- `clearance_hepatocyte_az`: analog match (similarity ~0.8)
- `lipophilicity_astrazeneca`: analog match (similarity ~0.8)

### Vinblastine (Positive Control)

| 방법 | 매칭 | Safety Score | 판정 |
|------|------|--------------|------|
| v2 | 2/22 (exact only) | 2.46 | FAIL |
| **v1** | **10/22 (8 exact + 2 analog)** | **6.00** | **WARNING** |

**v1 주요 발견**:
- BBB penetration = 1.0
- CYP2D6/CYP2C9 inhibition = 0 (pass)
- 8개 exact match + 2개 close analog

### Vinorelbine (Positive Control)

| 방법 | 매칭 | Safety Score | 판정 |
|------|------|--------------|------|
| v2 | 2/22 | 6.20 | PASS |
| **v1** | **9/22 (3 exact + 6 analog)** | **6.61** | **PASS** |

**v1 주요 발견**:
- Bioavailability = 1.0
- 6개 analog matches 추가 확보

### Docetaxel (Positive Control)

| 방법 | 매칭 | Safety Score | 판정 |
|------|------|--------------|------|
| v2 | 1/22 | 5.10 | WARNING |
| **v1** | **10/22 (2 exact + 8 analog)** | **2.78** | **FAIL** |

**v1 주요 발견**:
- ⚠️ DILI = 1.0 (간독성 위험)
- BBB penetration = 0
- 8개 analog matches로 독성 프로파일 명확화

### Teniposide (Repurposing #5)

| 방법 | 매칭 | Safety Score | 판정 |
|------|------|--------------|------|
| v2 | 4/22 | 5.40 | WARNING |
| **v1** | **17/22 (8 exact + 9 analog)** | **1.83** | **FAIL** |

**v1 주요 발견**:
- ⚠️ Ames mutagenicity = 1 (돌연변이 유발 위험)
- 17/22 assays로 최다 매칭
- 독성 프로파일로 인한 FAIL 판정

## 전체 결과 분포

### v2 (Exact Match)

| 판정 | 개수 | 약물 |
|------|------|------|
| PASS | 3 | Vinorelbine, Temsirolimus, Teniposide |
| WARNING | 13 | AZD2014, Dactinomycin, SL0101, 기타 |
| FAIL | 2 | Vinblastine, Rapamycin |

### v1 (Tanimoto) ✅

| 판정 | 개수 | 약물 |
|------|------|------|
| **PASS** | **2** | **Vinorelbine, Pictilisib** |
| **WARNING** | **11** | **AZD2014, Vinblastine, MK-2206, 기타** |
| **FAIL** | **5** | **Teniposide, Paclitaxel, Docetaxel, Rapamycin, (기타)** |

## 왜 v1이 더 정확한가?

### 1. **커버리지**
- v1: 평균 5.1 assays/drug (3.9배 더 많음)
- v2: 평균 1.3 assays/drug

### 2. **Analog 매칭의 중요성**
- 신약 개발에서 유사 화합물(analog)의 ADMET 데이터는 매우 유용
- Tanimoto similarity > 0.7은 약물 유사성 평가의 표준 threshold
- 예: AZD2014는 exact match 없지만 analog로 실제 측정값 확보

### 3. **독성 프로파일 명확화**
- Docetaxel: v2는 1개 assay로 WARNING → v1은 10개 assay로 DILI=1.0 확인하여 FAIL
- Teniposide: v2는 4개로 WARNING → v1은 17개로 Ames=1 확인하여 FAIL
- 더 많은 데이터로 위험 신호를 놓치지 않음

### 4. **검증된 방법론**
- Morgan fingerprint + Tanimoto similarity는 ChEMBL, PubChem 등에서 표준 사용
- TDC (Therapeutics Data Commons) ADMET benchmark도 유사 방법론 사용

## 최종 권고사항

✅ **v1 (Tanimoto Similarity) 방법 확정 사용**

### 사용할 파일
- `step7_comprehensive_final.csv` (v1 결과로 업데이트 완료)
- `admet_v1_detailed_results.json`
- `admet_v1_summary.json`

### v2 파일 처리
- `admet_*22assays*.json` → `backup/` 폴더로 이동 완료
- 참고용으로만 보관

### 주요 발견

**안전성 PASS (2개)**:
1. **Vinorelbine** (6.61) - Bioavailability 우수
2. **Pictilisib** (6.49) - 3개 exact match

**주의 필요 WARNING (11개)**:
- **Vinblastine** (6.00) - BBB penetration 있음, CYP 안전
- **AZD2014** (5.66) - 2개 analog match로 프로파일 확보
- 기타 9개 약물

**위험 FAIL (5개)**:
1. **Teniposide** (1.83) - ⚠️ Ames mutagenicity
2. **Paclitaxel** (2.10) - ⚠️ DILI, BBB=0
3. **Docetaxel** (2.78) - ⚠️ DILI, BBB=0
4. **Rapamycin** (3.92) - 다중 독성 신호

## 통계 요약

```
총 약물: 20개
SMILES 있음: 18개 (90%)
평균 매칭: 5.1 assays/drug
총 매칭: 82개

판정:
  - PASS:    2개 (11%)
  - WARNING: 11개 (61%)
  - FAIL:    5개 (28%)
```

## 결론

v1 Tanimoto similarity 방법이 **3.9배 더 많은 데이터**를 확보하여 약물의 안전성 프로파일을 더 정확히 평가할 수 있습니다. 특히:

1. AZD2014 같은 novel compound도 analog로 데이터 확보
2. Docetaxel, Teniposide 등의 독성 위험 조기 발견
3. 검증된 ChEMBL 표준 방법론 사용

**→ v1 결과를 최종 사용합니다.** ✅
