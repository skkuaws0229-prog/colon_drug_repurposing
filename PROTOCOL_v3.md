# Drug Discovery Pipeline 팀원 재현 프로토콜
## biso_myprotocol · say2-4team · v3.1
**작성일:** 2026-04-08 | **최종 수정:** 2026-04-14 | **작성자:** say2-4team | **버전:** v3.1

> **v3.1 주요 변경사항 (20260414):**
> - **Step 3**: 매칭 품질 검증 (3-2.5) + Feature Selection (3.5) 추가
> - **Step 4**: 32개 모델 학습, Gap 진단 (과적합 분석), 모델별 상세 지표
> - **Step 5**: 앙상블 A (3개: Tree 2 + DL 1) / B (5개) 구분
> - **Step 6**: Multi-objective ranking (IC50 35% + Survival 25% + Tanimoto 20% + Target 10% + Clinical 10%)
> - **Step 6**: Validation → Top 15 Repurposing + 5 Positive Controls 분리
> - **Step 7**: ADMET v1 Tanimoto similarity (22 assays, analog matching)
> - **Step 7+**: KG/API 검증 신규 추가 (PubMed, ChEMBL, Clinical Trials)
> - **제거**: Step 8 멀티모달 허들 (v2 대비)
> - **교훈**: Mock 데이터 사용 금지, 실측 데이터만 사용

---

## 참고 자료

- **메인 대시보드:** [v1 vs v3 Comparison](dashboards/v1_vs_v3_comparison_dashboard.html)
- **서브 대시보드:**
  - [Step 4: Model Detail](dashboards/step4_model_detail_dashboard.html)
  - [Step 5: Ensemble](dashboards/step5_ensemble_dashboard.html)
  - [Step 6: METABRIC](dashboards/step6_metabric_dashboard.html)
  - [Step 7: ADMET](dashboards/step7_admet_dashboard.html)
- **GitHub 저장소:** https://github.com/skkuaws0215/20260408_pre_project_biso_myprotocol.git
- **ADMET 완료 보고서:** [STEP7_ADMET_COMPLETE.md](20260414_re_pre_project_v3/step4_results/STEP7_ADMET_COMPLETE.md)

---

## 이 문서의 목적

이 프로토콜은 biso_myprotocol의 Drug Discovery Pipeline v3.1을 팀원이 **자신의 저장소에서 동일한 방법론으로 재현**할 수 있도록 작성된 가이드입니다.

**시작점:** 본인이 보유한 전처리 완료 데이터 (curated_date/)
**목표:** 이 프로토콜을 따라 새 환경/저장소에서 동일한 방법론으로 실험을 재현하는 것

> 이 프로토콜은 재현 가이드입니다. 본인의 전처리 데이터와 저장소를 사용해서 각 단계를 직접 실행하세요.

---

## 전체 파이프라인 흐름 (v3.1)

```
전처리 완료 데이터 (curated_date/)
        ↓
Step 1. 환경 설정 (~1~2시간)
        ↓
Step 2. 전처리 데이터 준비 (~1~2시간)
        ↓
Step 3. FE 실행 - AWS Batch + Nextflow (~3~6시간)
        ↓
Step 3-2.5. 매칭 품질 검증 (~15분) ← v3 신규
        ↓
Step 3.5. Feature Selection (~30분) ← v3 신규
        ↓
Step 4. 모델 학습 32개 + Gap 진단 (~6~10시간, GPU 권장)
        ↓
Step 5. 앙상블 A (3개) / B (5개) (~2~3시간)
        ↓
Step 6. Multi-objective Ranking + Validation (~1시간)
        ↓
Step 7. ADMET v1 Tanimoto 22-assay (~1~2시간) ← v3 개선
        ↓
Step 7+. KG/API 검증 (~30~45분) ← v3 신규
        ↓
결과 저장 + 대시보드 업데이트
```

**전체 소요 시간 (예상):** 약 16~30시간 (GPU 환경 기준)

**v2 대비 변경사항:**
- ✅ Step 3-2.5, 3.5 추가 (+45분)
- ✅ Step 4 확장 (6개 → 32개 모델, +2~4시간)
- ✅ Step 7 개선 (Tanimoto analog, +1시간)
- ✅ Step 7+ 추가 (+30~45분)
- ❌ Step 8 제거 (멀티모달 허들, -2~3시간)
- **순증:** 약 +1~4시간

---

## 재현 결과에 대한 기대치

이 프로토콜을 따르더라도 biso_myprotocol 수치와 완전히 동일한 결과가 나오지 않을 수 있습니다. 이는 정상입니다.

| 항목 | 차이가 생기는 이유 | 허용 여부 |
|---|---|---|
| FE 컬럼 수 | 데이터 버전·범위·전처리 조건 차이 | 정상 범위 허용 |
| Feature Selection 결과 | RF Importance 랜덤성 | 5,000~6,000개 범위면 OK |
| 모델 Spearman·RMSE | FE 입력값 차이 + 랜덤 시드 | 방향성만 동일하면 OK |
| Gap 수치 | 모델별 과적합 정도 차이 | PASS/FAIL 기준 동일하면 OK |
| METABRIC 검증 지표 | FE 차이가 누적되어 반영 | 방향성만 동일하면 OK |
| 추천 약물 순위 | Multi-objective 점수 분포 차이 | Top 15 중 10개 이상 겹치면 OK |
| ADMET 매칭 수 | Tanimoto threshold 민감도 | 평균 4~6 assays/drug면 OK |

> **중요:** 숫자가 다소 달라도 **방법론**이 동일하면 재현 성공입니다. biso_myprotocol 기준 수치는 비교 참고값입니다.

---

## 절대 규칙 (반드시 준수)

```
1. curated_date/         → 읽기 전용, 수정·삭제 절대 금지
2. curated_date/glue/    → 접근 자체 금지 (다른 팀원 영역)
3. Proxy 데이터 사용 시  → 즉시 멈추고 팀장에게 확인 요청
4. ADMET Mock 데이터     → 절대 사용 금지 (v3 교훈)
5. .aws/credentials      → Git 커밋 절대 금지
6. AWS 리소스 생성 시    → 태그 필수: Key=pre-batch-2-4-team, Value=YYYYMMDD_본인이름
7. Gap > 0.15 모델       → 앙상블 제외 (과적합)
8. ADMET 실측 데이터     → TDC ADMET Group 22개 assay 사용
```

---

## 커스터마이징 사항

암종이나 데이터가 달라지는 경우 아래 항목을 수정하세요.

### 암종 변경 시 수정 항목
| 항목 | 유방암(기준) | 변경 방법 |
|---|---|---|
| GDSC 필터 | TCGA_DESC == "BRCA" | 해당 암종 코드로 변경 |
| LINCS 세포주 | MCF7 | 해당 암종 세포주로 변경 |
| METABRIC 외부 검증 데이터 | METABRIC BRCA | 해당 암종 외부 검증 데이터로 교체 |
| 결과 저장 경로 | YYYYMMDD_biso | YYYYMMDD_본인이름 |

### 모델 추가/제거 시 주의사항
- 동일한 FE 산출물(features.parquet·labels.parquet)로 학습
- 동일한 5-fold CV 기준으로 평가
- Graph 계열 모델은 반드시 drug-split 적용
- **Gap 기준:** Gap ≤ 0.15 (PASS), 0.15 < Gap ≤ 0.20 (WARNING), Gap > 0.20 (FAIL)
- **앙상블 기준:** Spearman ≥ 0.70 AND RMSE ≤ 1.40 AND Gap ≤ 0.15

### 데이터 버전 명시
- GDSC1+2 병합 또는 GDSC2만 사용 여부 명시
- LINCS 원본 추출 또는 기존 파일 사용 여부 명시
- 프로토콜과 다른 처리는 README·대시보드에 반드시 기재

---

## STEP 1. 환경 설정
**예상 소요 시간: 1~2시간**

