-- Member B supplier persistence draft.
-- Member A owns Alembic integration; this file is the handoff source for migration review.

CREATE TABLE b_suppliers (
  supplier_id CHAR(36) NOT NULL,
  org_id CHAR(36) NOT NULL,
  legal_name VARCHAR(255) NOT NULL,
  status VARCHAR(32) NOT NULL,
  qualification_status VARCHAR(32) NOT NULL,
  category_ids JSON NOT NULL,
  risk_level VARCHAR(32) NOT NULL,
  is_frozen BOOLEAN NOT NULL DEFAULT FALSE,
  version INT NOT NULL DEFAULT 1,
  updated_at DATETIME(6) NOT NULL,
  PRIMARY KEY (supplier_id),
  INDEX ix_b_suppliers_org_risk (org_id, risk_level),
  INDEX ix_b_suppliers_org_status (org_id, status)
);

CREATE TABLE b_supplier_risk_reviews (
  review_id CHAR(36) NOT NULL,
  supplier_id CHAR(36) NOT NULL,
  conclusion VARCHAR(32) NOT NULL,
  note TEXT NOT NULL,
  reviewed_by VARCHAR(80) NOT NULL,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (review_id),
  CONSTRAINT fk_b_supplier_risk_reviews_supplier
    FOREIGN KEY (supplier_id) REFERENCES b_suppliers (supplier_id),
  INDEX ix_b_supplier_risk_reviews_supplier_created (supplier_id, created_at)
);
