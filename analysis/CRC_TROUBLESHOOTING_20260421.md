# CRC 파이프라인 트러블슈팅 정리 (2026-04-21)

## 범위
- 통합 실행: `20260418_crc_v1`
- 분할 실행: `20260420_crc_split_v2`
- 관련 대시보드: `colon_pipeline_dashboard.html`, `crc_results_dashboard.html`, `crc_results_dashboard_split.html`

## 1) 한글 깨짐 이슈

### 증상
- 대시보드/문서에서 한글이 깨져 보임.

### 원인
- 파일 인코딩(BOM/UTF-8)과 브라우저/뷰어 해석 차이.
- 한글 폰트 fallback 미흡.

### 조치
- HTML에 `meta charset="UTF-8"` 명시.
- 웹폰트와 로컬 fallback 폰트 스택 보강.
- 공유용 문서는 UTF-8 기준으로 재저장.

### 결과
- 대시보드 기준 한글 표시 정상화.

---

## 2) Top30에 약물명이 아닌 Drug ID가 노출

### 증상
- 결과 표에서 약물명 대신 `drug_id`가 중심으로 보임.

### 원인
- 모델 출력은 ID 중심이고, 이름/타깃/경로 정보는 다른 산출물(step6/메타)에 분산.

### 조치
- `build_colon_dashboard_data.ps1`에서 `drug_id -> drug_name/target/pathway` 매핑 보강.
- 매핑 실패 시 fallback 라벨을 표시해 원인 추적 가능하게 처리.

### 결과
- 대시보드에서 사람이 읽을 수 있는 약물명 중심으로 개선.

---

## 3) `target_expr_mean` 값(예: 0.15) 해석 혼선

### 증상
- "타깃 발현 평균 0.15가 무엇을 뜻하는지" 혼선 발생.

### 원인
- 지표 정의가 UI에서 충분히 설명되지 않음.

### 조치
- 대시보드 설명 문구 추가:
  - pair 데이터 기준 타깃 유전자 발현(정규화 스케일)의 평균값임을 명시.
  - 값이 낮다고 자동으로 "무효"가 아니라, 다른 점수와 함께 해석해야 함을 명시.

### 결과
- 지표의 의미와 해석 기준 명확화.

---

## 4) SMILES 누락 이슈 (핵심)

### 증상
- CRC 결과에서 SMILES 누락이 상대적으로 많이 관측됨.
- 예: `missing_smiles_rows = 52`

### 원인
1. 원본 카탈로그(`drug_features_catalog`) 자체에 `canonical_smiles`가 비어있는 약물이 존재.
2. 기존 매칭이 이름 기반에 치우쳐 별칭/표기 차이에서 누락이 발생.

### 자동 백필(Backfill) 추가 내용
- 파일: `nextflow/scripts/prepare_fe_inputs.py`
- 백필 순서:
  1. `drug_id` exact 매칭 우선
  2. 실패 시 정규화된 약물명(`drug_name_norm`)으로 fallback
  3. 후보가 여러 개인 경우 null이 아닌 값 우선 선택
- QC 확장:
  - `smiles_matched_by_drug_id`
  - `smiles_backfilled_by_name`
  - `smiles_unresolved_after_backfill`
  - `smiles_backfill_policy`

### 결과
- 단순 표기 불일치로 인한 누락률 감소.
- 원천 데이터 자체 결측 케이스는 별도 큐레이션 대상으로 분리 가능.

---

## 5) 분할 실행 중 실패/지연 포인트

### 증상
- 분할 실행에서 일부 단계 중단 또는 후속 결과 누락.

### 원인
- 리소스 부족(`bad allocation`) 및 중간 산출물 미생성으로 step6/7 연쇄 영향.
- RDKit 비활성 환경에서 구조 계산 경로 제한.

### 조치
- 실행 순서 재정렬 및 재실행 포인트(`--start-at`) 명확화.
- 생성물 존재 여부 체크 후 다음 단계 진행하도록 운영 절차 보완.

### 결과
- 재실행 시 복구 속도 및 안정성 개선.

---

## 6) Git/배포 과정 이슈

### 증상
- push 실패(권한/인증/403), 인덱스 잠금 이슈.

### 원인
- 인증 토큰/자격증명 불일치, 잠금 파일 충돌.

### 조치
- 자격증명 재설정 후 재인증.
- 필요한 파일만 분리 스테이징/커밋하여 충돌 범위 축소.

### 결과
- 대시보드/문서 공유를 위한 배포 경로 정상화.

---

## 재발 방지 체크리스트
- 신규 run 종료 직후 `missing_smiles_rows`와 backfill 지표를 함께 확인.
- 대시보드 생성 시 `drug_id` 단독 노출 비율 점검.
- 인코딩/폰트 확인 후 공유용 HTML 최종본 확정.
- Git 커밋은 기능 단위로 분리해 회귀 추적 가능하게 유지.
