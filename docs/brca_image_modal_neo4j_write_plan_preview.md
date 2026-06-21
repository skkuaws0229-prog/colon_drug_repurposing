# BRCA Image Modal Neo4j Write-Plan Preview (Dry-Run)

- project_root: `C:\work\drug-project`
- disease_code: BRCA
- source_table: image_modal_asset
- target_graph: Neo4j
- execute_neo4j: false
- candidate_count: 3
- planned_node_count: 4
- planned_relationship_count: 3
- overall_status: PASS

## Planned Relationships
- BRCA - HAS_IMAGE_MODAL -> cluster_kaplan_meier_os.png
- BRCA - HAS_IMAGE_MODAL -> kaplan_meier_os.png
- BRCA - HAS_IMAGE_MODAL -> pca_plot.png

## Cypher Template
```cypher
MERGE (d:Disease {code: $disease_code})
ON CREATE SET
  d.name = $disease_code,
  d.created_by = 'image_modal_loader'

MERGE (img:ImageModalAsset {s3_uri: $s3_uri})
SET
  img.file_name = $file_name,
  img.file_ext = $file_ext,
  img.inferred_asset_type = $inferred_asset_type,
  img.modality = 'image',
  img.size_bytes = $size_bytes,
  img.load_status = $load_status,
  img.source = 'postgres.image_modal_asset',
  img.updated_at = datetime()

MERGE (d)-[:HAS_IMAGE_MODAL]->(img)
```

## Guardrail Confirmation
- Neo4j write was not performed.
- PostgreSQL write was not performed.
- PostgreSQL was read only.
- S3 object download was not performed.
- Image binary was not processed.
- Agentic AI image interpretation was not performed.
