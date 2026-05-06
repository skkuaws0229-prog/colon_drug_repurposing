ALTER TABLE model_metric
ADD COLUMN IF NOT EXISTS phase TEXT,
ADD COLUMN IF NOT EXISTS family TEXT,
ADD COLUMN IF NOT EXISTS source_model_dir TEXT;

ALTER TABLE model_metric_detailed
ADD COLUMN IF NOT EXISTS phase TEXT,
ADD COLUMN IF NOT EXISTS family TEXT,
ADD COLUMN IF NOT EXISTS source_model_dir TEXT;

DELETE FROM model_metric
WHERE disease='BRCA'
  AND run_id='BRCA_RELEASE_V1';

DELETE FROM model_metric_detailed
WHERE disease='BRCA'
  AND run_id='BRCA_RELEASE_V1';

ALTER TABLE model_metric
DROP CONSTRAINT IF EXISTS uq_model_metric;

DROP INDEX IF EXISTS uq_model_metric_v2;

CREATE UNIQUE INDEX IF NOT EXISTS uq_model_metric_v2
ON model_metric (
  disease,
  run_id,
  source_s3_uri,
  COALESCE(phase, ''),
  COALESCE(family, ''),
  COALESCE(model, ''),
  COALESCE(metric, ''),
  COALESCE(source_model_dir, '')
);