### 1-1. GitHub 저장소 클론
```bash
# biso_myprotocol 참고 저장소
git clone https://github.com/skkuaws0215/20260408_pre_project_biso_myprotocol.git

# 본인 저장소 생성 후 클론
git clone https://github.com/[본인계정]/[본인저장소].git
cd [본인저장소]
```

### 1-2. Python 환경 설정
```bash
conda create -n drug4 python=3.10 -y
conda activate drug4

# 핵심 패키지
pip install pandas numpy scikit-learn lightgbm xgboost catboost \
    torch pyarrow boto3 awscli rdkit-pypi nextflow

# 추가 패키지 (v3)
pip install tdc  # TDC ADMET 데이터셋
pip install seaborn matplotlib plotly  # 시각화
pip install requests beautifulsoup4  # API 호출
```

### 1-3. Nextflow 설치
```bash
# Java 11+ 필요 (없으면 conda로 설치)
conda install -c conda-forge openjdk=11

# Nextflow 설치
curl -s https://get.nextflow.io | bash
chmod +x nextflow && sudo mv nextflow /usr/local/bin/
nextflow -version  # 정상 확인
```

### 1-4. AWS 설정
```bash
# 자격증명 설정
aws configure  # Account: 666803869796 확인

# 접근 확인
aws sts get-caller-identity
aws s3 ls s3://say2-4team/curated_date/

# 절대 접근 금지
# aws s3 ls s3://say2-4team/curated_date/glue/
```

### 1-5. AWS Batch 환경 세팅

**태그 설정 (모든 AWS 리소스에 필수 적용):**
```bash
TAG_KEY="pre-batch-2-4-team"
TAG_VAL="YYYYMMDD_본인이름"  # 예: 20260414_biso
```

**ECR 이미지 빌드 & 푸시:**
```bash
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
ECR_URI=${AWS_ACCOUNT}.dkr.ecr.ap-northeast-2.amazonaws.com/drug4-fe

aws ecr create-repository --repository-name drug4-fe \
  --region ap-northeast-2 \
  --tags Key=${TAG_KEY},Value=${TAG_VAL}

docker build -t drug4-fe --platform linux/amd64 .
docker tag drug4-fe:latest ${ECR_URI}:latest
docker push ${ECR_URI}:latest
```

**Compute Environment / Job Queue 확인:**
- 기존 팀 리소스(team4-fe-ce-cpu·team4-fe-queue-cpu) 재사용 가능한지 먼저 확인
- 없는 것만 새로 생성 (태그 반드시 적용)

### QC 체크
```
[ ] conda drug4 환경 생성 완료
[ ] Nextflow 정상 동작 확인
[ ] AWS Account 666803869796 확인
[ ] ECR 이미지 빌드·푸시 완료 (linux/amd64)
[ ] AWS Batch Compute Env·Job Queue 확인
[ ] GitHub 저장소 클론 완료
[ ] TDC 패키지 설치 확인
```

---

## STEP 2. 전처리 데이터 준비
**예상 소요 시간: 1~2시간 (LINCS 복사 포함)**

### 2-1. curated_date/ 파일 목록 확인 (읽기만)
```bash
# 전체 목록 확인
aws s3 ls s3://say2-4team/curated_date/ --human-readable

# 필수 6종 확인
REQUIRED=(
  "gdsc/gdsc2_basic_clean_*.parquet"
  "lincs/lincs_sig_info_*.parquet"
  "metabric/metabric_expression_*.parquet"
  "metabric/metabric_clinical_*.parquet"
  "drugbank/drug_master_*.parquet"
  "id_mapping*.parquet"
)
```

### 2-2. 업무폴더로 복사 (glue/ 제외 필수)
```bash
# curated_date/ → 업무폴더 복사 (원본 건드리지 않음)
aws s3 cp s3://say2-4team/curated_date/ \
  s3://say2-4team/[본인업무폴더]/data/ \
  --recursive \
  --exclude "glue/*"   # glue/ 절대 복사하지 말 것
```

### 2-3. LINCS MCF7 처리
biso_myprotocol에서는 두 가지 방식 중 선택:
- **방법 A:** oringinal_raw/lincs/ Level 5 GCTx(21GB)에서 직접 MCF7 추출
- **방법 B:** 팀 공유 lincs_mcf7.parquet 사용 (팀장 확인 후)

```bash
# 방법 A: 직접 추출 (권장)
# cmapPy 또는 h5py로 GCTx 파일에서 MCF7 시그니처 추출
python scripts/extract_lincs_mcf7.py \
  --input s3://say2-4team/oringinal_raw/lincs/GSE92742_*.gctx.gz \
  --cell_id MCF7 \
  --output s3://say2-4team/[본인업무폴더]/data/lincs_mcf7.parquet
```

### 2-4. GDSC 처리 결정
| 선택 | 설명 | 장단점 |
|---|---|---|
| GDSC2만 사용 | 품질 우수, 약물 295개 | 품질↑, 커버리지↓ |
| GDSC1+2 병합 | 약물 621개 | 커버리지↑, 품질↓ |

> biso_myprotocol은 GDSC2만 사용 (품질 우선 결정). 선택 이유를 README에 명시할 것.

### 2-5. config/data_paths.yaml 설정
```yaml
# 본인 업무폴더 경로로 수정
gdsc_ic50:     s3://say2-4team/[본인업무폴더]/data/gdsc/...
lincs:         s3://say2-4team/[본인업무폴더]/data/lincs_mcf7.parquet
metabric_expr: s3://say2-4team/[본인업무폴더]/data/metabric/...
metabric_clin: s3://say2-4team/[본인업무폴더]/data/metabric/...
output_dir:    s3://say2-4team/[본인업무폴더]/fe_output/
```

### QC 체크
```
[ ] curated_date/ 필수 데이터 확인 (glue/ 미접근)
[ ] 업무폴더로 복사 완료 (glue/ 제외 확인)
[ ] LINCS MCF7 처리 방식 결정 및 명시
[ ] GDSC 버전 선택 및 README 명시
[ ] config/data_paths.yaml 본인 경로로 수정
[ ] 팀4 원본 데이터(tmp_data) 복사 금지 확인
```

---

## STEP 3. FE 실행 (newfe_v8) — AWS Batch + Nextflow
**예상 소요 시간: 3~6시간 (LINCS 7.6GB 처리가 병목)**

### 3-1. 핵심 원칙 (반드시 준수)
```
✅ fit (imputation median, variance threshold) → TCGA 기준으로만 계산
✅ METABRIC → TCGA fit 기준값으로 transform만 적용 (fit 절대 금지)
✅ leakage 컬럼 제거 (샘플ID, 날짜, 결과 직접 포함)
✅ high-missing(>30%) 제거 · median imputation · variance filtering
✅ TCGA/METABRIC 컬럼 구조 반드시 일치
```

### 3-2. Drug Features 매칭
biso_myprotocol은 glue/ 접근 불가로 복합 매칭 사용:
```
1순위: ChEMBL (canonical_smiles 품질 우수)
2순위: DrugBank (미매칭 보완)
3순위: GDSC annotation fuzzy matching
4순위: PubChem API (외부 조회)
미매칭: SMILES=NA (all-zero fingerprint 처리)
```
매칭률 및 미매칭 목록 반드시 README·대시보드에 명시.

### 3-3. Nextflow config 설정
```bash
# nextflow.config 핵심 설정
process.executor = 'awsbatch'
process.queue    = 'team4-fe-queue-cpu'  # 또는 본인 Job Queue
aws.region       = 'ap-northeast-2'
workDir          = 's3://say2-4team/[본인업무폴더]/nextflow_work/'

# 태그 설정
aws.batch.jobDefinitionTags = ['pre-batch-2-4-team': 'YYYYMMDD_본인이름']
```

### 3-4. FE 실행
```bash
# dry-run (설정 확인)
nextflow run main.nf -profile awsbatch --dry-run

# 실행
nextflow run main.nf -profile awsbatch

# 진행상황 모니터링
aws batch describe-jobs --jobs [job-id]

# 로그 확인 (CloudWatch)
aws logs tail /aws/batch/job --follow
```

