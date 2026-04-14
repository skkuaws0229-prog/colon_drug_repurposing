# Drug Discovery Pipeline 팀원 재현 프로토콜
## biso_myprotocol · say2-4team · v3.0
**작성일:** 2026-04-08 | **수정일:** 2026-04-14 | **작성자:** say2-4team | **버전:** v3.0

> **v3.0 변경사항 (20260414):**
> - Step 3-2.5: 매칭 품질 검증 신규 추가 (SMILES 유효성·Fingerprint 품질·소스별 신뢰도·교차 검증·구조 일관성·Tanimoto 중복·Scaffold 검증)
> - Step 3.5: Feature Selection 신규 추가 (low variance → correlation → importance)
> - Step 4: 평가 체계 6단계 확장 (5CV → holdout → GroupKFold → unseen drug → scaffold split → multi-seed stability)
> - Step 4: 측정 지표 32개로 확대 (예측 성능 8 + 과적합 5 + 일반화 6종 + 앙상블 4 + 약물 랭킹 9)
> - Step 7+: scaleup_biso KG/API 연동 ADMET 검증·설명 자동화 추가
> - MultiModalFusionNet 제외 (RMSE FAIL + 앙상블 다양성 미기여 확인)
> - Step 8 멀티모달 허들 게이트 제외 (향후 Studying Project에서 재검토)

---

## 참고 자료
- **메인 대시보드:** https://skkuaws0215.github.io/20260408_pre_project_biso_myprotocol/dashboard.html
- **GitHub 저장소:** https://github.com/skkuaws0215/20260408_pre_project_biso_myprotocol.git
- **KG API 서버:** 20260409_scaleup_biso/ (Neo4j + FastAPI)

---

## 이 문서의 목적

이 프로토콜은 biso_myprotocol의 Drug Discovery Pipeline을 팀원이 **자신의 저장소에서 동일한 방법론으로 재현**할 수 있도록 작성된 가이드입니다.

**시작점:** 본인이 보유한 전처리 완료 데이터 (curated_date/)
**목표:** 이 프로토콜을 따라 새 환경/저장소에서 동일한 방법론으로 실험을 재현하는 것

> 이 프로토콜은 재현 가이드입니다. 본인의 전처리 데이터와 저장소를 사용해서 각 단계를 직접 실행하세요.

---

## 전체 파이프라인 흐름

```
전처리 완료 데이터 (curated_date/)
        ↓
Step 1. 환경 설정
        ↓
Step 2. 전처리 데이터 준비
        ↓
Step 3. FE 실행 - AWS Batch + Nextflow
  └─ Step 3-2.5 매칭 품질 검증              ← [20260414] 신규
        ↓
Step 3.5 Feature Selection                  ← [20260414] 신규
        ↓
Step 4. 모델 학습 + 6단계 평가 체계          ← [20260414] 확장
        ↓
Step 5. 앙상블 Track 2 (6모델)
        ↓
Step 6. METABRIC 외부 검증 A+B+C
        ↓
Step 7. ADMET Gate ML 자동화
  └─ Step 7+ KG/API 검증·설명 자동화        ← [20260414] 신규
        ↓
결과 저장 + 대시보드 업데이트
```

---

## 재현 결과에 대한 기대치

이 프로토콜을 따르더라도 biso_myprotocol 수치와 완전히 동일한 결과가 나오지 않을 수 있습니다. 이는 정상입니다.

| 항목 | 차이가 생기는 이유 | 허용 여부 |
|---|---|---|
| FE 컬럼 수 | 데이터 버전·범위·전처리 조건 차이 | 정상 범위 허용 |
| 모델 Spearman·RMSE | FE 입력값 차이 + 랜덤 시드 | 방향성만 동일하면 OK |
| METABRIC 검증 지표 | FE 차이가 누적되어 반영 | 방향성만 동일하면 OK |
| 추천 약물 순위 | 모델 예측값 분포 차이 | 일부 순위 변동 가능 |
| Feature Selection 후 컬럼 수 | selection 기준 차이 | ±20% 허용 |

> 중요: 숫자가 다소 달라도 방법론이 동일하면 재현 성공입니다. biso_myprotocol 기준 수치는 비교 참고값입니다.

---

## 절대 규칙 (반드시 준수)

