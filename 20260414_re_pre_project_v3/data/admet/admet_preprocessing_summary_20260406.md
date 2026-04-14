# ADMET Preprocessing Summary (2026-04-06)

## What Was Done
- ADMET task별 train_val/test CSV를 개별 parquet로 변환
- Drug_ID와 Drug 문자열을 정리하고 placeholder를 NA로 통일
- Y를 numeric으로 변환
- task inventory parquet를 생성

## What Was Not Done Yet
- SMILES canonicalization
- task별 classification/regression label 해석 통일
- 약물 중복 통합
- downstream filtering or reranking feature 생성

## Main Outputs
- `admet_task_inventory_20260406.parquet`
- 각 task 디렉터리 아래 `train_val_basic_clean_20260406.parquet` / `test_basic_clean_20260406.parquet`

## Key Reminder
- 이번 단계는 task 의미를 건드리지 않고 원천 CSV를 안정적인 parquet 구조로 옮기는 기본 전처리만 수행했다.