**FE 산출물 확인:**
```bash
# S3에 생성된 파일 확인
aws s3 ls s3://say2-4team/[본인업무폴더]/fe_output/

# 필수 파일 (v3 기준)
features.parquet       # TCGA 학습용 (예: 20,421 features)
features_metabric.parquet  # METABRIC 외부 검증용
labels.parquet         # IC50 값
drug_features.parquet  # SMILES, Fingerprint 등
```

### QC 체크
```
[ ] Nextflow 정상 완료 (exit code 0)
[ ] features.parquet 생성 확인 (컬럼 수 15,000~25,000)
[ ] features_metabric.parquet 생성 확인
[ ] labels.parquet 생성 확인
[ ] TCGA/METABRIC 컬럼 일치 확인
[ ] all-zero FP 약물 목록 확인 (NA SMILES)
```

---

## STEP 3-2.5. 매칭 품질 검증 (**v3 신규**)
**예상 소요 시간: ~15분**

### 3-2.5-1. SMILES 매칭률 확인
```python
# scripts/check_smiles_matching.py
import pandas as pd

drug_features = pd.read_parquet('s3://[...]/drug_features.parquet')
total = len(drug_features)
matched = (drug_features['smiles'].notna()).sum()
matching_rate = matched / total * 100

print(f"✓ SMILES 매칭률: {matching_rate:.1f}% ({matched}/{total})")
print(f"✗ 미매칭 약물: {total - matched}개")

# 미매칭 약물 리스트 저장
unmatched = drug_features[drug_features['smiles'].isna()]['drug_name']
unmatched.to_csv('unmatched_drugs.csv', index=False)
```

**기준:**
- 매칭률 ≥ 75%: PASS
- 60% ≤ 매칭률 < 75%: WARNING (미매칭 이유 명시)
- 매칭률 < 60%: FAIL (데이터 소스 재검토)

### 3-2.5-2. All-zero Fingerprint 제거
```python
# all-zero FP 약물 제거
features = pd.read_parquet('features.parquet')
fp_cols = [c for c in features.columns if c.startswith('fp_')]
zero_mask = (features[fp_cols] == 0).all(axis=1)

print(f"✗ All-zero FP 약물: {zero_mask.sum()}개")
features_clean = features[~zero_mask]
features_clean.to_parquet('features_clean.parquet')
```

### QC 체크
```
[ ] SMILES 매칭률 75% 이상
[ ] 미매칭 약물 목록 저장 (README 명시)
[ ] All-zero FP 약물 제거 완료
[ ] features_clean.parquet 생성 확인
```

---

## STEP 3.5. Feature Selection (**v3 신규**)
**예상 소요 시간: ~30분**

### 3.5-1. Random Forest Importance 기반 선택
```python
# scripts/feature_selection_rf.py
from sklearn.ensemble import RandomForestRegressor
import pandas as pd
import numpy as np

# 데이터 로드
features = pd.read_parquet('features_clean.parquet')
labels = pd.read_parquet('labels.parquet')

# Random Forest로 Importance 계산
rf = RandomForestRegressor(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)
rf.fit(features, labels)

# Importance 기반 상위 선택
importances = pd.Series(rf.feature_importances_, index=features.columns)
importances_sorted = importances.sort_values(ascending=False)

# 상위 5,000~6,000개 선택 (누적 중요도 기준)
cumsum = importances_sorted.cumsum()
n_features = (cumsum < 0.95).sum()  # 95% 누적 중요도
n_features = min(n_features, 6000)  # 최대 6,000개

selected_features = importances_sorted.head(n_features).index.tolist()
print(f"✓ 선택된 Feature: {len(selected_features)}개 (원본: {len(features.columns)}개)")

# 저장
features_selected = features[selected_features]
features_selected.to_parquet('features_selected.parquet')

# Importance 저장 (분석용)
importances_sorted.to_csv('feature_importances.csv')
```

**v3 기준:**
- 원본: 20,421개 → 선택: 5,531개 (72.9% 감축)
- 기준: 누적 중요도 95% 또는 최대 6,000개

### QC 체크
```
[ ] Feature Selection 완료 (5,000~6,000개)
[ ] features_selected.parquet 생성
[ ] feature_importances.csv 저장
[ ] README에 원본/선택 Feature 수 명시
```

---

## STEP 4. 모델 학습 (32개) + Gap 진단 (**v3 확장**)
**예상 소요 시간: 6~10시간 (GPU 권장)**

### 4-1. 모델 목록 (v3 기준: 32개)

**Tree-based (12개):**
1. CatBoost
2. LightGBM
3. XGBoost
4. ExtraTrees
5. RandomForest
6. GradientBoosting
7. HistGradientBoosting
8. AdaBoost
9. BaggingRegressor
10. DART (CatBoost)
11. GOSS (LightGBM)
12. RF-L1 (LightGBM)

**Deep Learning (10개):**
13. FlatMLP
14. DeepMLP
15. ResNet1D
16. TabNet
17. FT-Transformer
18. SAINT
19. AutoInt
20. DCN-v2
21. Wide&Deep
22. DeepFM

**Graph Neural Networks (6개):**
23. GCN
24. GAT
25. GraphSAGE
26. GIN
27. MPNN
28. AttentiveFP

**Hybrid (4개):**
29. LightGBM + MLP Ensemble
30. CatBoost + Attention
31. XGBoost + Graph
32. TabTransformer

### 4-2. 학습 설정

**공통 설정:**
```python
# 5-fold CV
n_splits = 5
random_state = 42

# Train/Holdout split
train_size = 0.8
holdout_size = 0.2

# GPU 설정 (DL 모델)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
```

**모델별 Hyperparameter (v3 최적화):**
```python
# CatBoost
catboost_params = {
    'iterations': 1000,
    'learning_rate': 0.05,
    'depth': 6,
    'l2_leaf_reg': 3,
    'random_seed': 42,
    'task_type': 'GPU'  # GPU 사용 시
}

# LightGBM
lgbm_params = {
    'n_estimators': 1000,
    'learning_rate': 0.05,
    'num_leaves': 31,
    'max_depth': -1,
    'reg_alpha': 0.1,
    'reg_lambda': 0.1,
    'random_state': 42,
    'device': 'gpu'  # GPU 사용 시
}

# FlatMLP
flatmlp_params = {
    'hidden_dims': [512, 256, 128],
    'dropout': 0.3,
    'batch_size': 256,
    'epochs': 100,
    'lr': 0.001,
    'optimizer': 'adam'
}
```

### 4-3. Gap 진단 (**v3 핵심**)

**Gap 계산:**
```python
# Gap = OOF Spearman - Train Spearman
gap = spearman_oof - spearman_train

# 판정 기준
if gap <= 0.15:
    verdict = "PASS"
elif gap <= 0.20:
    verdict = "WARNING"
else:
    verdict = "FAIL"
```

**Gap 해석 가이드:**
- **Gap ≤ 0.10**: 과적합 없음 (이상적)
- **0.10 < Gap ≤ 0.15**: 경미한 과적합 (허용)
- **0.15 < Gap ≤ 0.20**: 중간 과적합 (주의)
- **Gap > 0.20**: 심각한 과적합 (앙상블 제외)

**v3 결과 예시:**
| 모델 | Train Sp | OOF Sp | Gap | 판정 |
|------|----------|--------|-----|------|
| CatBoost | 0.902 | 0.828 | 0.074 | PASS ✅ |
| LightGBM | 0.905 | 0.815 | 0.090 | PASS ✅ |
| ExtraTrees | 0.941 | 0.790 | 0.151 | FAIL ❌ |
| FlatMLP | 0.847 | 0.792 | 0.055 | PASS ✅ |

### 4-4. 32개 측정 지표

**각 모델마다 계산:**
1. Train Spearman
2. Train RMSE
3. OOF Spearman (5-fold CV)
4. OOF RMSE
5. Holdout Spearman
6. Holdout RMSE
7. Gap (Train - OOF Spearman)
8. Train R²
9. OOF R²
10. Holdout R²
11. Train MAE
12. OOF MAE
13. Holdout MAE
14. ... (총 32개)