```
1. curated_date/         → 읽기 전용, 수정·삭제 절대 금지
2. curated_date/glue/    → 접근 자체 금지 (다른 팀원 영역)
3. Proxy 데이터 사용 시  → 즉시 멈추고 팀장에게 확인 요청
4. ADMET 외부 DB 추가 시 → 반드시 명시 후 진행
5. .aws/credentials      → Git 커밋 절대 금지
6. AWS 리소스 생성 시    → 태그 필수: Key=pre-batch-2-4-team, Value=YYYYMMDD_본인이름
7. features.parquet 원본 → 수정 금지, Feature Selection은 별도 파일로 생성
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
- 추가 모델도 앙상블 기준(Sp≥0.713 AND RMSE≤1.385) 동일 적용

### 데이터 버전 명시
- GDSC1+2 병합 또는 GDSC2만 사용 여부 명시
- LINCS 원본 추출 또는 기존 파일 사용 여부 명시
- 프로토콜과 다른 처리는 README·대시보드에 반드시 기재

---

## STEP 1. 환경 설정
**예상 소요 시간: 1~2시간**

### 1-1. GitHub 저장소 클론
```bash
git clone https://github.com/skkuaws0215/20260408_pre_project_biso_myprotocol.git
git clone https://github.com/[본인계정]/[본인저장소].git
cd [본인저장소]
```

### 1-2. Python 환경 설정
```bash
conda create -n drug4 python=3.10 -y
conda activate drug4
pip install pandas numpy scikit-learn lightgbm xgboost catboost \
    torch pyarrow boto3 awscli rdkit-pypi nextflow
```

### 1-3. Nextflow 설치
```bash
conda install -c conda-forge openjdk=11
curl -s https://get.nextflow.io | bash
chmod +x nextflow && sudo mv nextflow /usr/local/bin/
nextflow -version
```

### 1-4. AWS 설정
```bash
aws configure  # Account: 666803869796 확인
aws sts get-caller-identity
aws s3 ls s3://say2-4team/curated_date/
# aws s3 ls s3://say2-4team/curated_date/glue/  ← 절대 접근 금지
```

### 1-5. AWS Batch 환경 세팅

**태그 설정:**
```bash
TAG_KEY="pre-batch-2-4-team"
TAG_VAL="YYYYMMDD_본인이름"
```

**ECR 이미지 빌드 & 푸시:**
```bash
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
ECR_URI=${AWS_ACCOUNT}.dkr.ecr.ap-northeast-2.amazonaws.com/drug4-fe
aws ecr create-repository --repository-name drug4-fe \
  --region ap-northeast-2 --tags Key=${TAG_KEY},Value=${TAG_VAL}
docker build -t drug4-fe --platform linux/amd64 .
docker tag drug4-fe:latest ${ECR_URI}:latest
docker push ${ECR_URI}:latest
```

### QC 체크
```
[ ] conda drug4 환경 생성 완료
[ ] Nextflow 정상 동작 확인
[ ] AWS Account 666803869796 확인
[ ] ECR 이미지 빌드·푸시 완료 (linux/amd64)
[ ] AWS Batch Compute Env·Job Queue 확인
[ ] GitHub 저장소 클론 완료
```

---

## STEP 2. 전처리 데이터 준비
**예상 소요 시간: 1~2시간**

### 2-1. curated_date/ 파일 목록 확인 (읽기만)
```bash
aws s3 ls s3://say2-4team/curated_date/ --human-readable
```

### 2-2. 업무폴더로 복사 (glue/ 제외 필수)
```bash
aws s3 cp s3://say2-4team/curated_date/ \
  s3://say2-4team/[본인업무폴더]/data/ \
  --recursive --exclude "glue/*"
```

### 2-3. LINCS MCF7 처리
- **방법 A (권장):** oringinal_raw/lincs/ Level 5 GCTx(21GB)에서 직접 MCF7 추출
- **방법 B:** 팀 공유 lincs_mcf7.parquet 사용 (팀장 확인 후)

### 2-4. GDSC 처리 결정
> biso_myprotocol은 GDSC2만 사용 (품질 우선 결정). 선택 이유를 README에 명시할 것.

### 2-5. config/data_paths.yaml 설정
```yaml
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
**예상 소요 시간: 3~6시간**

### 3-1. 핵심 원칙 (반드시 준수)
```
✅ fit (imputation median, variance threshold) → TCGA 기준으로만 계산
✅ METABRIC → TCGA fit 기준값으로 transform만 적용 (fit 절대 금지)
✅ leakage 컬럼 제거 (샘플ID, 날짜, 결과 직접 포함)
✅ high-missing(>30%) 제거 · median imputation · variance filtering
✅ TCGA/METABRIC 컬럼 구조 반드시 일치
```

### 3-2. Drug Features 매칭
```
1순위: ChEMBL (canonical_smiles 품질 우수)
2순위: DrugBank (미매칭 보완)
3순위: GDSC annotation fuzzy matching
4순위: PubChem API (외부 조회)
미매칭: SMILES=NA (all-zero fingerprint 처리)
```

### 3-2.5 매칭 품질 검증 [20260414 신규]

> 매칭률(예: 82.4%)만으로는 품질을 보장할 수 없음. 1% 매칭도 "매칭"으로 카운트되므로
> 실제 정보 기여도를 검증해야 함.

