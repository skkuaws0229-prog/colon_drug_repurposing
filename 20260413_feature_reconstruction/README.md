# Feature Reconstruction (20260413)

## 배경
- GroupKFold baseline: Spearman 0.4964
- Feature selection (low variance 72% 제거) 효과 없음
- 결론: feature 수가 아닌 표현 방식 문제

## 전략 전환
- ❌ Feature selection
- ✅ Feature aggregation / representation

## 실행 계획
- Step 1. CRISPR → Pathway aggregation (MSigDB Hallmark 50)
- Step 2. Target-based feature 추가
- Step 3. PCA 보조 실험 (optional)

## 목표
- 현재: Spearman ~0.49
- 목표: Spearman 0.60~0.70

## 작업 로그
- 20260413: 폴더 생성 + 전략 확정