**결과 저장:**
```python
# 결과 테이블
results = pd.DataFrame({
    'model': model_names,
    'train_sp': train_sps,
    'oof_sp': oof_sps,
    'holdout_sp': holdout_sps,
    'gap': gaps,
    'verdict': verdicts,
    # ... 32개 지표
})

results.to_csv('step4_model_results.csv', index=False)
```

### QC 체크
```
[ ] 32개 모델 학습 완료
[ ] 각 모델별 32개 지표 계산 완료
[ ] Gap 진단 완료 (PASS/WARNING/FAIL)
[ ] step4_model_results.csv 저장
[ ] PASS 모델 10개 이상 확보
[ ] Gap > 0.15 모델 목록 확인
```

---

## STEP 5. 앙상블 A (3개) / B (5개) (**v3 개선**)
**예상 소요 시간: 2~3시간**

### 5-1. 앙상블 기준

**공통 기준:**
- Spearman ≥ 0.70
- RMSE ≤ 1.40
- **Gap ≤ 0.15** (v3 추가)

### 5-2. 앙상블 A (3개) - 최종 추천

**구성:**
1. **CatBoost** (Gap=0.074)
2. **LightGBM** (Gap=0.090)
3. **FlatMLP** (Gap=0.055)

**가중치 (OOF 성능 기반):**
```python
weights_A = {
    'CatBoost': 0.40,
    'LightGBM': 0.35,
    'FlatMLP': 0.25
}

# 앙상블 예측
pred_A = (
    weights_A['CatBoost'] * pred_catboost +
    weights_A['LightGBM'] * pred_lgbm +
    weights_A['FlatMLP'] * pred_flatmlp
)
```

**v3 성능:**
- OOF Spearman: 0.835
- Holdout Spearman: 0.828
- METABRIC Spearman: 0.681

### 5-3. 앙상블 B (5개) - 확장 검증

**구성:**
1. CatBoost
2. LightGBM
3. FlatMLP
4. XGBoost
5. DART

**가중치:**
```python
weights_B = {
    'CatBoost': 0.30,
    'LightGBM': 0.25,
    'FlatMLP': 0.20,
    'XGBoost': 0.15,
    'DART': 0.10
}
```

**v3 성능:**
- OOF Spearman: 0.842
- Holdout Spearman: 0.831
- METABRIC Spearman: 0.689

### 5-4. 앙상블 선택 기준

| 앙상블 | 모델 수 | 특징 | 권장 상황 |
|--------|---------|------|-----------|
| **A (3개)** | 3 | 간결, 안정적 | 최종 배포, 해석 중요 |
| **B (5개)** | 5 | 성능 우수 | 벤치마크, 논문 |

> **biso_myprotocol 권장:** 앙상블 A (3개) 사용

### QC 체크
```
[ ] 앙상블 A (3개) 구성 완료
[ ] 앙상블 B (5개) 구성 완료
[ ] 가중치 최적화 완료
[ ] OOF/Holdout 성능 평가 완료
[ ] METABRIC 성능 평가 완료
[ ] 최종 앙상블 선택 (A 또는 B)
```

---

## STEP 6. Multi-objective Ranking + Validation (**v3 확장**)
**예상 소요 시간: ~1시간**

### 6-1. Multi-objective Scoring

**가중치 (v3 최적화):**
```python
weights = {
    'ic50_rank': 0.35,      # IC50 예측 순위
    'survival': 0.25,       # METABRIC 생존 분석
    'tanimoto': 0.20,       # 약물 다양성
    'target': 0.10,         # Target 중복도
    'clinical': 0.10        # FDA 승인 여부
}

# 최종 점수 계산
final_score = (
    weights['ic50_rank'] * ic50_normalized +
    weights['survival'] * survival_normalized +
    weights['tanimoto'] * (1 - tanimoto_avg) +  # 낮을수록 좋음
    weights['target'] * (1 - target_overlap) +
    weights['clinical'] * clinical_score
)
```

**정규화 방법:**
- IC50 rank: 0~1 (순위 기반)
- Survival: Cox HR log p-value 정규화
- Tanimoto: 평균 유사도 (1에서 뺌)
- Target: 중복도 (1에서 뺌)
- Clinical: FDA 승인=1, 연구중=0.5, 미적용=0

### 6-2. Validation (72개) → Top 15 + Positive Control 5

**Validation 선정 (72개):**
```python
# METABRIC 외부 검증
validation_drugs = metabric_results[
    (metabric_results['p_value'] < 0.05) &
    (metabric_results['hr'] < 1.0)  # Hazard Ratio < 1 (유리)
].sort_values('final_score', ascending=False)

print(f"✓ Validation 약물: {len(validation_drugs)}개")
```

**Top 15 Repurposing:**
```python
# Validation 중 FDA 미승인 약물
repurposing = validation_drugs[
    validation_drugs['category'] != 'Category 1: 유방암 치료제 (FDA 승인)'
].head(15)

repurposing.to_csv('repurposing_top15.csv', index=False)
```

**Positive Control 5개:**
```python
# FDA 승인 유방암 치료제 중 상위 5개
positive_controls = validation_drugs[
    validation_drugs['category'] == 'Category 1: 유방암 치료제 (FDA 승인)'
].sort_values('final_score', ascending=False).head(5)

positive_controls.to_csv('positive_controls.csv', index=False)
```

**v3 결과 예시:**

Top 15 Repurposing:
1. AZD2014 (0.341) - MTOR inhibitor
2. Dactinomycin (0.329) - ESR1
3. SL0101 (0.294) - Kinase inhibitor
4. Temsirolimus (0.280) - MTOR
5. Teniposide (0.213) - DNA replication
...

Positive Controls (5개):
1. Vinblastine (0.496)
2. Docetaxel (0.408)
3. Paclitaxel (0.382)
4. Docetaxel (0.368) - 중복 제거 필요
5. Vinorelbine (0.343)

### 6-3. 카테고리 분류

**3-tier 분류:**
- **Category 1:** 유방암 치료제 (FDA 승인) - 5개
- **Category 2:** 유방암 연구 중 - 8개
- **Category 3:** 유방암 미적용 (신규 발굴) - 7개

### QC 체크
```
[ ] Multi-objective scoring 완료
[ ] Validation 72개 선정
[ ] Top 15 Repurposing 선정
[ ] Positive Control 5개 선정 (중복 제거)
[ ] 카테고리 분류 완료
[ ] repurposing_top15.csv 저장
[ ] positive_controls.csv 저장
```

---

## STEP 7. ADMET v1 Tanimoto 22-assay (**v3 개선**)
**예상 소요 시간: 1~2시간**

### 7-1. TDC ADMET 데이터셋 다운로드

**22개 assay 목록:**
```python
from tdc.benchmark_group import admet_group

ADMET_ASSAYS = [
    # Absorption (7개)
    'caco2_wang', 'bioavailability_ma', 'hia_hou', 'pgp_broccatelli',
    'solubility_aqsoldb', 'lipophilicity_astrazeneca', 'ppbr_az',

    # Distribution (2개)
    'bbb_martins', 'vdss_lombardo',

    # Metabolism (6개)
    'cyp2c9_substrate_carbonmangels', 'cyp2d6_substrate_carbonmangels',
    'cyp3a4_substrate_carbonmangels', 'cyp2c9_veith', 'cyp2d6_veith',
    'cyp3a4_veith',

    # Excretion (3개)
    'clearance_hepatocyte_az', 'clearance_microsome_az', 'half_life_obach',

    # Toxicity (4개)
    'ames', 'dili', 'herg', 'ld50_zhu'
]

# 다운로드
group = admet_group(path='data/admet/')
for assay in ADMET_ASSAYS:
    benchmark = group.get(assay)
    train, valid = benchmark['train'], benchmark['valid']
    train.to_parquet(f'data/admet/{assay}/train_val_basic_clean.parquet')
```

### 7-2. Tanimoto Similarity 매칭 (**v3 핵심**)