**① SMILES 유효성 검증**
- RDKit 파싱 성공 여부 확인 (mol = Chem.MolFromSmiles(smiles))
- 파싱 실패 → NA 처리
- 지표: raw parse success rate / final usable SMILES rate (두 지표 분리)
- 분자량·원자 수 합리성 점검 (MW < 50 또는 MW > 5000 → flag)

**② Fingerprint 품질 검증**
- Morgan Fingerprint(radius=2, nBits=2048) 생성 성공 여부
- bit density 하한 점검: 전체 2048비트 중 non-zero 비트 비율
  - < 2% (41비트 미만) → flag (정보량 부족)
- 분포 통계 저장: median, p5, p95 bit density
- all-zero fingerprint와 실질적으로 구분되지 않는 건 → NA와 동일 취급

**③ 소스별 신뢰도 등급**
| 등급 | 소스 | 기준 |
|---|---|---|
| A (High) | ChEMBL canonical_smiles | 정확한 이름 매칭 |
| B (Medium) | DrugBank exact name | 정확한 이름 매칭 |
| C (Low) | DrugBank synonym / fuzzy matching | 유사 이름 매칭 |
| D (Lowest) | PubChem API 이름 검색 | 오매칭 가능성 있음 |

- A+B등급 비율 모니터링: 전체 매칭의 60% 이상 권장
- D등급 건은 교차 검증 우선 대상

**④ Cross-source 교차 검증**
- 동일 약물을 2개 이상 소스에서 매칭한 경우 canonical SMILES 또는 InChIKey 기준 일치 여부 확인
- 교차 검증 가능 대상에서 concordance rate 산출 (90% 이상 목표)
- 불일치 건 → 수동 검토 또는 A등급 소스 우선 채택

**⑤ 구조 일관성 검증**
- 동일 canonical_drug_id 내에서 상이한 구조가 매핑된 경우 확인
- drug_id 내 구조 충돌 → FAIL 처리 (재매칭 또는 manual review)
- 전역 duplicate는 기록, drug_id 내 충돌은 fail

**⑥ Tanimoto / 중복 검증**
- 매칭된 약물 간 Tanimoto 유사도 계산
- exact duplicate (Tanimoto = 1.0 + 다른 drug_id) 점검
- near-duplicate (Tanimoto > 0.95 + 다른 drug_id) 점검
- 전역 duplicate는 기록으로 남기고, drug_id 내 충돌은 fail 처리

**⑦ Scaffold 생성 가능성 점검**
- Murcko scaffold 생성 성공률 기록
- scaffold split (Step 4 평가)에 필요하므로 실패 시 해당 약물 scaffold split 대상에서 제외

**⑧ 품질 미달 처리 순서**
```
1. rematch: 다른 소스로 재매칭 시도
2. fallback: 하위 소스 재조회
3. NA 처리: 최종 미매칭 → all-zero fingerprint
4. manual review queue: 구조 충돌·오매칭 의심 건 기록
```

### 매칭 품질 QC 기준
| 항목 | 기준 | 비고 |
|---|---|---|
| SMILES raw parse success rate | 기록 | 파싱 성공한 건수 |
| Final usable SMILES rate | 95% 이상 | 파싱 성공 + bit density 통과 |
| Bit density < 2% flag 건수 | 기록 | 정보량 부족 약물 수 |
| A+B등급 비율 | 60% 이상 | 고신뢰 매칭 비율 |
| Cross-source concordance | 90% 이상 | 교차 검증 일치율 |
| drug_id 내 구조 충돌 | 0건 | 충돌 시 fail |
| Scaffold 생성 성공률 | 기록 | scaffold split 대상 확인 |

### QC 체크
```
[ ] SMILES RDKit 파싱 완료 · 성공률 기록
[ ] Fingerprint bit density 분포 확인 · flag 건수 기록
[ ] 소스별 A/B/C/D 등급 분류 완료
[ ] Cross-source 교차 검증 완료 · concordance rate 기록
[ ] drug_id 내 구조 충돌 0건 확인
[ ] Tanimoto 중복 점검 완료
[ ] Scaffold 생성 성공률 기록
[ ] 품질 미달 건 처리 완료 (rematch/NA/manual review)
[ ] 전체 매칭 품질 보고서 README 명시
```

### 3-3. Nextflow config 설정
```bash
process.executor = 'awsbatch'
process.queue    = 'team4-fe-queue-cpu'
aws.region       = 'ap-northeast-2'
workDir          = 's3://say2-4team/[본인업무폴더]/nextflow_work/'
aws.batch.jobDefinitionTags = ['pre-batch-2-4-team': 'YYYYMMDD_본인이름']
```

