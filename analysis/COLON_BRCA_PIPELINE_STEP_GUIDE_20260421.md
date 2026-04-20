# Colon vs BRCA 파이프라인 단계별 운영/배포 가이드

작성일: 2026-04-21  
대상 저장소: `colon_drug_repurposing`

## 1. 문서 목적
이 문서는 다음 2가지를 한 번에 정리합니다.

1. Colon 파이프라인과 BRCA 파이프라인의 실행 단계를 동일한 형식으로 문서화
2. 문서/코드 변경사항을 Git에 올리는 절차를 단계별로 정리

## 2. 파이프라인 범위

### 2.1 Colon 파이프라인 (현재 운영 기준)
- 오케스트레이션: `nextflow/main.nf`
- 주요 스크립트:
  - `nextflow/scripts/split_cohort_raw_inputs.py`
  - `nextflow/scripts/prepare_fe_inputs.py`
  - `nextflow/scripts/build_features.py`
  - `nextflow/scripts/build_pair_features_newfe_v2.py`
- 대표 실행 산출 예시:
  - `runs/20260420_crc_split_v2/*`

### 2.2 BRCA 파이프라인 (v3 기준)
- 기준 문서: `20260414_re_pre_project_v3/protocol_guide_v3.1_20260414.md`
- 대표 실행 스크립트:
  - `20260414_re_pre_project_v3/step4_results/run_step6_7_final.py`
- 대표 결과:
  - `20260414_re_pre_project_v3/step4_results/step6_metabric_results/*`
  - `20260414_re_pre_project_v3/step4_results/step6_final/*`

## 3. Colon 파이프라인 단계별

### Step 0. 코호트 분할
- 목적: raw 입력을 `colon/rectal` 등 코호트 단위로 분리
- 스크립트: `split_cohort_raw_inputs.py`
- 핵심 산출물:
  - `raw_inputs/label.parquet`
  - `raw_inputs/sample.parquet`
  - `raw_inputs/drug.parquet`
  - `raw_inputs/lincs_drug_signature.parquet`
  - `raw_inputs/drug_target.parquet`

### Step 1. FE 입력 준비 (Bridge)
- 목적: labels/sample/drug를 FE 계약 형식으로 정규화
- 스크립트: `prepare_fe_inputs.py`
- 핵심 산출물:
  - `fe_inputs/labels.parquet`
  - `fe_inputs/sample_features.parquet`
  - `fe_inputs/drug_features.parquet`
  - `fe_inputs/join_qc_report.json`

#### SMILES 자동 백필(현재 반영 상태)
- 반영 파일: `nextflow/scripts/prepare_fe_inputs.py`
- 정책:
  1. `DRUG_ID`(또는 canonical drug id) exact 매칭 우선
  2. 실패 시 `drug_name_norm` fallback
  3. 그룹 집계 시 null이 아닌 첫 값 우선
- QC 추가 필드:
  - `smiles_matched_by_drug_id`
  - `smiles_backfilled_by_name`
  - `smiles_unresolved_after_backfill`
  - `smiles_backfill_policy`

### Step 2. 기본 피처 생성
- 목적: sample+drug+label 통합, 결측/분산/정규화 처리
- 스크립트: `build_features.py`
- 산출물:
  - `features/features.parquet`
  - `features/labels.parquet`
  - `features/manifest.json`

### Step 3. Pair 피처 생성
- 목적: pair 단위 고급 피처 생성
- 스크립트: `build_pair_features_newfe_v2.py`
- 피처 그룹:
  - drug chemistry
  - LINCS similarity
  - target interaction
- 산출물:
  - `pair_features/pair_features_newfe_v2.parquet`
  - `pair_features/feature_manifest.json`

### Step 4. 모델 학습/앙상블
- 모델 결과 경로:
  - `models/ml_results/*.json`
  - `models/dl_results/*.json`
  - `models/graph_results/*.json`
  - `models/ensemble_results/*.json`
- 핵심 산출:
  - Ensemble Top30
  - Top15 후보

### Step 5. Step6 (METABRIC 검증)
- 결과 파일: `models/metabric_results/step6_metabric_results.json`
- 대표 지표:
  - `n_targets_expressed / n_total`
  - `P@15`, `P@20`
  - validated Top15

### Step 6. Step7 (ADMET Gate)
- 결과 파일: `models/admet_results/step7_admet_results.json`
- 대표 지표:
  - `n_assays`
  - `n_drugs_input / n_drugs_output`
  - 최종 카테고리(Approved/Candidate/Caution)

## 4. BRCA(v3) 파이프라인 단계별

### Step 1. FE 및 모델 생성
- 기준 문서 절차에 따라 BRCA용 FE/모델 학습 수행
- 참조: `20260414_re_pre_project_v3/protocol_guide_v3.1_20260414.md`

### Step 2. Top30 기반 Step6 실행
- 결과:
  - `step6_metabric_results/step6_summary.json`
  - method A/B/C 산출

### Step 3. Step7 ADMET 통합 실행
- 통합 스크립트:
  - `step4_results/run_step6_7_final.py`
- 결과:
  - `step6_final/step7_comprehensive_summary.json`
  - `step6_final/repurposing_summary.json`

## 5. Colon vs BRCA 차이 체크포인트

1. 오케스트레이션
- Colon: Nextflow DSL2 파이프라인 중심
- BRCA: v3 절차 문서 + Step6/7 통합 스크립트 중심

2. 코호트 처리
- Colon: 코호트 분할(`colon`, `rectal`) 운영
- BRCA: 단일 BRCA 코호트 중심

3. SMILES 전략
- Colon: FE 단계에서 자동 백필 로직 내장
- BRCA: 매칭 품질 검증(3-2.5) + 후속 Step7 요약 중심

4. 산출 구조
- Colon: run 디렉토리별 manifest/QC 추적이 강함
- BRCA: Step6/7 리포트 산출이 상세함

## 6. Git 업로드 단계 (문서/코드 공통)

### Step 1. 변경 확인
```powershell
git status
```

### Step 2. 파일 스테이징
문서만 올릴 때:
```powershell
git add analysis/COLON_BRCA_PIPELINE_STEP_GUIDE_20260421.md
```

문서 + 파이프라인 파일 같이 올릴 때:
```powershell
git add analysis/COLON_BRCA_PIPELINE_STEP_GUIDE_20260421.md
git add nextflow/scripts/prepare_fe_inputs.py
git add nextflow/main.nf
```

### Step 3. 커밋
```powershell
git commit -m "docs: add step-by-step colon vs BRCA pipeline guide"
```

### Step 4. 푸시
```powershell
git push origin main
```

### Step 5. 권한 오류(403) 시 조치
1. 현재 계정이 repo write 권한 있는지 확인
2. 잘못 저장된 GitHub credential 삭제 후 재인증
3. 다시 `git push origin main` 실행

## 7. 운영 체크리스트

- [ ] Colon 실행 후 `join_qc_report.json`에서 sample/drug 조인율 확인
- [ ] `drug_qc`에서 SMILES 백필/미해결 건수 확인
- [ ] Step6 결과에서 `P@15`, `P@20`, target expressed 확인
- [ ] Step7 결과에서 최종 카테고리 분포 확인
- [ ] BRCA 비교 시 method A/B/C 기준으로 동일 지표 매핑 확인
- [ ] Git push 전에 `git status`로 불필요 파일 포함 여부 확인