**방법론:**
```python
from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs

# Morgan Fingerprint 생성
def get_fingerprint(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol:
        return AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)
    return None

# Tanimoto Similarity 계산
def calculate_tanimoto(fp1, fp2):
    return DataStructs.TanimotoSimilarity(fp1, fp2)

# 매칭 기준
SIMILARITY_THRESHOLDS = {
    'exact': 1.0,
    'close_analog': 0.85,
    'analog': 0.70
}

# 각 약물에 대해 assay library에서 best match 찾기
for drug_smiles in drug_smiles_list:
    drug_fp = get_fingerprint(drug_smiles)

    best_similarity = 0
    best_y_value = None
    match_type = 'no_match'

    for assay_smiles, y_value in assay_library:
        assay_fp = get_fingerprint(assay_smiles)
        similarity = calculate_tanimoto(drug_fp, assay_fp)

        if similarity > best_similarity:
            best_similarity = similarity
            best_y_value = y_value

            # Match type 결정
            if similarity == 1.0:
                match_type = 'exact'
            elif similarity > 0.85:
                match_type = 'close_analog'
            elif similarity > 0.70:
                match_type = 'analog'

    # 결과 저장
    admet_results[drug_name][assay_name] = {
        'y_value': best_y_value,
        'similarity': best_similarity,
        'match_type': match_type
    }
```

**v3 결과 예시:**
- AZD2014: 2/22 assays (0 exact + 2 analog), safety=5.66
- Vinblastine: 10/22 assays (8 exact + 2 analog), safety=6.00
- Vinorelbine: 9/22 assays (3 exact + 6 analog), safety=6.61

### 7-3. Safety Score 계산

**가중치 시스템:**
```python
SAFETY_WEIGHTS = {
    'ames': -2.0,          # Mutagenicity (negative)
    'dili': -2.0,          # Liver toxicity (negative)
    'herg': -1.5,          # Cardiotoxicity (negative)
    'ld50_zhu': 1.0,       # Higher is safer
    'bioavailability_ma': 1.0,
    'bbb_martins': 0.5,
    'caco2_wang': 0.5
}

# Safety Score 계산
def calculate_safety_score(admet_results):
    base_score = 5.0
    weighted_sum = 0
    n_assays = 0

    for assay, result in admet_results.items():
        if result['match_type'] != 'no_match':
            weight = SAFETY_WEIGHTS.get(assay, 0.0)
            y_value = result['y_value']
            similarity = result['similarity']

            # Similarity 보정
            adjusted_weight = weight * similarity

            # Normalization
            if isinstance(y_value, (int, float)):
                if y_value > 1:
                    normalized = min(1.0, y_value / 10.0)
                else:
                    normalized = y_value

                weighted_sum += adjusted_weight * normalized
                n_assays += 1

    # Final score
    safety_score = base_score + weighted_sum + (n_assays * 0.15)
    return max(0, min(10, safety_score))
```

**판정 기준:**
- Safety ≥ 6.0: PASS
- 4.0 ≤ Safety < 6.0: WARNING
- Safety < 4.0: FAIL

### 7-4. v1 vs v2 교훈 (**중요**)

**v2 실패 (Mock 데이터):**
- Exact SMILES match만 사용
- 평균 1.3 assays/drug (커버리지 매우 낮음)
- AZD2014: 0 매칭 (실패)

**v1 성공 (실측 데이터):**
- Tanimoto similarity > 0.7 (analog 포함)
- 평균 5.1 assays/drug (3.9배 증가)
- AZD2014: 2 analog 매칭 (성공)

**v3 적용:**
- **반드시 v1 방법론 사용**
- Mock 데이터 절대 금지
- TDC ADMET Group 22개 assay 사용
- Tanimoto similarity threshold > 0.7

### QC 체크
```
[ ] TDC ADMET 22개 assay 다운로드 완료
[ ] Tanimoto similarity 계산 완료
[ ] 평균 매칭 4~6 assays/drug 확보
[ ] Safety score 계산 완료
[ ] PASS/WARNING/FAIL 판정 완료
[ ] v1 방법론 확인 (Mock 데이터 미사용)
[ ] admet_v1_detailed_results.json 저장
```

---

## STEP 7+. KG/API 검증 (**v3 신규**)
**예상 소요 시간: 30~45분**

### 7+-1. PubMed 문헌 검증

**API 호출:**
```python
import requests

def search_pubmed(drug_name, disease="breast cancer"):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        'db': 'pubmed',
        'term': f'({drug_name}) AND ({disease})',
        'retmax': 10,
        'retmode': 'json'
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    count = int(data['esearchresult']['count'])
    ids = data['esearchresult'].get('idlist', [])

    return {
        'drug_name': drug_name,
        'pubmed_count': count,
        'pmids': ids[:5],  # 상위 5개
        'has_evidence': count > 0
    }

# Top 15 약물에 대해 검증
for drug in repurposing_top15:
    result = search_pubmed(drug['drug_name'])
    drug['pubmed_evidence'] = result
```

### 7+-2. ChEMBL Target 검증

```python
from chembl_webresource_client.new_client import new_client

def get_chembl_targets(smiles):
    molecule = new_client.molecule
    target = new_client.target

    # SMILES로 화합물 검색
    mols = molecule.filter(molecule_structures__canonical_smiles__flexmatch=smiles)

    if not mols:
        return []

    chembl_id = mols[0]['molecule_chembl_id']

    # Target 검색
    activities = new_client.activity.filter(molecule_chembl_id=chembl_id)
    targets = [act['target_chembl_id'] for act in activities]

    return list(set(targets))
```

### 7+-3. Clinical Trials 검증

```python
def search_clinical_trials(drug_name, condition="breast cancer"):
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        'query.term': f'{drug_name} AND {condition}',
        'format': 'json',
        'pageSize': 100
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    studies = data.get('studies', [])

    return {
        'drug_name': drug_name,
        'trial_count': len(studies),
        'phases': [s['protocolSection']['designModule'].get('phases', [])
                   for s in studies],
        'has_trials': len(studies) > 0
    }
```

### 7+-4. 카테고리 재분류

**Evidence 기반 재분류:**
```python
def reclassify_category(drug_evidence):
    pubmed = drug_evidence['pubmed_count']
    trials = drug_evidence['trial_count']
    targets = len(drug_evidence['chembl_targets'])

    if pubmed > 10 or trials > 0:
        return "Category 2: 유방암 연구 중"
    elif targets > 0:
        return "Category 3: 유방암 미적용 (신규 발굴)"
    else:
        return "Category 3: 유방암 미적용 (신규 발굴)"
```

### QC 체크
```
[ ] PubMed 검증 완료 (Top 15)
[ ] ChEMBL Target 검증 완료
[ ] Clinical Trials 검증 완료
[ ] 카테고리 재분류 완료
[ ] kg_api_results.json 저장
[ ] 재분류 이유 명시 (README)
```

---

## 결과 저장 + 대시보드 업데이트

### 최종 산출물

**필수 파일:**
```
results/
├── step4_model_results.csv          # 32개 모델 상세
├── step5_ensemble_A_results.json    # 앙상블 A (3개)
├── step5_ensemble_B_results.json    # 앙상블 B (5개)
├── step6_validation_top.csv         # Validation 72개
├── step6_repurposing_top15.csv      # Top 15 Repurposing
├── step6_positive_controls.csv      # Positive Control 5개
├── step7_admet_v1_detailed.json     # ADMET v1 상세
├── step7_admet_v1_summary.json      # ADMET v1 요약
├── step7plus_kg_results.json        # KG/API 검증
└── step7_comprehensive_final.csv    # 전체 통합 결과
```

**대시보드 파일:**
```
dashboards/
├── v1_vs_v3_comparison_dashboard.html  # 메인
├── step4_model_detail_dashboard.html   # Step 4 상세
├── step5_ensemble_dashboard.html       # Step 5 상세
├── step6_metabric_dashboard.html       # Step 6 상세
└── step7_admet_dashboard.html          # Step 7 상세
```

### 대시보드 업데이트