### 3-4. FE 실행
```bash
nextflow run nextflow/main.nf \
  -profile awsbatch \
  -c nextflow.config \
  --s3_input  s3://say2-4team/[본인업무폴더]/data/ \
  --s3_output s3://say2-4team/[본인업무폴더]/fe_output/ \
  --run_name  YYYYMMDD_newfe_v8_본인이름 \
  --config    config/data_paths.yaml \
  -resume -with-report fe_report.html -with-trace fe_trace.txt
```

### 3-5. FE 완료 QC 기준
| 확인 항목 | biso 기준값 | 허용 범위 |
|---|---|---|
| 최종 컬럼 수 | 18,316 | ±500 |
| TCGA 행 수 | 7,730 | GDSC 버전에 따라 다름 |
| LINCS 매핑률 | 82.4% | ±5% |
| Drug SMILES 매칭률 | 82.4% (243/295) | ±10% |

### FE QC 체크
```
[ ] FE 실행 완료 · 산출물 구조 확인
[ ] METABRIC에 TCGA fit transform만 적용 확인
[ ] 컬럼 수·행 수·매핑률 기록
[ ] 결측치 없음 확인 (median imputation 완료)
[ ] S3 출력 확인 (features.parquet · labels.parquet · preprocessing_stats.json)
```

---

## STEP 3.5 Feature Selection [20260414 신규]
**예상 소요 시간: 1~2시간**

> FE 산출물(features.parquet)은 원본 보존. Feature Selection 결과는 features_slim.parquet로 별도 생성.
> TCGA 기준으로 selection → METABRIC에 동일 컬럼 적용 (METABRIC에서 별도 selection 금지 = leakage).

### 3.5-1. Selection 순서 (반드시 이 순서로)

**1단계: Low Variance 제거**
- 분산이 임계값 미만인 feature 제거
- TCGA 데이터 기준으로 variance 계산
- 제거된 컬럼 목록 기록

**2단계: High Correlation 정리**
- Pearson 상관계수 > 0.95인 feature 쌍에서 하나 제거
- 제거 기준: 상관 쌍 중 전체 feature와의 평균 상관이 더 높은 쪽 제거
- 제거된 컬럼 목록 기록

**3단계: Feature Importance 기반 하위 컷**
- CatBoost(앙상블 통과 모델 중 Best)로 1회 학습
- importance 하위 10~20% 제거
- 단, biology signal(CRISPR 핵심 유전자, 약물 타겟 관련 feature) 보존 주의
- 제거된 컬럼 목록 기록

### 3.5-2. 산출물
```
features.parquet       → 원본 (수정 금지)
features_slim.parquet  → selection 후 버전
feature_selection_log.json → 각 단계별 제거 컬럼·제거 사유·잔여 컬럼 수
```

### 3.5-3. METABRIC 적용
- TCGA에서 selection한 컬럼 목록을 그대로 METABRIC에 적용
- METABRIC에서 별도 selection 절대 금지 (leakage)

### QC 기준
| 항목 | 기준 |
|---|---|
| 원본 대비 잔여 컬럼 비율 | 50~80% 권장 |
| slim vs 원본 성능 비교 | slim이 동등 이상이면 slim 채택 |
| biology signal 보존 | 핵심 유전자·타겟 feature 잔존 확인 |
| TCGA-METABRIC 컬럼 일치 | 100% |

### QC 체크
```
[ ] Low variance 제거 완료 · 제거 수 기록
[ ] High correlation 정리 완료 · 제거 수 기록
[ ] Importance 하위 컷 완료 · 제거 수 기록
[ ] features_slim.parquet 생성 완료
[ ] feature_selection_log.json 저장
[ ] METABRIC에 동일 컬럼 적용 확인
[ ] 원본 features.parquet 미수정 확인
```

---

## STEP 4. 모델 학습 + 6단계 평가 체계 [20260414 확장]
**예상 소요 시간: 8~16시간 (GPU 권장, 평가 확장 포함)**

### 4-1. 모델 구성

> 튜닝 현황: 모든 모델은 하이퍼파라미터 기본값(default) 사용. 튜닝 미적용.

| # | 모델 | 유형 | biso Spearman | biso RMSE | 비고 |
|---|---|---|---|---|---|
| 1 | LightGBM | ML | 0.7913 | 1.3438 | 앙상블 PASS |
| 2 | LightGBM DART | ML | 0.7848 | 1.4029 | RMSE FAIL |
| 3 | XGBoost | ML | 0.7895 | 1.3445 | 앙상블 PASS |
| 4 | CatBoost | ML | 0.8007 | 1.3172 | ML Best |
| 5 | RandomForest | ML | 0.6267 | 1.9747 | FAIL |
| 6 | ExtraTrees | ML | 0.6468 | 1.8704 | FAIL |
| 7 | Stacking (Ridge) | ML | 0.7981* | 1.3213* | 시간초과 제외 |
| 8 | RSF | ML | 0.6142 | - | METABRIC 전용 |
| 9 | ResidualMLP | DL | 0.7855 | 1.3776 | 앙상블 PASS |
| 10 | FlatMLP | DL | 0.7936 | 1.3429 | DL Best |
| 11 | TabNet | DL | 0.7780 | 1.3892 | RMSE FAIL |
| 12 | FT-Transformer | DL | 0.7625 | 1.4444 | FAIL |
| 13 | Cross-Attention | DL | 0.7852 | 1.3716 | Gap=0.024 최우수 |
| 14 | GraphSAGE | GNN | 0.3852 | 2.3189 | METABRIC 전용 |
| 15 | GAT | GNN | 0.0085 | 2.6608 | FAIL |

