-- Member B RAG persistence draft.
-- Member A owns Alembic integration; this file is the handoff source for migration review.
-- The rag runtime should use repositories or infrastructure adapters outside the restricted
-- rag orchestration boundary when this draft becomes a real migration.

CREATE TABLE b_knowledge_documents (
  document_id CHAR(36) NOT NULL,
  org_id CHAR(36) NOT NULL,
  title VARCHAR(200) NOT NULL,
  owner_module VARCHAR(80) NOT NULL,
  source_type VARCHAR(40) NOT NULL,
  object_key VARCHAR(500) NULL,
  content_digest CHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL,
  chunk_count INT NOT NULL DEFAULT 0,
  tags JSON NOT NULL,
  created_by CHAR(36) NOT NULL,
  indexed_at DATETIME(6) NULL,
  version INT NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  PRIMARY KEY (document_id),
  INDEX ix_b_knowledge_documents_org_status (org_id, status),
  INDEX ix_b_knowledge_documents_owner_updated (owner_module, updated_at),
  UNIQUE INDEX ux_b_knowledge_documents_org_digest (org_id, content_digest)
);

CREATE TABLE b_knowledge_chunks (
  chunk_id CHAR(36) NOT NULL,
  document_id CHAR(36) NOT NULL,
  org_id CHAR(36) NOT NULL,
  chunk_index INT NOT NULL,
  text_digest CHAR(64) NOT NULL,
  qdrant_point_id CHAR(36) NULL,
  token_count INT NOT NULL DEFAULT 0,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (chunk_id),
  CONSTRAINT fk_b_knowledge_chunks_document
    FOREIGN KEY (document_id) REFERENCES b_knowledge_documents (document_id),
  INDEX ix_b_knowledge_chunks_document_index (document_id, chunk_index),
  INDEX ix_b_knowledge_chunks_qdrant_point (qdrant_point_id)
);