**HTML 생성:**
```python
# scripts/generate_dashboards.py
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Step 4: 모델 비교
fig_gap = px.scatter(
    model_results,
    x='oof_sp',
    y='gap',
    color='verdict',
    hover_data=['model', 'train_sp'],
    title='Step 4: Gap Analysis (32 Models)'
)
fig_gap.write_html('dashboards/step4_model_detail_dashboard.html')

# Step 7: ADMET
fig_admet = px.bar(
    admet_summary,
    x='drug_name',
    y='safety_score',
    color='verdict',
    title='Step 7: ADMET Safety Scores (v1 Tanimoto)'
)
fig_admet.write_html('dashboards/step7_admet_dashboard.html')
```

---

## 재현 체크리스트 (전체)

### 환경
```
[ ] conda drug4 환경 생성
[ ] AWS 설정 완료 (Account 666803869796)
[ ] Nextflow 설치 확인
[ ] TDC 패키지 설치
```

### 데이터
```
[ ] curated_date/ 접근 확인 (glue/ 제외)
[ ] LINCS MCF7 처리 완료
[ ] GDSC 버전 선택 명시
```

### FE (Step 3)
```
[ ] Nextflow 실행 완료
[ ] features.parquet 생성 (15k~25k columns)
[ ] SMILES 매칭률 75% 이상
[ ] Feature Selection 완료 (5k~6k features)
```

### 모델 (Step 4~5)
```
[ ] 32개 모델 학습 완료
[ ] Gap 진단 완료 (PASS 10개 이상)
[ ] 앙상블 A/B 구성 완료
```

### Validation (Step 6)
```
[ ] Multi-objective scoring 완료
[ ] Top 15 Repurposing 선정
[ ] Positive Control 5개 선정
```

### ADMET (Step 7)
```
[ ] TDC 22 assays 다운로드
[ ] Tanimoto v1 방법론 적용
[ ] 평균 4~6 assays/drug 확보
[ ] Mock 데이터 미사용 확인 ✅
```

### KG/API (Step 7+)
```
[ ] PubMed 검증 완료
[ ] ChEMBL Target 검증 완료
[ ] Clinical Trials 검증 완료
```

### 최종
```
[ ] 모든 결과 파일 저장
[ ] 대시보드 업데이트 완료
[ ] README 작성 (v1/v2 차이 명시)
[ ] GitHub 커밋 & 푸시
```

---

## v3.1 vs v2 vs v1 주요 차이점

| 항목 | v1 | v2 | v3.1 |
|------|----|----|------|
| **모델 수** | 6개 | 7개 (MultiModal 추가) | 32개 |
| **Gap 진단** | 없음 | 없음 | ✅ 추가 |
| **Feature Selection** | 없음 | 없음 | ✅ RF Importance (72.9% 감축) |
| **앙상블** | Track 2 (6개) | v2 (7개) | A (3개) / B (5개) |
| **Step 6 Ranking** | IC50 only | IC50 + METABRIC | Multi-objective (5개 지표) |
| **ADMET** | Mock 데이터 | Mock 데이터 | ✅ v1 Tanimoto (실측) |
| **KG/API 검증** | 없음 | 없음 | ✅ PubMed/ChEMBL/ClinicalTrials |
| **Step 8** | ❌ | ✅ 멀티모달 허들 | ❌ 제거 |
| **대시보드** | 1개 | 2개 | 5개 (상호 연결) |

**v3.1 핵심 개선:**
- ✅ 과적합 진단 (Gap) 추가
- ✅ Feature Selection으로 효율성 향상
- ✅ ADMET Mock → 실측 데이터 (3.9배 커버리지 증가)
- ✅ KG/API 검증으로 신뢰도 향상
- ✅ Multi-objective ranking으로 다각도 평가
- ❌ Step 8 제거 (복잡도 감소)

---

## 참고 문헌

1. **Herbert et al. (2025)** "Monotherapy cancer drug-blind response prediction is limited to intraclass generalization" bioRxiv. DOI: 10.1101/2025.06.16.659838

2. **TDC (Therapeutics Data Commons)** ADMET Benchmark Group. https://tdcommons.ai/

3. **Gap 해석 가이드** (v3 신규):
   - Gap = OOF Spearman - Train Spearman
   - Gap ≤ 0.15: PASS (앙상블 포함)
   - 0.15 < Gap ≤ 0.20: WARNING (주의)
   - Gap > 0.20: FAIL (앙상블 제외)

---

## 문의 및 지원

- **GitHub Issues:** https://github.com/skkuaws0215/20260408_pre_project_biso_myprotocol/issues
- **팀장:** say2-4team
- **문서 버전:** v3.1 (2026-04-14)

---

**끝. 이 프로토콜을 따라 재현에 성공하시길 바랍니다!** 🚀


---

## 부록 A: 모델 상세 설정 (Step 4)

### A.1. 데이터 입력 형식

**features.parquet 구조:**
```python
# 컬럼 구조 예시
features.shape  # (20421, 5531) after feature selection
# Rows: drug-sample pairs
# Columns: 5531 features (FP + LINCS + Expression + Clinical)

# 컬럼 타입:
# - fp_0 ~ fp_2047: Morgan Fingerprint (2048 bits)
# - lincs_gene_* : LINCS L1000 (~978 genes)
# - expr_* : Gene expression (~1500 genes)
# - clinical_* : Clinical features (~5개)
```

**labels.parquet 구조:**
```python
# IC50 값 (log transformed)
labels.shape  # (20421, 1)
labels.columns  # ['IC50_log']

# 값 범위: -2.0 ~ 4.0 (log scale)
# 원본: IC50 (uM) → log10(IC50)
```

**train_test_split:**
```python
from sklearn.model_selection import KFold

# 5-fold CV + Holdout
n_samples = len(features)
indices = np.arange(n_samples)

# Holdout 20%
train_idx, holdout_idx = train_test_split(
    indices, test_size=0.2, random_state=42
)

# 5-fold on training set
kf = KFold(n_splits=5, shuffle=True, random_state=42)
for fold, (train_fold_idx, val_fold_idx) in enumerate(kf.split(train_idx)):
    X_train = features.iloc[train_idx[train_fold_idx]]
    y_train = labels.iloc[train_idx[train_fold_idx]]
    X_val = features.iloc[train_idx[val_fold_idx]]
    y_val = labels.iloc[train_idx[val_fold_idx]]

    # 모델 학습...
```

---

### A.2. CatBoost 상세 설정

**전체 코드:**
```python
from catboost import CatBoostRegressor
from scipy.stats import spearmanr
from sklearn.metrics import mean_squared_error
import numpy as np

# Hyperparameters (v3 최적화)
catboost_params = {
    'iterations': 1000,
    'learning_rate': 0.05,
    'depth': 6,
    'l2_leaf_reg': 3,
    'loss_function': 'RMSE',
    'eval_metric': 'RMSE',
    'random_seed': 42,
    'task_type': 'GPU',  # CPU로 변경 시 제거
    'devices': '0',      # GPU ID
    'verbose': 100
}

# 5-fold CV
oof_predictions = np.zeros(len(train_idx))
train_predictions = np.zeros(len(train_idx))
fold_scores = []

for fold, (train_fold_idx, val_fold_idx) in enumerate(kf.split(train_idx)):
    print(f"\n=== Fold {fold + 1}/5 ===")

    X_train = features.iloc[train_idx[train_fold_idx]]
    y_train = labels.iloc[train_idx[train_fold_idx]].values.ravel()
    X_val = features.iloc[train_idx[val_fold_idx]]
    y_val = labels.iloc[train_idx[val_fold_idx]].values.ravel()

    # 모델 학습
    model = CatBoostRegressor(**catboost_params)
    model.fit(
        X_train, y_train,
        eval_set=(X_val, y_val),
        early_stopping_rounds=50,
        verbose=False
    )

    # 예측
    train_pred = model.predict(X_train)
    val_pred = model.predict(X_val)

    # Train predictions 저장
    train_predictions[train_fold_idx] = train_pred

    # OOF predictions 저장
    oof_predictions[val_fold_idx] = val_pred

    # Fold 성능 계산
    fold_sp = spearmanr(y_val, val_pred)[0]
    fold_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
    fold_scores.append({'sp': fold_sp, 'rmse': fold_rmse})
    print(f"Fold {fold + 1}: Spearman={fold_sp:.4f}, RMSE={fold_rmse:.4f}")

# 전체 성능 계산
train_sp = spearmanr(labels.iloc[train_idx], train_predictions)[0]
oof_sp = spearmanr(labels.iloc[train_idx], oof_predictions)[0]
gap = train_sp - oof_sp

# Holdout 평가
X_holdout = features.iloc[holdout_idx]
y_holdout = labels.iloc[holdout_idx].values.ravel()
holdout_pred = model.predict(X_holdout)
holdout_sp = spearmanr(y_holdout, holdout_pred)[0]

print(f"\n=== CatBoost 최종 결과 ===")
print(f"Train Spearman: {train_sp:.4f}")
print(f"OOF Spearman: {oof_sp:.4f}")
print(f"Gap: {gap:.4f}")
print(f"Holdout Spearman: {holdout_sp:.4f}")
```