### 4-2. 앙상블 포함 기준
```
Spearman ≥ 0.713 AND RMSE ≤ 1.385 → 앙상블 포함
하나라도 FAIL → 앙상블 제외
Graph 계열 → P@20 ≥ 0.70 별도 기준 적용
RSF → C-index 기준 별도 판단 (METABRIC 전용)
```

### 4-3. 과적합 기준
| Gap(Sp) | 판정 |
|---|---|
| < 0.05 | 과적합 없음 ✅ |
| 0.05~0.10 | 허용 범위 ⚠️ |
| 0.10~0.15 | 주의 ⚠️⚠️ |
| > 0.15 | 과적합 심각 ❌ |

### 4-4. 6단계 평가 체계 [20260414 신규]

> 기존 Random 5CV만으로는 모델 일반화 능력을 판단하기 어려움.
> 앙상블 통과 모델(6개)에만 전체 평가 적용. FAIL 모델은 1단계(5CV)만 실행.

**1단계: Random 5CV + Holdout (기존)**
- 무작위 5-fold CV + 20% holdout test
- 기본 성능 기준선 확보
- 모든 15개 모델에 적용

**2단계: GroupKFold (by canonical_drug_id)**
- 같은 약물이 train/val에 섞이지 않도록 분리
- 약물 단위 일반화 능력 평가
- 앙상블 통과 모델에만 적용

**3단계: Unseen Drug Holdout**
- 학습에 완전히 없던 약물(20~30%)로만 test
- 실제 배치 시나리오 재현
- top-k recall 중요 (Top 30 중 실제 활성 약물 비율)

**4단계: Scaffold Split**
- Murcko scaffold 기준 완전 분리
- 구조적으로 새로운 약물에 대한 예측력
- Step 3-2.5 scaffold 생성 성공 건만 대상

**5단계: Multi-seed Stability**
- seed 5개 (42, 123, 456, 789, 2026) 돌려서 mean±std
- top-k overlap: seed 바꿔도 Top 30이 몇 개 겹치는지
- fold std: 5개 fold 간 성능 편차

### 4-5. 측정 지표 (총 32개) [20260414 확장]

**예측 성능 (8개)**
| 지표 | 설명 | 용도 |
|---|---|---|
| Spearman | 순위 상관 | 핵심 지표 |
| Kendall tau | 보수적 순위 상관 (동점 처리) | Spearman 보완 |
| Pearson | 선형 상관 | 선형 관계 확인 |
| R² | 설명력 (전체 분산 중 모델 설명 비율) | 전반적 적합도 |
| RMSE | 예측 오차 크기 | 핵심 지표 |
| MAE | 절대 오차 평균 | 이상치 덜 민감 |
| MedianAE | 절대 오차 중앙값 | 대부분 예측의 실제 정확도 |
| P95 absolute error | 최악 5% 오차 크기 | 꼬리 위험(tail risk) |

**과적합 진단 (5개)**
| 지표 | 설명 |
|---|---|
| Train Spearman | 학습 데이터 성능 |
| OOF Spearman | Out-of-Fold 전체 예측 성능 |
| Gap (Train - OOF) | 과적합 정도 |
| Train/Val Ratio | 과적합 비율 |
| Fold별 Spearman std | fold 간 성능 안정성 |

**일반화 (Split별 6종)**
| Split | 기준 | 목적 | 주요 지표 |
|---|---|---|---|
| Random 5CV | 무작위 | 기본 평균 성능 | Spearman, RMSE, MAE, R² |
| Holdout | 무작위 test | 최종 성능 | Spearman, RMSE, MAE, R² |
| GroupKFold (Drug) | canonical_drug_id | 새 약물 일반화 | Spearman, RMSE |
| Unseen Drug | 약물 완전 분리 | 실제 배치 일반화 | Spearman, top-k recall |
| Scaffold Split | scaffold 완전 분리 | 구조 일반화 | Spearman, RMSE |
| Stability | multi-seed | 재현성 | mean±std, top-k overlap |

