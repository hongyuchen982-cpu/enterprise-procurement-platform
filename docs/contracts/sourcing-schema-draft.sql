-- Member B sourcing persistence draft.
-- Member A owns Alembic integration; this file is the handoff source for migration review.

CREATE TABLE b_sourcing_projects (
  sourcing_project_id CHAR(36) NOT NULL,
  org_id CHAR(36) NOT NULL,
  procurement_request_id CHAR(36) NOT NULL,
  procurement_request_version INT NOT NULL,
  title VARCHAR(200) NOT NULL,
  category_id CHAR(36) NOT NULL,
  candidate_supplier_ids JSON NOT NULL,
  created_by CHAR(36) NOT NULL,
  status VARCHAR(32) NOT NULL,
  version INT NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  cancellation_reason TEXT NULL,
  PRIMARY KEY (sourcing_project_id),
  INDEX ix_b_sourcing_projects_org_status (org_id, status),
  INDEX ix_b_sourcing_projects_status_updated (status, updated_at),
  INDEX ix_b_sourcing_projects_procurement_request (
    procurement_request_id,
    procurement_request_version
  )
);