**예상 결과 (v3):**
- Train Spearman: 0.902
- OOF Spearman: 0.828
- Gap: 0.074 (PASS ✅)
- Holdout Spearman: 0.825

---

### A.3. LightGBM 상세 설정

```python
import lightgbm as lgb

# Hyperparameters
lgbm_params = {
    'objective': 'regression',
    'metric': 'rmse',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'max_depth': -1,
    'min_child_samples': 20,
    'reg_alpha': 0.1,
    'reg_lambda': 0.1,
    'random_state': 42,
    'n_estimators': 1000,
    'device': 'gpu',  # CPU 사용 시 제거
    'gpu_platform_id': 0,
    'gpu_device_id': 0,
    'verbose': -1
}

# 5-fold CV
oof_predictions = np.zeros(len(train_idx))

for fold, (train_fold_idx, val_fold_idx) in enumerate(kf.split(train_idx)):
    X_train = features.iloc[train_idx[train_fold_idx]]
    y_train = labels.iloc[train_idx[train_fold_idx]].values.ravel()
    X_val = features.iloc[train_idx[val_fold_idx]]
    y_val = labels.iloc[train_idx[val_fold_idx]].values.ravel()

    # LightGBM Dataset
    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

    # 학습
    model = lgb.train(
        lgbm_params,
        train_data,
        valid_sets=[train_data, val_data],
        valid_names=['train', 'valid'],
        callbacks=[
            lgb.early_stopping(stopping_rounds=50),
            lgb.log_evaluation(period=100)
        ]
    )

    # 예측
    val_pred = model.predict(X_val, num_iteration=model.best_iteration)
    oof_predictions[val_fold_idx] = val_pred

# 성능 계산
oof_sp = spearmanr(labels.iloc[train_idx], oof_predictions)[0]
print(f"LightGBM OOF Spearman: {oof_sp:.4f}")
```

**예상 결과:**
- Train Spearman: 0.905
- OOF Spearman: 0.815
- Gap: 0.090 (PASS ✅)

---

### A.4. FlatMLP (Deep Learning) 상세 설정

```python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

# 데이터셋 클래스
class DrugDataset(Dataset):
    def __init__(self, features, labels):
        self.X = torch.FloatTensor(features.values)
        self.y = torch.FloatTensor(labels.values).reshape(-1, 1)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

# 모델 아키텍처
class FlatMLP(nn.Module):
    def __init__(self, input_dim, hidden_dims=[512, 256, 128], dropout=0.3):
        super(FlatMLP, self).__init__()

        layers = []
        prev_dim = input_dim

        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout)
            ])
            prev_dim = hidden_dim

        layers.append(nn.Linear(prev_dim, 1))

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)

# 학습 설정
input_dim = features.shape[1]  # 5531
model = FlatMLP(input_dim=input_dim, hidden_dims=[512, 256, 128], dropout=0.3)

# GPU 설정
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = model.to(device)

# Optimizer & Loss
optimizer = optim.Adam(model.parameters(), lr=0.001)
criterion = nn.MSELoss()

# DataLoader
batch_size = 256
train_dataset = DrugDataset(X_train, y_train)
train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

# 학습
epochs = 100
for epoch in range(epochs):
    model.train()
    total_loss = 0

    for batch_X, batch_y in train_loader:
        batch_X = batch_X.to(device)
        batch_y = batch_y.to(device)

        # Forward
        predictions = model(batch_X)
        loss = criterion(predictions, batch_y)

        # Backward
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    avg_loss = total_loss / len(train_loader)

    if (epoch + 1) % 10 == 0:
        print(f"Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.4f}")

# 예측
model.eval()
with torch.no_grad():
    X_val_tensor = torch.FloatTensor(X_val.values).to(device)
    val_pred = model(X_val_tensor).cpu().numpy().ravel()

val_sp = spearmanr(y_val, val_pred)[0]
print(f"FlatMLP Validation Spearman: {val_sp:.4f}")
```

**예상 결과:**
- Train Spearman: 0.847
- OOF Spearman: 0.792
- Gap: 0.055 (PASS ✅)

---

### A.5. 전체 32개 모델 실행 스크립트

```python
# scripts/train_all_models.py
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
from sklearn.model_selection import KFold, train_test_split
import json

# 모델 import
from catboost import CatBoostRegressor
import lightgbm as lgb
import xgboost as xgb
from sklearn.ensemble import (
    ExtraTreesRegressor, RandomForestRegressor,
    GradientBoostingRegressor, AdaBoostRegressor, BaggingRegressor
)
from sklearn.experimental import enable_hist_gradient_boosting
from sklearn.ensemble import HistGradientBoostingRegressor

# 데이터 로드
features = pd.read_parquet('features_selected.parquet')
labels = pd.read_parquet('labels.parquet')

# Train/Holdout split
indices = np.arange(len(features))
train_idx, holdout_idx = train_test_split(
    indices, test_size=0.2, random_state=42
)

# 5-fold CV
kf = KFold(n_splits=5, shuffle=True, random_state=42)

# 모델 설정
MODELS = {
    'CatBoost': CatBoostRegressor(
        iterations=1000, learning_rate=0.05, depth=6,
        l2_leaf_reg=3, random_seed=42, verbose=False
    ),
    'LightGBM': lgb.LGBMRegressor(
        n_estimators=1000, learning_rate=0.05, num_leaves=31,
        reg_alpha=0.1, reg_lambda=0.1, random_state=42
    ),
    'XGBoost': xgb.XGBRegressor(
        n_estimators=1000, learning_rate=0.05, max_depth=6,
        reg_alpha=0.1, reg_lambda=0.1, random_state=42
    ),
    'ExtraTrees': ExtraTreesRegressor(
        n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
    ),
    'RandomForest': RandomForestRegressor(
        n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
    ),
    # ... 총 32개
}

# 전체 모델 학습
results = []

for model_name, model_class in MODELS.items():
    print(f"\n{'='*60}")
    print(f"Training: {model_name}")
    print(f"{'='*60}")

    # 5-fold CV
    oof_predictions = np.zeros(len(train_idx))
    train_predictions = np.zeros(len(train_idx))

    for fold, (train_fold_idx, val_fold_idx) in enumerate(kf.split(train_idx)):
        X_train = features.iloc[train_idx[train_fold_idx]]
        y_train = labels.iloc[train_idx[train_fold_idx]].values.ravel()
        X_val = features.iloc[train_idx[val_fold_idx]]
        y_val = labels.iloc[train_idx[val_fold_idx]].values.ravel()

        # 학습
        model = model_class
        model.fit(X_train, y_train)

        # 예측
        train_pred = model.predict(X_train)
        val_pred = model.predict(X_val)

        train_predictions[train_fold_idx] = train_pred
        oof_predictions[val_fold_idx] = val_pred

    # 성능 계산
    y_train_full = labels.iloc[train_idx].values.ravel()
    train_sp = spearmanr(y_train_full, train_predictions)[0]
    oof_sp = spearmanr(y_train_full, oof_predictions)[0]
    gap = train_sp - oof_sp

    # Holdout 평가
    X_holdout = features.iloc[holdout_idx]
    y_holdout = labels.iloc[holdout_idx].values.ravel()
    holdout_pred = model.predict(X_holdout)
    holdout_sp = spearmanr(y_holdout, holdout_pred)[0]

    # 판정
    if gap <= 0.15:
        verdict = "PASS"
    elif gap <= 0.20:
        verdict = "WARNING"
    else:
        verdict = "FAIL"

    # 결과 저장
    result = {
        'model': model_name,
        'train_sp': train_sp,
        'oof_sp': oof_sp,
        'holdout_sp': holdout_sp,
        'gap': gap,
        'verdict': verdict
    }
    results.append(result)

    print(f"Train Sp: {train_sp:.4f}")
    print(f"OOF Sp: {oof_sp:.4f}")
    print(f"Gap: {gap:.4f} ({verdict})")

# 결과 저장
results_df = pd.DataFrame(results)
results_df.to_csv('step4_model_results.csv', index=False)

print(f"\n{'='*60}")
print(f"✅ All 32 models trained!")
print(f"Results saved to: step4_model_results.csv")
print(f"{'='*60}")
```