**앙상블 품질 (4개)**
| 지표 | 설명 |
|---|---|
| 앙상블 > 개별 Best | 앙상블 의미 여부 |
| 앙상블 Gap | 앙상블 과적합 |
| 가중치 분포 | 특정 모델 쏠림 여부 |
| 모델 간 예측 상관 (diversity) | 상관 높으면 앙상블 효과 없음 |

**약물 랭킹 품질 (9개)**
| 지표 | 설명 |
|---|---|
| Precision@k | Top k 중 실제 활성 약물 비율 |
| Recall@k | 전체 활성 약물 중 Top k에 포함된 비율 |
| NDCG@k | 순위 품질 (상위에 좋은 약물일수록 높음) |
| MAP | Mean Average Precision |
| EF@k (Enrichment Factor) | 랜덤 대비 Top k 활성 약물 농축 배수 |
| Top-k overlap (across seeds) | seed 변경 시 Top 30 겹침률 |
| Top-k overlap (across splits) | split 방식 간 Top 30 겹침률 |
| 동일 계열 중복률 | Top 30 내 같은 MOA 비율 |
| Target coverage | Top 30이 커버하는 타겟 수 |

### 4-6. 실행 순서
```bash
# ML 8개 먼저 (CPU) — features_slim.parquet 사용
python ml/train_all_models.py \
  --fe_path    [FE_OUTPUT]/tcga/features_slim.parquet \
  --label_path [FE_OUTPUT]/tcga/labels.parquet \
  --output_dir models/ --cv_folds 5

# 원본 비교 실행 (앙상블 통과 모델 1~2개만)
python ml/train_all_models.py \
  --fe_path    [FE_OUTPUT]/tcga/features.parquet \
  --label_path [FE_OUTPUT]/tcga/labels.parquet \
  --output_dir models_full/ --cv_folds 5 --models catboost,lightgbm

# GraphSAGE·GAT (drug-split 필수)
python ml/train_graph.py --split_strategy drug --output_dir models/graph/

# 6단계 평가 (앙상블 통과 모델에만)
python ml/evaluate_extended.py \
  --model_dir models/ \
  --fe_path   [FE_OUTPUT]/tcga/features_slim.parquet \
  --seeds     42,123,456,789,2026 \
  --output    evaluation_results/
```

### QC 체크
```
[ ] ML 8개 완료 · 결과값 기록
[ ] DL 5개 완료 · 결과값 기록
[ ] Graph 2개 완료 · drug-split 적용 확인
[ ] 앙상블 통과 모델 목록 확정
[ ] slim vs 원본 성능 비교 완료
[ ] 6단계 평가 완료 (앙상블 통과 모델)
[ ] 32개 지표 기록
[ ] 과적합 진단 · Gap 기록
[ ] 약물 랭킹 지표 기록
[ ] top-k overlap (seeds/splits) 기록
```

---

## STEP 5. 앙상블 (Track 2 — Spearman 가중 평균, 6모델)
**예상 소요 시간: 2~3시간**

### 5-1. 앙상블 구조
```
[입력] features_slim.parquet (전체 샘플)
        ↓
[6개 모델 병렬 예측]
각 모델이 동일 입력으로 IC50 예측값 생성
(OOF: Out-of-Fold 예측값 사용)
        ↓
[Spearman 기반 가중치 계산]
가중치 = 각 모델 Val Spearman / 전체 합계
        ↓
[가중 평균 → 최종 IC50 예측값]
약물별 앙상블 IC50 = Σ(모델 예측값 × 가중치)
        ↓
[Top 30 추출]
        ↓
[METABRIC 검증 → Top 15 선별]
```

### 5-2. 튜닝 현황
- 가중치 최적화 미적용 (Spearman 단순 가중 평균)
- 개선 방향: Optuna 기반 가중치 최적화 시 추가 성능 향상 가능

### 5-3. 실행
```bash
python ml/ensemble/ensemble_track2.py \
  --model_dir  models/ \
  --fe_path    [FE_OUTPUT]/tcga/features_slim.parquet \
  --output     ensemble_results/
```

### 5-4. QC 기준
```
✅ 앙상블 Spearman > 개별 Best 모델 Spearman (핵심)
✅ Gap ≈ 0 (과적합 없음)
✅ Top 30 전부 Sensitivity 확인
✅ 동일 계열 약물 중복 여부 확인 (다양성)
✅ biso 기준: Spearman 0.8055, RMSE 1.3008, Gap 0.0004
```

### QC 체크
```
[ ] 앙상블 Spearman > 개별 Best 모델 확인
[ ] Gap 확인
[ ] Top 30 추출 완료
[ ] 약물 랭킹 지표 (Precision@k, NDCG@k, EF@k) 기록
[ ] S3 저장 완료
```

---

## STEP 6. METABRIC 외부 검증 (A+B+C)
**예상 소요 시간: 30~45분**

