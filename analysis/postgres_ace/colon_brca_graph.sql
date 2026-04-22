\set ON_ERROR_STOP on

-- Colon vs BRCA graph materialization pack for PostgreSQL (ACE workflow)
-- Prerequisite:
--   psql "$POSTGRES_DSN" -f analysis/postgres_ace/colon_brca_relationship.sql
-- Usage:
--   psql "$POSTGRES_DSN" -f analysis/postgres_ace/colon_brca_graph.sql

CREATE SCHEMA IF NOT EXISTS ace;

DO $$
BEGIN
    IF to_regclass('ace.repurposing_result') IS NULL THEN
        RAISE EXCEPTION 'Missing table ace.repurposing_result. Run analysis/postgres_ace/colon_brca_relationship.sql first.';
    END IF;
END
$$;

DROP TABLE IF EXISTS ace.graph_edge CASCADE;
DROP TABLE IF EXISTS ace.graph_node CASCADE;

CREATE TABLE ace.graph_node (
    node_id bigserial PRIMARY KEY,
    node_key text NOT NULL UNIQUE,
    node_type text NOT NULL CHECK (node_type IN ('disease', 'drug', 'pathway', 'target')),
    label text NOT NULL,
    attrs jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ace.graph_edge (
    edge_id bigserial PRIMARY KEY,
    src_node_id bigint NOT NULL REFERENCES ace.graph_node(node_id) ON DELETE CASCADE,
    dst_node_id bigint NOT NULL REFERENCES ace.graph_node(node_id) ON DELETE CASCADE,
    edge_type text NOT NULL CHECK (
        edge_type IN ('has_candidate', 'in_pathway', 'targets', 'shared_candidate')
    ),
    weight double precision,
    attrs jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (src_node_id, dst_node_id, edge_type)
);

CREATE INDEX idx_graph_node_type ON ace.graph_node (node_type);
CREATE INDEX idx_graph_edge_src ON ace.graph_edge (src_node_id);
CREATE INDEX idx_graph_edge_dst ON ace.graph_edge (dst_node_id);
CREATE INDEX idx_graph_edge_type ON ace.graph_edge (edge_type);

WITH disease_nodes AS (
    SELECT DISTINCT disease
    FROM ace.repurposing_result
    WHERE disease IN ('colon', 'brca')
)
INSERT INTO ace.graph_node (node_key, node_type, label, attrs)
SELECT
    'disease:' || disease AS node_key,
    'disease' AS node_type,
    upper(disease) AS label,
    jsonb_build_object('disease', disease) AS attrs
FROM disease_nodes;

WITH best_drug AS (
    SELECT
        r.*,
        row_number() OVER (
            PARTITION BY r.disease, r.drug_name_norm
            ORDER BY r.rank_in_list NULLS LAST, r.result_id
        ) AS rn
    FROM ace.repurposing_result r
    WHERE coalesce(r.drug_name_norm, '') <> ''
)
INSERT INTO ace.graph_node (node_key, node_type, label, attrs)
SELECT
    'drug:' || disease || ':' || drug_name_norm AS node_key,
    'drug' AS node_type,
    coalesce(nullif(drug_name, ''), drug_name_norm) AS label,
    jsonb_build_object(
        'disease', disease,
        'drug_name_norm', drug_name_norm,
        'drug_id', drug_id,
        'rank_in_list', rank_in_list,
        'combined_score', combined_score,
        'category', category,
        'run_tag', run_tag
    ) AS attrs
FROM best_drug
WHERE rn = 1;

WITH pathway_nodes AS (
    SELECT DISTINCT trim(pathway) AS pathway
    FROM ace.repurposing_result
    WHERE coalesce(trim(pathway), '') <> ''
)
INSERT INTO ace.graph_node (node_key, node_type, label, attrs)
SELECT
    'pathway:' || regexp_replace(lower(pathway), '[^a-z0-9]+', '_', 'g') AS node_key,
    'pathway' AS node_type,
    pathway AS label,
    jsonb_build_object('pathway', pathway) AS attrs
FROM pathway_nodes;

WITH raw_target AS (
    SELECT DISTINCT trim(token) AS target_token
    FROM ace.repurposing_result r
    CROSS JOIN LATERAL regexp_split_to_table(coalesce(r.target, ''), '\s*,\s*') AS token
    WHERE trim(token) <> ''
),
norm_target AS (
    SELECT
        target_token,
        regexp_replace(lower(target_token), '[^a-z0-9]+', '_', 'g') AS target_norm
    FROM raw_target
)
INSERT INTO ace.graph_node (node_key, node_type, label, attrs)
SELECT
    'target:' || target_norm AS node_key,
    'target' AS node_type,
    target_token AS label,
    jsonb_build_object('target_norm', target_norm) AS attrs
FROM norm_target;

WITH disease_drug AS (
    SELECT
        d.node_id AS disease_id,
        g.node_id AS drug_id,
        (g.attrs->>'combined_score')::double precision AS combined_score,
        g.attrs AS drug_attrs
    FROM ace.graph_node d
    JOIN ace.graph_node g
      ON g.node_type = 'drug'
     AND d.node_type = 'disease'
     AND g.attrs->>'disease' = d.attrs->>'disease'
)
INSERT INTO ace.graph_edge (src_node_id, dst_node_id, edge_type, weight, attrs)
SELECT
    disease_id AS src_node_id,
    drug_id AS dst_node_id,
    'has_candidate' AS edge_type,
    combined_score AS weight,
    jsonb_build_object('drug_attrs', drug_attrs) AS attrs
FROM disease_drug;

WITH rel AS (
    SELECT DISTINCT
        'drug:' || r.disease || ':' || r.drug_name_norm AS drug_key,
        'pathway:' || regexp_replace(lower(trim(r.pathway)), '[^a-z0-9]+', '_', 'g') AS pathway_key
    FROM ace.repurposing_result r
    WHERE coalesce(r.drug_name_norm, '') <> ''
      AND coalesce(trim(r.pathway), '') <> ''
)
INSERT INTO ace.graph_edge (src_node_id, dst_node_id, edge_type, weight, attrs)
SELECT
    gd.node_id AS src_node_id,
    gp.node_id AS dst_node_id,
    'in_pathway' AS edge_type,
    NULL::double precision AS weight,
    '{}'::jsonb AS attrs
FROM rel
JOIN ace.graph_node gd ON gd.node_key = rel.drug_key
JOIN ace.graph_node gp ON gp.node_key = rel.pathway_key;

WITH target_rel AS (
    SELECT DISTINCT
        'drug:' || r.disease || ':' || r.drug_name_norm AS drug_key,
        'target:' || regexp_replace(lower(trim(token)), '[^a-z0-9]+', '_', 'g') AS target_key
    FROM ace.repurposing_result r
    CROSS JOIN LATERAL regexp_split_to_table(coalesce(r.target, ''), '\s*,\s*') AS token
    WHERE coalesce(r.drug_name_norm, '') <> ''
      AND trim(token) <> ''
)
INSERT INTO ace.graph_edge (src_node_id, dst_node_id, edge_type, weight, attrs)
SELECT
    gd.node_id AS src_node_id,
    gt.node_id AS dst_node_id,
    'targets' AS edge_type,
    NULL::double precision AS weight,
    '{}'::jsonb AS attrs
FROM target_rel
JOIN ace.graph_node gd ON gd.node_key = target_rel.drug_key
JOIN ace.graph_node gt ON gt.node_key = target_rel.target_key;

WITH overlap AS (
    SELECT
        c.node_id AS colon_drug_node_id,
        b.node_id AS brca_drug_node_id,
        c.attrs->>'drug_name_norm' AS drug_name_norm,
        c.label AS colon_drug_name,
        b.label AS brca_drug_name
    FROM ace.graph_node c
    JOIN ace.graph_node b
      ON c.node_type = 'drug'
     AND b.node_type = 'drug'
     AND c.attrs->>'disease' = 'colon'
     AND b.attrs->>'disease' = 'brca'
     AND c.attrs->>'drug_name_norm' = b.attrs->>'drug_name_norm'
)
INSERT INTO ace.graph_edge (src_node_id, dst_node_id, edge_type, weight, attrs)
SELECT
    colon_drug_node_id AS src_node_id,
    brca_drug_node_id AS dst_node_id,
    'shared_candidate' AS edge_type,
    1.0 AS weight,
    jsonb_build_object(
        'drug_name_norm', drug_name_norm,
        'colon_drug_name', colon_drug_name,
        'brca_drug_name', brca_drug_name
    ) AS attrs
FROM overlap;

CREATE OR REPLACE VIEW ace.v_graph_node_counts AS
SELECT
    node_type,
    COUNT(*) AS node_count
FROM ace.graph_node
GROUP BY node_type
ORDER BY node_type;

CREATE OR REPLACE VIEW ace.v_graph_edge_counts AS
SELECT
    edge_type,
    COUNT(*) AS edge_count
FROM ace.graph_edge
GROUP BY edge_type
ORDER BY edge_type;

CREATE OR REPLACE VIEW ace.v_graph_top_degree AS
WITH e AS (
    SELECT src_node_id AS node_id FROM ace.graph_edge
    UNION ALL
    SELECT dst_node_id AS node_id FROM ace.graph_edge
)
SELECT
    n.node_key,
    n.node_type,
    n.label,
    COUNT(*) AS degree
FROM e
JOIN ace.graph_node n ON n.node_id = e.node_id
GROUP BY n.node_key, n.node_type, n.label
ORDER BY degree DESC, n.node_key;

-- Quick query checklist
-- 1) Node counts:
--    SELECT * FROM ace.v_graph_node_counts;
-- 2) Edge counts:
--    SELECT * FROM ace.v_graph_edge_counts;
-- 3) Highest-degree nodes:
--    SELECT * FROM ace.v_graph_top_degree LIMIT 20;
-- 4) Colon -> Drug -> Pathway:
--    SELECT d.label AS disease, dr.label AS drug, p.label AS pathway
--    FROM ace.graph_edge e1
--    JOIN ace.graph_node d ON d.node_id = e1.src_node_id AND d.node_type = 'disease'
--    JOIN ace.graph_node dr ON dr.node_id = e1.dst_node_id AND dr.node_type = 'drug'
--    JOIN ace.graph_edge e2 ON e2.src_node_id = dr.node_id AND e2.edge_type = 'in_pathway'
--    JOIN ace.graph_node p ON p.node_id = e2.dst_node_id AND p.node_type = 'pathway'
--    WHERE d.attrs->>'disease' = 'colon'
--    ORDER BY dr.label, p.label;