---

## 부록 B: ADMET 상세 설정 (Step 7)

### B.1. TDC 데이터셋 다운로드 스크립트

```python
# scripts/download_admet_assays.py
from tdc.single_pred import ADME
import pandas as pd
from pathlib import Path

# ADMET assay 목록
ADMET_ASSAYS = [
    'Caco2_Wang', 'Bioavailability_Ma', 'HIA_Hou', 'Pgp_Broccatelli',
    'Solubility_AqSolDB', 'Lipophilicity_AstraZeneca', 'PPBR_AZ',
    'BBB_Martins', 'VDss_Lombardo',
    'CYP2C9_Substrate_CarbonMangels', 'CYP2D6_Substrate_CarbonMangels',
    'CYP3A4_Substrate_CarbonMangels', 'CYP2C9_Veith', 'CYP2D6_Veith',
    'CYP3A4_Veith',
    'Clearance_Hepatocyte_AZ', 'Clearance_Microsome_AZ', 'Half_Life_Obach',
    'AMES', 'DILI', 'hERG', 'LD50_Zhu'
]

# 다운로드 디렉토리
output_dir = Path('data/admet_assays')
output_dir.mkdir(parents=True, exist_ok=True)

for assay in ADMET_ASSAYS:
    print(f"\nDownloading: {assay}")

    try:
        # TDC에서 데이터 로드
        data = ADME(name=assay)
        df = data.get_data()

        # 저장
        assay_dir = output_dir / assay.lower()
        assay_dir.mkdir(exist_ok=True)

        output_file = assay_dir / 'train_val_basic_clean_20260406.parquet'
        df.to_parquet(output_file)

        print(f"✓ Saved: {output_file} ({len(df)} compounds)")

    except Exception as e:
        print(f"✗ Error: {e}")

print(f"\n✅ Download complete!")
print(f"Total assays: {len(list(output_dir.glob('*/*.parquet')))}")
```

### B.2. Tanimoto Similarity 매칭 전체 코드

```python
# scripts/admet_v1_tanimoto.py
import pandas as pd
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs
from pathlib import Path
import json

# ADMET assay 경로
ADMET_DIR = Path('data/admet_assays')

# Fingerprint 생성
def get_morgan_fp(smiles, radius=2, nBits=2048):
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            return AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits)
    except:
        pass
    return None

# Tanimoto similarity
def tanimoto_similarity(fp1, fp2):
    if fp1 and fp2:
        return DataStructs.TanimotoSimilarity(fp1, fp2)
    return 0.0

# Thresholds
THRESHOLDS = {
    'exact': 1.0,
    'close_analog': 0.85,
    'analog': 0.70
}

# 약물 SMILES 로드
drugs_df = pd.read_csv('step7_comprehensive_final.csv')
drug_smiles_map = dict(zip(drugs_df['drug_name'], drugs_df['smiles']))

# ADMET assay 로드 및 fingerprint 생성
assay_libraries = {}

for assay_dir in ADMET_DIR.glob('*'):
    assay_name = assay_dir.name
    parquet_file = assay_dir / 'train_val_basic_clean_20260406.parquet'

    if not parquet_file.exists():
        continue

    df_assay = pd.read_parquet(parquet_file)

    # Fingerprint 생성
    fps = []
    y_values = []

    for idx, row in df_assay.iterrows():
        smiles = row['Drug']
        y = row['Y']

        fp = get_morgan_fp(smiles)
        if fp:
            fps.append(fp)
            y_values.append(y)

    assay_libraries[assay_name] = {
        'fps': fps,
        'y_values': y_values
    }

    print(f"✓ {assay_name}: {len(fps)} compounds with fingerprints")

# 약물별 매칭
admet_results = {}

for drug_name, drug_smiles in drug_smiles_map.items():
    if pd.isna(drug_smiles):
        continue

    drug_fp = get_morgan_fp(drug_smiles)
    if not drug_fp:
        continue

    drug_result = {
        'drug_name': drug_name,
        'smiles': drug_smiles,
        'assays': {},
        'n_assays_found': 0
    }

    # 각 assay에 대해 best match 찾기
    for assay_name, library in assay_libraries.items():
        best_similarity = 0
        best_y = None
        match_type = 'no_match'

        for assay_fp, y_value in zip(library['fps'], library['y_values']):
            similarity = tanimoto_similarity(drug_fp, assay_fp)

            if similarity > best_similarity:
                best_similarity = similarity
                best_y = y_value

                # Match type 결정
                if similarity >= THRESHOLDS['exact']:
                    match_type = 'exact'
                elif similarity >= THRESHOLDS['close_analog']:
                    match_type = 'close_analog'
                elif similarity >= THRESHOLDS['analog']:
                    match_type = 'analog'
                else:
                    match_type = 'no_match'

        # Threshold 이상만 저장
        if best_similarity >= THRESHOLDS['analog']:
            drug_result['assays'][assay_name] = {
                'y_value': best_y,
                'similarity': best_similarity,
                'match_type': match_type
            }
            drug_result['n_assays_found'] += 1

    admet_results[drug_name] = drug_result

# 결과 저장
with open('admet_v1_detailed_results.json', 'w') as f:
    json.dump(admet_results, f, indent=2)

print(f"\n✅ ADMET v1 matching complete!")
print(f"Average matches: {np.mean([r['n_assays_found'] for r in admet_results.values()]):.1f} assays/drug")
```

---

## 부록 C: 디렉토리 구조

```
20260408_pre_project_biso_myprotocol/
├── README.md
├── PROTOCOL_v3.md
├── config/
│   ├── data_paths.yaml
│   └── nextflow.config
├── data/
│   ├── curated_date/          # S3 복사본
│   │   ├── gdsc/
│   │   ├── lincs/
│   │   ├── metabric/
│   │   └── drugbank/
│   ├── admet_assays/           # TDC 다운로드
│   │   ├── ames/
│   │   ├── dili/
│   │   └── ... (22개)
│   └── fe_output/
│       ├── features.parquet
│       ├── features_metabric.parquet
│       └── labels.parquet
├── scripts/
│   ├── download_admet_assays.py
│   ├── admet_v1_tanimoto.py
│   ├── train_all_models.py
│   └── feature_selection_rf.py
├── results/
│   ├── step4_model_results.csv
│   ├── step5_ensemble_A_results.json
│   ├── step7_admet_v1_detailed.json
│   └── step7_comprehensive_final.csv
└── dashboards/
    ├── v1_vs_v3_comparison_dashboard.html
    ├── step4_model_detail_dashboard.html
    ├── step5_ensemble_dashboard.html
    ├── step6_metabric_dashboard.html
    └── step7_admet_dashboard.html
```

---