### 6-1. 검증 방법
| 방법 | 입력 | 평가 지표 | biso 결과 |
|---|---|---|---|
| A — IC50 proxy | METABRIC FE + 앙상블 예측 | Spearman | 29/30 타겟 BRCA 발현 확인 |
| B — Survival binary | METABRIC OS/RFS + RSF 모델 | C-index · AUROC | C-index=0.821 |
| C — GraphSAGE P@20 | drug-drug 유사도 그래프 | P@20 | P@20=0.94 |

### 6-2. 실행
```bash
python ml/metabric_validation/validate_abc.py \
  --model_dir     models/ \
  --metabric_fe   [FE_OUTPUT]/metabric/ \
  --metabric_clin [본인업무폴더]/data/metabric/metabric_clinical_*.parquet \
  --output        metabric_results/
```

### QC 체크
```
[ ] Method A·B·C 모두 완료
[ ] 방향성 확인 (Spearman 높을수록, AUROC 0.5 이상)
[ ] Top 15 선별 완료
[ ] S3 저장 완료
```

---

## STEP 7. ADMET Gate (ML 자동화 · 3단계 필터링)
**예상 소요 시간: 40분~1시간**

### 7-1. ADMET ML 자동화 개요
- 22개 ADMET assay 스크리닝
- Morgan Fingerprint (SMILES 기반) → 피처 생성
- Tanimoto 유사도 매칭으로 학습 데이터 구성
- 각 assay별 개별 모델 학습

### 7-2. 추가 외부 DB (반드시 명시)
| DB | 용도 | 목표 |
|---|---|---|
| PyTDC | 전체 성능 보강 | 85.8% → 90%+ |
| SuperCYP | CYP3A4 억제제/기질 분리 | 80% → 90%+ |
| NCATS ADME | 경계값 케이스 보강 | 오판 감소 |
| ChEMBL ADMET | 커버리지 확대 | - |

### 7-3. CYP3A4 분리 모델 (중요)
```python
model_cyp3a4_inhibitor = train(cyp3a4_inhibitor_data)
model_cyp3a4_substrate = train(cyp3a4_substrate_data)
```

### 7-4. 3단계 필터링 기준
```
Tier 1 Hard Fail → 즉시 탈락
  - hERG > 0.7, PAINS > 0, Lipinski 위반 > 2

Tier 2 Soft Flag → 검토 후 판단
  - hERG 0.5~0.7, DILI · Ames · CYP3A4 · PPB · Caco2

Tier 3 Context → 항암제 특성상 완화 적용
  - F(oral) · t_half · Carcinogenicity
```

### 7-5. 약물 분류 기준 (유방암 기준)
| 카테고리 | 기준 |
|---|---|
| 유방암 현재 사용 | FDA 유방암 적응증 승인 |
| 유방암 적응증 확장/연구 중 | 임상시험 진행 중·타 암종 승인 |
| 유방암 미사용 | 신약 후보물질 |

### 7-6. 실행
```bash
python admet/admet_ml_v2.py \
  --drug_list    ensemble_results/top15_drugs.csv \
  --external_db  pytdc supercyp ncats_adme chembl \
  --output       admet_results/
```

### ADMET QC 기준
| 항목 | 목표 |
|---|---|
| 전체 정확도 | 85.8% 이상 |
| hERG | 100% |
| Ames | 80% 이상 |
| BBB | 93% 이상 |
| CYP3A4 | 80% 이상 |

### QC 체크
```
[ ] 22개 assay 스크리닝 완료
[ ] 외부 DB 추가 사용 시 명시 확인
[ ] CYP3A4 억제제/기질 분리 적용 확인
[ ] Tier 1 통과 약물 확인
[ ] 유방암 적응증 기준 분류 적용
[ ] 최종 약물 목록 S3 저장 완료
```

---

## STEP 7+. KG/API 검증·설명 자동화 [20260414 신규]
**예상 소요 시간: 30분~1시간**

> 20260409_scaleup_biso (Neo4j + FastAPI)를 활용하여
> ADMET 통과 약물에 대한 근거 자료를 자동으로 수집·검증합니다.

### 7+-1. 자동 수집 항목
| 소스 | 수집 내용 | API 엔드포인트 |
|---|---|---|
| FAERS | 부작용 빈도·심각도 | /api/drug/{name}/side_effects |
| ClinicalTrials.gov | 임상시험 현황·단계·모집상태 | /api/drug/{name}/trials |
| HIRA | 약가·급여/비급여 정보 | /api/drug/{name} (보험 필드) |
| PubMed | 최신 관련 논문 | /api/pubmed?query={drug}+breast+cancer |
| Neo4j KG | 타겟·pathway·PPI 네트워크 | /api/drug/{name}/targets, /pathways |

