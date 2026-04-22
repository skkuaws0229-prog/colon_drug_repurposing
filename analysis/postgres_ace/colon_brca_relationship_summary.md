# Colon vs BRCA Repurposing Relationship (PostgreSQL ACE)

## Sources
- Colon: `models/admet_results/final_drug_candidates.csv`
- BRCA: `20260414_re_pre_project_v3/step4_results/step6_final/repurposing_top15.csv`

## Quick Metrics
- Colon unique drugs: `13`
- BRCA unique drugs: `15`
- Overlapping drugs: `2`
- Drug-level Jaccard index: `0.0769`

## Overlapping Drug Names
- `Dactinomycin`
- `Rapamycin`

## Shared Pathways
- `Cell cycle`
- `DNA replication`
- `Mitosis`
- `Other`
- `PI3K/MTOR signaling`
- `Protein stability and degradation`

## Shared Target Tokens
- `CDK9`
- `HSP90`
- `MTORC1`
- `RNA polymerase`

## Category Snapshot
- Colon (`Approved/Candidate/Caution`): `7 / 5 / 1`
- BRCA (`Category 2 / Category 3`): `8 / 7`

## SQL Pack
Run:

```bash
psql "$POSTGRES_DSN" -f analysis/postgres_ace/colon_brca_relationship.sql
```

Then query:

```sql
SELECT * FROM ace.v_repurposing_overlap_summary;
SELECT * FROM ace.v_repurposing_drug_overlap;
SELECT * FROM ace.v_repurposing_pathway_overlap;
SELECT * FROM ace.v_repurposing_target_overlap;
SELECT * FROM ace.v_repurposing_disease_unique;
```

