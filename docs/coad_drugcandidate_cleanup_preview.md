# COAD DrugCandidate Cleanup Preview (Live EC2, Read-only)

- generated_at: 2026-05-19T19:26:49.971804+00:00
- neo4j_status: ok
- data_source: live_ec2
- write/delete executed: false

- delete_candidate_count: 15
- normal_candidate_count_preserved: 30
- normal_candidate_in_delete_scope: 0

## Contaminated drug_id
- CatBoost
- CrossAttention
- ExtraTrees
- FTTransformer
- FlatMLP
- GAT
- GraphSAGE
- LightGBM
- LightGBM_DART
- RandomForest
- ResidualMLP
- TabNet
- TabTransformer
- WideDeep
- XGBoost

## Relationship types
- CANDIDATE_FOR: 15
- HAS_CANDIDATE_SCORE: 15

## Connected labels
- CandidateScore: 15
- Disease: 15

## Target nodes (degree)
- CatBoost: degree=2 key=id:CatBoost
- CrossAttention: degree=2 key=id:CrossAttention
- ExtraTrees: degree=2 key=id:ExtraTrees
- FTTransformer: degree=2 key=id:FTTransformer
- FlatMLP: degree=2 key=id:FlatMLP
- GAT: degree=2 key=id:GAT
- GraphSAGE: degree=2 key=id:GraphSAGE
- LightGBM: degree=2 key=id:LightGBM
- LightGBM_DART: degree=2 key=id:LightGBM_DART
- RandomForest: degree=2 key=id:RandomForest
- ResidualMLP: degree=2 key=id:ResidualMLP
- TabNet: degree=2 key=id:TabNet
- TabTransformer: degree=2 key=id:TabTransformer
- WideDeep: degree=2 key=id:WideDeep
- XGBoost: degree=2 key=id:XGBoost

## Cleanup Cypher Preview (DO NOT EXECUTE)
```cypher
// PREVIEW ONLY - DO NOT EXECUTE WITHOUT APPROVAL
MATCH (n:DrugCandidate)-[:CANDIDATE_FOR]->(:Disease {code:'COAD'})
WHERE n.drug_name IS NULL
  AND n.drug_name_norm IS NULL
  AND n.drug_id IN ['CatBoost','CrossAttention','ExtraTrees','FTTransformer','FlatMLP','GAT','GraphSAGE','LightGBM','LightGBM_DART','RandomForest','ResidualMLP','TabNet','TabTransformer','WideDeep','XGBoost']
WITH n
MATCH (n)-[r]-()
RETURN count(DISTINCT n) AS target_nodes, count(r) AS target_relationships;
```

## Verification Queries
```cypher
MATCH (n:DrugCandidate)-[:CANDIDATE_FOR]->(:Disease {code:'COAD'}) RETURN count(n) AS total_drug_candidates, count(CASE WHEN n.drug_name IS NULL AND n.drug_name_norm IS NULL THEN 1 END) AS contaminated_candidates;
```
```cypher
MATCH (n:DrugCandidate)-[:CANDIDATE_FOR]->(:Disease {code:'COAD'}) WHERE n.drug_name IS NULL AND n.drug_name_norm IS NULL AND n.drug_id IN ['CatBoost','CrossAttention','ExtraTrees','FTTransformer','FlatMLP','GAT','GraphSAGE','LightGBM','LightGBM_DART','RandomForest','ResidualMLP','TabNet','TabTransformer','WideDeep','XGBoost'] RETURN n.drug_id AS contaminated_drug_id ORDER BY contaminated_drug_id;
```
```cypher
MATCH (n:DrugCandidate)-[:CANDIDATE_FOR]->(:Disease {code:'COAD'}) WHERE n.drug_name IS NOT NULL OR n.drug_name_norm IS NOT NULL RETURN count(n) AS normal_candidate_count;
```
```cypher
MATCH (n:DrugCandidate)-[:CANDIDATE_FOR]->(:Disease {code:'COAD'}) WHERE n.drug_name IS NULL AND n.drug_name_norm IS NULL AND n.drug_id IN ['CatBoost','CrossAttention','ExtraTrees','FTTransformer','FlatMLP','GAT','GraphSAGE','LightGBM','LightGBM_DART','RandomForest','ResidualMLP','TabNet','TabTransformer','WideDeep','XGBoost'] MATCH (n)-[r]-() RETURN type(r) AS rel_type, count(*) AS rel_count ORDER BY rel_count DESC;
```

## Risk Notes
- none

## Execution Notice
- This is preview only. No DELETE/DETACH DELETE/MERGE/CREATE/SET executed.
