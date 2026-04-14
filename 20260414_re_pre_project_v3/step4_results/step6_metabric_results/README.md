
# Step 6 METABRIC 외부 검증

## 필요한 데이터

1. **METABRIC Expression Data** (`metabric_expression.parquet`)
   - Gene expression matrix (genes × patients)
   - Source: cBioPortal METABRIC study

2. **METABRIC Clinical Data** (`metabric_clinical.parquet`)
   - Columns: patient_id, OS_months, OS_status, ...

3. **Drug Annotations** (`../drug_annotations.parquet`)
   - Drug ID, name, targets, MOA, etc.

## 실행 방법

```bash
python step6_metabric_comprehensive.py
```

## 출력 파일

- `method_a_results.json` - IC50 proxy 예측 결과
- `method_b_survival.json` - Survival analysis 결과
- `method_c_graphsage.json` - GraphSAGE P@20 결과
- `catboost_top15.csv` - CatBoost Top 15 약물
- `ensemble_a_top15.csv` - Ensemble A Top 15 약물
- `drug_categories.csv` - 약물 카테고리 분류