### 7+-2. 실행
```bash
# KG API 서버 실행 (별도 터미널)
cd 20260409_scaleup_biso
uvicorn chat.api_server:app --reload --port 8000

# ADMET 통과 약물 자동 검증
python scripts/kg_validation.py \
  --drug_list  admet_results/final_drugs.csv \
  --api_url    http://localhost:8000 \
  --output     kg_validation_results/
```

### 7+-3. 산출물
- 약물별 근거 자료 종합 보고서 (JSON/CSV)
- 부작용 프로파일 요약
- 임상시험 현황 요약
- 관련 논문 목록
- 타겟-pathway 네트워크 시각화 데이터

### QC 체크
```
[ ] FAERS 부작용 수집 완료 (Top 15 약물)
[ ] ClinicalTrials 임상시험 현황 수집 완료
[ ] PubMed 관련 논문 수집 완료
[ ] Neo4j 타겟·pathway 조회 완료
[ ] 약물별 종합 근거 보고서 생성
[ ] 대시보드 반영
```

---

## 결과 저장 및 공유

```bash
BASE="s3://say2-4team/[본인업무폴더]"
aws s3 sync fe_output/ ${BASE}/fe_output/
aws s3 sync models/ ${BASE}/models/
aws s3 sync ensemble_results/ ${BASE}/ensemble_results/
aws s3 sync evaluation_results/ ${BASE}/evaluation_results/
aws s3 sync metabric_results/ ${BASE}/metabric_results/
aws s3 sync admet_results/ ${BASE}/admet_results/
aws s3 sync kg_validation_results/ ${BASE}/kg_validation_results/

git add .
git commit -m "feat: [YYYYMMDD] 파이프라인 v3 완료"
git push origin main
```

---

## 전체 체크리스트

```
환경
[ ] conda 환경 생성·패키지 설치 완료
[ ] AWS 자격증명 확인 (Account 666803869796)
[ ] GitHub 저장소 클론 완료
[ ] AWS 태그 설정 확인

데이터
[ ] curated_date/ 필수 데이터 확인 (glue/ 미접근)
[ ] 업무폴더로 복사 완료 (glue/ 제외)
[ ] GDSC 버전 선택 및 README 명시
[ ] LINCS 처리 방식 결정 및 명시

FE + 매칭 품질
[ ] FE 실행 완료
[ ] 매칭 품질 검증 완료 (SMILES·Fingerprint·등급·교차·충돌·Tanimoto·Scaffold)
[ ] 품질 미달 건 처리 완료
[ ] METABRIC에 TCGA fit transform만 적용 확인

Feature Selection
[ ] Low variance → Correlation → Importance 순서 적용
[ ] features_slim.parquet 생성
[ ] METABRIC 동일 컬럼 적용 확인
[ ] 원본 미수정 확인

모델
[ ] 15개 모델 학습 완료
[ ] 6단계 평가 완료 (앙상블 통과 모델)
[ ] 32개 지표 기록
[ ] slim vs 원본 비교 완료
[ ] GraphSAGE·GAT drug-split 적용 확인

앙상블
[ ] 앙상블 Spearman > 개별 Best 모델 확인
[ ] Top 30 추출 완료
[ ] 약물 랭킹 지표 기록

METABRIC
[ ] A+B+C 검증 완료·지표 기록
[ ] Top 15 선별 완료

ADMET + KG
[ ] ADMET 3단계 필터링 완료
[ ] CYP3A4 분리 모델 적용 확인
[ ] KG/API 자동 검증 완료
[ ] 약물별 근거 보고서 생성

결과
[ ] S3 업로드 완료
[ ] 대시보드 GitHub push 완료
[ ] .aws/credentials Git 커밋 안 됨 확인
[ ] README에 커스터마이징 사항 명시
```

---

## 주의사항 요약

```
❌ curated_date/ 수정·삭제 금지
❌ curated_date/glue/ 접근 금지
❌ METABRIC으로 fit 금지 (transform만)
❌ METABRIC에서 별도 Feature Selection 금지 (leakage)
❌ GraphSAGE·GAT sample-split 금지
❌ .aws/credentials Git 커밋 금지
❌ 팀4 tmp_data 파일 직접 복사 금지
❌ features.parquet 원본 수정 금지
⚠️ Proxy 데이터 필요 시 팀장 확인 필수
⚠️ ADMET 외부 DB 추가 시 반드시 명시
⚠️ 커스터마이징 사항은 README·대시보드에 기록
⚠️ 매칭 품질 미달 건 발견 시 재매칭 또는 NA 처리
```

---

## 문의

궁금한 점은 담당자(say2-4team)에게 문의하거나 GitHub Issues를 활용하세요.

- **메인 대시보드:** https://skkuaws0215.github.io/20260408_pre_project_biso_myprotocol/dashboard.html
- **GitHub:** https://github.com/skkuaws0215/20260408_pre_project_biso_myprotocol.git
- **KG API Swagger:** http://localhost:8000/docs (로컬 실행 시)
