-- Member B risk assessment persistence draft.
-- Member A owns Alembic integration; this file is the handoff source for migration review.

CREATE TABLE b_supplier_risk_assessments (
  assessment_id CHAR(36) NOT NULL,
  supplier_id CHAR(36) NOT NULL,
  org_id CHAR(36) NOT NULL,
  supplier_name VARCHAR(255) NOT NULL,
  score INT NOT NULL,
  risk_level VARCHAR(32) NOT NULL,
  recommended_action VARCHAR(32) NOT NULL,
  factors JSON NOT NULL,
  summary TEXT NOT NULL,
  assessed_by VARCHAR(80) NOT NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  PRIMARY KEY (assessment_id),
  INDEX ix_b_supplier_risk_assessments_supplier_updated (supplier_id, updated_at),
  INDEX ix_b_supplier_risk_assessments_org_score (org_id, score),
  INDEX ix_b_supplier_risk_assessments_action (recommended_action)
);
