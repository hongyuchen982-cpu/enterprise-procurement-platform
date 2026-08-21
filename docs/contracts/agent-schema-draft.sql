-- Member B agent persistence draft.
-- Member A owns Alembic integration; this file is the handoff source for migration review.

CREATE TABLE b_agent_tasks (
  task_id CHAR(36) NOT NULL,
  agent_type VARCHAR(80) NOT NULL,
  org_id CHAR(36) NOT NULL,
  requested_by CHAR(36) NOT NULL,
  goal TEXT NOT NULL,
  subject_refs JSON NOT NULL,
  status VARCHAR(32) NOT NULL,
  trace_id CHAR(36) NOT NULL,
  error_code VARCHAR(80) NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  PRIMARY KEY (task_id),
  INDEX ix_b_agent_tasks_org_status (org_id, status),
  INDEX ix_b_agent_tasks_status_updated (status, updated_at),
  INDEX ix_b_agent_tasks_trace (trace_id)
);

CREATE TABLE b_agent_task_events (
  event_id CHAR(36) NOT NULL,
  task_id CHAR(36) NOT NULL,
  event_type VARCHAR(80) NOT NULL,
  from_status VARCHAR(32) NULL,
  to_status VARCHAR(32) NOT NULL,
  message TEXT NOT NULL,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (event_id),
  CONSTRAINT fk_b_agent_task_events_task
    FOREIGN KEY (task_id) REFERENCES b_agent_tasks (task_id),
  INDEX ix_b_agent_task_events_task_created (task_id, created_at),
  INDEX ix_b_agent_task_events_type_created (event_type, created_at)
);

CREATE TABLE b_agent_confirmations (
  confirmation_id CHAR(36) NOT NULL,
  task_id CHAR(36) NOT NULL,
  tool_call_id CHAR(36) NOT NULL,
  risk_level VARCHAR(16) NOT NULL,
  proposed_action TEXT NOT NULL,
  target_refs JSON NOT NULL,
  target_versions JSON NOT NULL,
  input_digest VARCHAR(128) NOT NULL,
  required_permission VARCHAR(120) NOT NULL,
  status VARCHAR(32) NOT NULL,
  expires_at DATETIME(6) NOT NULL,
  confirmed_by CHAR(36) NULL,
  confirmed_at DATETIME(6) NULL,
  rejection_reason TEXT NULL,
  PRIMARY KEY (confirmation_id),
  CONSTRAINT fk_b_agent_confirmations_task
    FOREIGN KEY (task_id) REFERENCES b_agent_tasks (task_id),
  INDEX ix_b_agent_confirmations_status_expires (status, expires_at),
  INDEX ix_b_agent_confirmations_task_status (task_id, status)
);
