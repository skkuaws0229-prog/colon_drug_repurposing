\set ON_ERROR_STOP on

-- Colon vs BRCA repurposing relationship analysis pack for PostgreSQL (ACE workflow)
-- Usage (from repository root):
--   psql "$POSTGRES_DSN" -f analysis/postgres_ace/colon_brca_relationship.sql

CREATE SCHEMA IF NOT EXISTS ace;

DROP TABLE IF EXISTS ace.repurposing_result CASCADE;
CREATE TABLE ace.repurposing_result (
    result_id bigserial PRIMARY KEY,
    disease text NOT NULL CHECK (disease IN ('colon', 'brca')),
    run_tag text NOT NULL,
    source_file text NOT NULL,
    rank_in_list integer,
    drug_id text,
    drug_name text NOT NULL,
    drug_name_norm text GENERATED ALWAYS AS (
        regexp_replace(lower(coalesce(drug_name, '')), '[^a-z0-9]+', '', 'g')
    ) STORED,
    target text,
    pathway text,
    category text,
    efficacy_score double precision,
    safety_score double precision,
    combined_score double precision,
    flags text,
    extra jsonb NOT NULL DEFAULT '{}'::jsonb,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_repurposing_result_disease ON ace.repurposing_result (disease);
CREATE INDEX idx_repurposing_result_drug_norm ON ace.repurposing_result (drug_name_norm);
CREATE INDEX idx_repurposing_result_pathway ON ace.repurposing_result (pathway);

DROP TABLE IF EXISTS ace.stage_colon;
CREATE TEMP TABLE ace.stage_colon (
    final_rank text,
    drug_id text,
    drug_name text,
    target text,
    pathway text,
    pred_ic50 text,
    sensitivity_rate text,
    safety_score text,
    category text,
    flags text,
    combined_score text,
    n_assays_tested text
);

\copy ace.stage_colon FROM 'models/admet_results/final_drug_candidates.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

INSERT INTO ace.repurposing_result (
    disease,
    run_tag,
    source_file,
    rank_in_list,
    drug_id,
    drug_name,
    target,
    pathway,
    category,
    efficacy_score,
    safety_score,
    combined_score,
    flags,
    extra
)
SELECT
    'colon' AS disease,
    '20260418_crc_v1' AS run_tag,
    'models/admet_results/final_drug_candidates.csv' AS source_file,
    NULLIF(final_rank, '')::integer AS rank_in_list,
    NULLIF(drug_id, '') AS drug_id,
    drug_name,
    NULLIF(target, '') AS target,
    NULLIF(pathway, '') AS pathway,
    NULLIF(category, '') AS category,
    CASE
        WHEN pred_ic50 ~ '^-?[0-9]+(\.[0-9]+)?([eE]-?[0-9]+)?$' THEN pred_ic50::double precision
        ELSE NULL
    END AS efficacy_score,
    CASE
        WHEN safety_score ~ '^-?[0-9]+(\.[0-9]+)?([eE]-?[0-9]+)?$' THEN safety_score::double precision
        ELSE NULL
    END AS safety_score,
    CASE
        WHEN combined_score ~ '^-?[0-9]+(\.[0-9]+)?([eE]-?[0-9]+)?$' THEN combined_score::double precision
        ELSE NULL
    END AS combined_score,
    NULLIF(flags, '') AS flags,
    jsonb_build_object(
        'sensitivity_rate', CASE WHEN sensitivity_rate ~ '^-?[0-9]+(\.[0-9]+)?([eE]-?[0-9]+)?$' THEN sensitivity_rate::double precision END,
        'n_assays_tested', CASE WHEN n_assays_tested ~ '^[0-9]+$' THEN n_assays_tested::integer END
    ) AS extra
FROM ace.stage_colon
WHERE coalesce(drug_name, '') <> '';

DROP TABLE IF EXISTS ace.stage_brca;
CREATE TEMP TABLE ace.stage_brca (
    rank text,
    canonical_drug_id text,
    drug_name text,
    target text,
    target_matches text,
    target_score text,
    pathway text,
    subtypes text,
    category text,
    tanimoto text,
    best_fda_match text,
    survival_p text,
    survival_score text,
    clinical_score text,
    safety_score text,
    ic50_score text,
    final_score text,
    is_fda text,
    normalized_name text,
    is_fda_brca text,
    repurposing_rank text
);

\copy ace.stage_brca FROM '20260414_re_pre_project_v3/step4_results/step6_final/repurposing_top15.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

INSERT INTO ace.repurposing_result (
    disease,
    run_tag,
    source_file,
    rank_in_list,
    drug_id,
    drug_name,
    target,
    pathway,
    category,
    efficacy_score,
    safety_score,
    combined_score,
    flags,
    extra
)
SELECT
    'brca' AS disease,
    '20260414_re_pre_project_v3' AS run_tag,
    '20260414_re_pre_project_v3/step4_results/step6_final/repurposing_top15.csv' AS source_file,
    CASE
        WHEN repurposing_rank ~ '^[0-9]+$' THEN repurposing_rank::integer
        WHEN rank ~ '^[0-9]+$' THEN rank::integer
        ELSE NULL
    END AS rank_in_list,
    NULLIF(canonical_drug_id, '') AS drug_id,
    drug_name,
    NULLIF(target, '') AS target,
    NULLIF(pathway, '') AS pathway,
    CASE
        WHEN category ~* 'Category[[:space:]]*1' THEN 'Category 1'
        WHEN category ~* 'Category[[:space:]]*2' THEN 'Category 2'
        WHEN category ~* 'Category[[:space:]]*3' THEN 'Category 3'
        ELSE NULLIF(category, '')
    END AS category,
    CASE
        WHEN ic50_score ~ '^-?[0-9]+(\.[0-9]+)?([eE]-?[0-9]+)?$' THEN ic50_score::double precision
        ELSE NULL
    END AS efficacy_score,
    CASE
        WHEN safety_score ~ '^-?[0-9]+(\.[0-9]+)?([eE]-?[0-9]+)?$' THEN safety_score::double precision
        ELSE NULL
    END AS safety_score,
    CASE
        WHEN final_score ~ '^-?[0-9]+(\.[0-9]+)?([eE]-?[0-9]+)?$' THEN final_score::double precision
        ELSE NULL
    END AS combined_score,
    NULL::text AS flags,
    jsonb_build_object(
        'subtypes', NULLIF(subtypes, ''),
        'target_matches', NULLIF(target_matches, ''),
        'target_score', CASE WHEN target_score ~ '^-?[0-9]+(\.[0-9]+)?([eE]-?[0-9]+)?$' THEN target_score::double precision END,
        'tanimoto', CASE WHEN tanimoto ~ '^-?[0-9]+(\.[0-9]+)?([eE]-?[0-9]+)?$' THEN tanimoto::double precision END,
        'survival_p', CASE WHEN survival_p ~ '^-?[0-9]+(\.[0-9]+)?([eE]-?[0-9]+)?$' THEN survival_p::double precision END,
        'survival_score', CASE WHEN survival_score ~ '^-?[0-9]+(\.[0-9]+)?([eE]-?[0-9]+)?$' THEN survival_score::double precision END,
        'clinical_score', CASE WHEN clinical_score ~ '^-?[0-9]+(\.[0-9]+)?([eE]-?[0-9]+)?$' THEN clinical_score::double precision END
    ) AS extra
FROM ace.stage_brca
WHERE coalesce(drug_name, '') <> '';

CREATE OR REPLACE VIEW ace.v_repurposing_overlap_summary AS
WITH c AS (
    SELECT DISTINCT drug_name_norm FROM ace.repurposing_result WHERE disease = 'colon'
),
b AS (
    SELECT DISTINCT drug_name_norm FROM ace.repurposing_result WHERE disease = 'brca'
),
i AS (
    SELECT c.drug_name_norm FROM c INNER JOIN b ON c.drug_name_norm = b.drug_name_norm
)
SELECT
    (SELECT COUNT(*) FROM c) AS colon_unique_drugs,
    (SELECT COUNT(*) FROM b) AS brca_unique_drugs,
    (SELECT COUNT(*) FROM i) AS overlap_unique_drugs,
    (SELECT COUNT(*) FROM c) + (SELECT COUNT(*) FROM b) - (SELECT COUNT(*) FROM i) AS union_unique_drugs,
    CASE
        WHEN ((SELECT COUNT(*) FROM c) + (SELECT COUNT(*) FROM b) - (SELECT COUNT(*) FROM i)) = 0 THEN 0
        ELSE (SELECT COUNT(*) FROM i)::double precision
             / ((SELECT COUNT(*) FROM c) + (SELECT COUNT(*) FROM b) - (SELECT COUNT(*) FROM i))
    END AS jaccard_drug;

CREATE OR REPLACE VIEW ace.v_repurposing_drug_overlap AS
WITH ranked AS (
    SELECT
        *,
        row_number() OVER (
            PARTITION BY disease, drug_name_norm
            ORDER BY rank_in_list NULLS LAST, result_id
        ) AS rn
    FROM ace.repurposing_result
),
colon AS (
    SELECT * FROM ranked WHERE disease = 'colon' AND rn = 1
),
brca AS (
    SELECT * FROM ranked WHERE disease = 'brca' AND rn = 1
)
SELECT
    colon.drug_name_norm,
    colon.drug_name AS colon_drug_name,
    brca.drug_name AS brca_drug_name,
    colon.rank_in_list AS colon_rank,
    brca.rank_in_list AS brca_rank,
    colon.pathway AS colon_pathway,
    brca.pathway AS brca_pathway,
    colon.target AS colon_target,
    brca.target AS brca_target,
    colon.combined_score AS colon_combined_score,
    brca.combined_score AS brca_combined_score
FROM colon
INNER JOIN brca ON colon.drug_name_norm = brca.drug_name_norm
ORDER BY colon.rank_in_list NULLS LAST;

CREATE OR REPLACE VIEW ace.v_repurposing_pathway_overlap AS
SELECT
    pathway,
    COUNT(*) FILTER (WHERE disease = 'colon') AS colon_rows,
    COUNT(*) FILTER (WHERE disease = 'brca') AS brca_rows,
    COUNT(DISTINCT drug_name_norm) FILTER (WHERE disease = 'colon') AS colon_unique_drugs,
    COUNT(DISTINCT drug_name_norm) FILTER (WHERE disease = 'brca') AS brca_unique_drugs
FROM ace.repurposing_result
WHERE coalesce(pathway, '') <> ''
GROUP BY pathway
HAVING COUNT(*) FILTER (WHERE disease = 'colon') > 0
   AND COUNT(*) FILTER (WHERE disease = 'brca') > 0
ORDER BY (COUNT(*) FILTER (WHERE disease = 'colon')
        + COUNT(*) FILTER (WHERE disease = 'brca')) DESC,
         pathway;

CREATE OR REPLACE VIEW ace.v_repurposing_target_overlap AS
WITH tokenized AS (
    SELECT
        disease,
        drug_name_norm,
        trim(token) AS target_token
    FROM ace.repurposing_result
    CROSS JOIN LATERAL regexp_split_to_table(coalesce(target, ''), '\s*,\s*') AS token
    WHERE trim(token) <> ''
),
normed AS (
    SELECT
        disease,
        drug_name_norm,
        target_token,
        regexp_replace(lower(target_token), '[^a-z0-9]+', '', 'g') AS token_norm
    FROM tokenized
),
agg AS (
    SELECT
        token_norm,
        min(target_token) AS display_token,
        COUNT(DISTINCT drug_name_norm) FILTER (WHERE disease = 'colon') AS colon_drug_hits,
        COUNT(DISTINCT drug_name_norm) FILTER (WHERE disease = 'brca') AS brca_drug_hits
    FROM normed
    WHERE token_norm <> ''
    GROUP BY token_norm
)
SELECT
    display_token AS target_token,
    colon_drug_hits,
    brca_drug_hits
FROM agg
WHERE colon_drug_hits > 0
  AND brca_drug_hits > 0
ORDER BY (colon_drug_hits + brca_drug_hits) DESC, display_token;

CREATE OR REPLACE VIEW ace.v_repurposing_disease_unique AS
SELECT
    disease,
    drug_name,
    rank_in_list,
    pathway,
    target,
    category,
    combined_score
FROM ace.repurposing_result r
WHERE NOT EXISTS (
    SELECT 1
    FROM ace.repurposing_result o
    WHERE o.disease <> r.disease
      AND o.drug_name_norm = r.drug_name_norm
)
ORDER BY disease, rank_in_list NULLS LAST, drug_name;

-- Quick query checklist for ACE / NL2SQL review
-- 1) Summary:
--    SELECT * FROM ace.v_repurposing_overlap_summary;
-- 2) Overlapping drugs:
--    SELECT * FROM ace.v_repurposing_drug_overlap;
-- 3) Shared pathways:
--    SELECT * FROM ace.v_repurposing_pathway_overlap;
-- 4) Shared targets:
--    SELECT * FROM ace.v_repurposing_target_overlap;
-- 5) Disease-unique candidates:
--    SELECT * FROM ace.v_repurposing_disease_unique;

