"""Initial backendV1 schema, frozen from revisions0001–0015 on2026-10-27.

Only v1-owned objects are created. Historical source revisions are archived in
alembic/archive/0001-0015_20261027.zip; this file never imports application models.
Existing databases on the retired chain need an explicit reviewed transition.
"""

import sqlalchemy as sa

from alembic import context, op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

V1_OWNED = (
    "chat_assistants",
    "chat_conversations",
    "chat_turns",
    "kb_collections",
    "kb_compilation_artifacts",
    "kb_compilation_edit_previews",
    "kb_compilation_inputs",
    "kb_compilation_review_artifacts",
    "kb_compilation_review_jobs",
    "kb_compilation_reviews",
    "kb_compilation_runs",
    "kb_compiled_documents",
    "kb_compiled_versions",
    "kb_index_chunks",
    "kb_index_inputs",
    "kb_index_runs",
    "kb_publication_decisions",
    "kb_publication_previews",
    "kb_source_revisions",
    "kb_sources",
    "kb_upload_requests",
    "model_defaults",
    "model_usage_records",
    "modelops_events",
    "ocr_processing_runs",
    "ocr_run_artifacts",
    "ocr_run_pages",
    "ocr_spelling_runs",
    "ocr_text_versions",
    "ops_actions",
    "ops_evidence_backups",
    "provider_key_audits",
    "provider_keys",
    "providers",
    "resource_lifecycle_actions",
    "resource_lifecycle_states",
    "workspace_allowed_providers",
    "workspace_events",
    "workspace_members",
    "workspace_model_defaults",
    "workspace_quotas",
    "workspaces",
)

DDL = (
    """
CREATE TABLE kb_upload_requests (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	actor_ref VARCHAR(200) NOT NULL, 
	idempotency_key VARCHAR(128) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	source_id VARCHAR(64) NOT NULL, 
	revision_id VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT kb_upload_requests_pkey PRIMARY KEY (id), 
	CONSTRAINT uq_kb_upload_idempotency UNIQUE NULLS DISTINCT (workspace_id, actor_ref, idempotency_key), 
	CONSTRAINT ck_kb_upload_request_hash CHECK (char_length(request_hash) = 64)
)
""",
    """
CREATE TABLE model_defaults (
	id VARCHAR(32) NOT NULL, 
	chat_provider_id VARCHAR(64), 
	chat_model VARCHAR(200), 
	embedding_provider_id VARCHAR(64), 
	embedding_model VARCHAR(200), 
	rerank_provider_id VARCHAR(64), 
	rerank_model VARCHAR(200), 
	ocr_provider_id VARCHAR(64), 
	ocr_model VARCHAR(200), 
	updated_by VARCHAR(200), 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT model_defaults_pkey PRIMARY KEY (id)
)
""",
    """
CREATE TABLE modelops_events (
	id VARCHAR(64) NOT NULL, 
	actor_ref VARCHAR(200) NOT NULL, 
	action VARCHAR(64) NOT NULL, 
	provider_id VARCHAR(64), 
	detail JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT modelops_events_pkey PRIMARY KEY (id)
)
""",
    """
CREATE TABLE providers (
	id VARCHAR(64) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	provider_type VARCHAR(32) NOT NULL, 
	base_url VARCHAR(1024) NOT NULL, 
	model_name VARCHAR(200) NOT NULL, 
	capabilities JSONB DEFAULT '[]'::jsonb NOT NULL, 
	is_active BOOLEAN DEFAULT true NOT NULL, 
	priority INTEGER DEFAULT 5 NOT NULL, 
	timeout_seconds INTEGER DEFAULT 30 NOT NULL, 
	extra_config JSONB DEFAULT '{}'::jsonb NOT NULL, 
	created_by VARCHAR(200), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT providers_pkey PRIMARY KEY (id), 
	CONSTRAINT providers_name_key UNIQUE NULLS DISTINCT (name), 
	CONSTRAINT ck_provider_type CHECK (provider_type IN ('openai_compatible','gemini','local','nemotron','paddleocr'))
)
""",
    """
CREATE TABLE workspaces (
	id VARCHAR(64) NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description TEXT, 
	status VARCHAR(32) DEFAULT 'active'::character varying NOT NULL, 
	created_by VARCHAR(200), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT workspaces_pkey PRIMARY KEY (id), 
	CONSTRAINT ck_workspace_status CHECK (status IN ('active','suspended'))
)
""",
    """
CREATE TABLE kb_collections (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description TEXT, 
	created_by VARCHAR(200) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT kb_collections_pkey PRIMARY KEY (id), 
	CONSTRAINT kb_collections_workspace_id_fkey FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	CONSTRAINT uq_kb_collection_name UNIQUE NULLS DISTINCT (workspace_id, name), 
	CONSTRAINT uq_kb_collection_scope UNIQUE NULLS DISTINCT (id, workspace_id)
)
""",
    """
CREATE TABLE model_usage_records (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	provider_id VARCHAR(64) NOT NULL, 
	actor_ref VARCHAR(200) NOT NULL, 
	request_id VARCHAR(128) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	capability VARCHAR(16) NOT NULL, 
	model_name VARCHAR(200) NOT NULL, 
	month_period DATE NOT NULL, 
	reserved_tokens BIGINT NOT NULL, 
	total_tokens BIGINT, 
	cost_usd NUMERIC(20, 8), 
	status VARCHAR(16) DEFAULT 'reserved'::character varying NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT model_usage_records_pkey PRIMARY KEY (id), 
	CONSTRAINT model_usage_records_provider_id_fkey FOREIGN KEY(provider_id) REFERENCES providers (id) ON DELETE RESTRICT, 
	CONSTRAINT model_usage_records_workspace_id_fkey FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT, 
	CONSTRAINT uq_model_usage_request UNIQUE NULLS DISTINCT (workspace_id, request_id), 
	CONSTRAINT ck_model_usage_cost CHECK (cost_usd IS NULL OR cost_usd >= 0), 
	CONSTRAINT ck_model_usage_status CHECK (status IN ('reserved','completed','failed','unknown')), 
	CONSTRAINT ck_model_usage_tokens CHECK (reserved_tokens > 0 AND (total_tokens IS NULL OR total_tokens >= 0))
)
""",
    """
CREATE TABLE ops_actions (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	actor_ref VARCHAR(200) NOT NULL, 
	kind VARCHAR(24) NOT NULL, 
	job_id VARCHAR(64) NOT NULL, 
	action VARCHAR(24) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	reason VARCHAR(2000) NOT NULL, 
	state_sha256 VARCHAR(64) NOT NULL, 
	preview_sha256 VARCHAR(64) NOT NULL, 
	idempotency_key VARCHAR(128), 
	request_hash VARCHAR(64), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	dispatched_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT ops_actions_pkey PRIMARY KEY (id), 
	CONSTRAINT ops_actions_workspace_id_fkey FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT, 
	CONSTRAINT uq_ops_action_request UNIQUE NULLS DISTINCT (workspace_id, actor_ref, idempotency_key), 
	CONSTRAINT ck_ops_action_status CHECK (status IN ('preview','pending','dispatched','superseded')), 
	CONSTRAINT ck_ops_action_type CHECK (action IN ('dispatch','delete_backup'))
)
""",
    """
CREATE TABLE provider_key_audits (
	id VARCHAR(64) NOT NULL, 
	provider_id VARCHAR(64) NOT NULL, 
	key_id VARCHAR(64), 
	actor_ref VARCHAR(200), 
	action VARCHAR(32) NOT NULL, 
	reason VARCHAR(512), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT provider_key_audits_pkey PRIMARY KEY (id), 
	CONSTRAINT provider_key_audits_provider_id_fkey FOREIGN KEY(provider_id) REFERENCES providers (id) ON DELETE CASCADE
)
""",
    """
CREATE TABLE provider_keys (
	id VARCHAR(64) NOT NULL, 
	provider_id VARCHAR(64) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	secret_encrypted TEXT NOT NULL, 
	masked_hint VARCHAR(16) NOT NULL, 
	status VARCHAR(32) DEFAULT 'active'::character varying NOT NULL, 
	priority INTEGER DEFAULT 5 NOT NULL, 
	lease_until TIMESTAMP WITH TIME ZONE, 
	cooldown_until TIMESTAMP WITH TIME ZONE, 
	consecutive_failures INTEGER DEFAULT 0 NOT NULL, 
	created_by VARCHAR(200), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT provider_keys_pkey PRIMARY KEY (id), 
	CONSTRAINT provider_keys_provider_id_fkey FOREIGN KEY(provider_id) REFERENCES providers (id) ON DELETE CASCADE, 
	CONSTRAINT ck_provider_key_status CHECK (status IN ('active','revoked'))
)
""",
    """
CREATE TABLE resource_lifecycle_actions (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	actor_ref VARCHAR(200) NOT NULL, 
	kind VARCHAR(24) NOT NULL, 
	resource_id VARCHAR(64) NOT NULL, 
	action VARCHAR(24) NOT NULL, 
	reason VARCHAR(2000) NOT NULL, 
	parameters JSONB NOT NULL, 
	impact JSONB NOT NULL, 
	state_sha256 VARCHAR(64) NOT NULL, 
	preview_sha256 VARCHAR(64) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	idempotency_key VARCHAR(128), 
	request_hash VARCHAR(64), 
	result JSONB, 
	error_code VARCHAR(64), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	accepted_at TIMESTAMP WITH TIME ZONE, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT resource_lifecycle_actions_pkey PRIMARY KEY (id), 
	CONSTRAINT resource_lifecycle_actions_workspace_id_fkey FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT, 
	CONSTRAINT uq_lifecycle_request UNIQUE NULLS DISTINCT (workspace_id, actor_ref, idempotency_key), 
	CONSTRAINT ck_lifecycle_action_status CHECK (status IN ('preview','pending','completed','failed'))
)
""",
    """
CREATE TABLE resource_lifecycle_states (
	workspace_id VARCHAR(64) NOT NULL, 
	kind VARCHAR(24) NOT NULL, 
	resource_id VARCHAR(64) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	revision INTEGER NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT resource_lifecycle_states_pkey PRIMARY KEY (workspace_id, kind, resource_id), 
	CONSTRAINT resource_lifecycle_states_workspace_id_fkey FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT, 
	CONSTRAINT ck_resource_lifecycle_status CHECK (status IN ('active','archived','deleted'))
)
""",
    """
CREATE TABLE workspace_allowed_providers (
	workspace_id VARCHAR(64) NOT NULL, 
	provider_id VARCHAR(64) NOT NULL, 
	is_default BOOLEAN DEFAULT false NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT workspace_allowed_providers_pkey PRIMARY KEY (workspace_id, provider_id), 
	CONSTRAINT workspace_allowed_providers_provider_id_fkey FOREIGN KEY(provider_id) REFERENCES providers (id) ON DELETE CASCADE, 
	CONSTRAINT workspace_allowed_providers_workspace_id_fkey FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
)
""",
    """
CREATE TABLE workspace_events (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	actor_ref VARCHAR(200), 
	action VARCHAR(64) NOT NULL, 
	target_type VARCHAR(64), 
	target_id VARCHAR(64), 
	detail JSONB DEFAULT '{}'::jsonb NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT workspace_events_pkey PRIMARY KEY (id), 
	CONSTRAINT workspace_events_workspace_id_fkey FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
)
""",
    """
CREATE TABLE workspace_members (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	actor_ref VARCHAR(200) NOT NULL, 
	display_name VARCHAR(255), 
	role VARCHAR(32) DEFAULT 'member'::character varying NOT NULL, 
	status VARCHAR(32) DEFAULT 'active'::character varying NOT NULL, 
	invited_by VARCHAR(200), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT workspace_members_pkey PRIMARY KEY (id), 
	CONSTRAINT workspace_members_workspace_id_fkey FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	CONSTRAINT uq_workspace_member UNIQUE NULLS DISTINCT (workspace_id, actor_ref), 
	CONSTRAINT ck_member_role CHECK (role IN ('admin','editor','reviewer','member')), 
	CONSTRAINT ck_member_status CHECK (status IN ('active','pending','revoked'))
)
""",
    """
CREATE TABLE workspace_quotas (
	workspace_id VARCHAR(64) NOT NULL, 
	month_period DATE NOT NULL, 
	monthly_token_limit BIGINT, 
	tokens_used BIGINT DEFAULT '0'::bigint NOT NULL, 
	tokens_reserved BIGINT DEFAULT '0'::bigint NOT NULL, 
	is_blocked BOOLEAN DEFAULT false NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT workspace_quotas_pkey PRIMARY KEY (workspace_id, month_period), 
	CONSTRAINT workspace_quotas_workspace_id_fkey FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT, 
	CONSTRAINT ck_quota_counters CHECK (tokens_used >= 0 AND tokens_reserved >= 0), 
	CONSTRAINT ck_quota_limit CHECK (monthly_token_limit IS NULL OR monthly_token_limit >= 0)
)
""",
    """
CREATE TABLE chat_assistants (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	description TEXT NOT NULL, 
	persona TEXT NOT NULL, 
	chat_provider_id VARCHAR(64), 
	revision INTEGER NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	top_k INTEGER NOT NULL, 
	history_turns INTEGER NOT NULL, 
	max_output_tokens INTEGER NOT NULL, 
	created_by VARCHAR(200) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT chat_assistants_pkey PRIMARY KEY (id), 
	CONSTRAINT chat_assistants_chat_provider_id_fkey FOREIGN KEY(chat_provider_id) REFERENCES providers (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_chat_assistant_collection FOREIGN KEY(collection_id, workspace_id) REFERENCES kb_collections (id, workspace_id) ON DELETE RESTRICT, 
	CONSTRAINT uq_chat_assistant_scope UNIQUE NULLS DISTINCT (id, workspace_id, collection_id), 
	CONSTRAINT ck_chat_assistant_config CHECK (revision >= 1 AND top_k BETWEEN 1 AND 20 AND history_turns BETWEEN 0 AND 10 AND max_output_tokens > 0)
)
""",
    """
CREATE TABLE kb_compilation_runs (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	generation INTEGER NOT NULL, 
	topic VARCHAR(2000) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	requested_by VARCHAR(200) NOT NULL, 
	idempotency_key VARCHAR(128) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	input_sha256 VARCHAR(64) NOT NULL, 
	provider_id VARCHAR(64) NOT NULL, 
	config JSONB NOT NULL, 
	requested_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	dispatched_at TIMESTAMP WITH TIME ZONE, 
	started_at TIMESTAMP WITH TIME ZONE, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	request_started_at TIMESTAMP WITH TIME ZONE, 
	attempt_count INTEGER NOT NULL, 
	worker_id VARCHAR(120), 
	lease_expires_at TIMESTAMP WITH TIME ZONE, 
	usage_id VARCHAR(64), 
	usage_tokens INTEGER, 
	error_code VARCHAR(64), 
	parent_run_id VARCHAR(64), 
	origin VARCHAR(16) DEFAULT 'model'::character varying NOT NULL, 
	CONSTRAINT kb_compilation_runs_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_compilation_collection FOREIGN KEY(collection_id, workspace_id) REFERENCES kb_collections (id, workspace_id) ON DELETE RESTRICT, 
	CONSTRAINT fk_compilation_parent FOREIGN KEY(parent_run_id, workspace_id, collection_id) REFERENCES kb_compilation_runs (id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT kb_compilation_runs_provider_id_fkey FOREIGN KEY(provider_id) REFERENCES providers (id) ON DELETE RESTRICT, 
	CONSTRAINT kb_compilation_runs_usage_id_fkey FOREIGN KEY(usage_id) REFERENCES model_usage_records (id) ON DELETE RESTRICT, 
	CONSTRAINT uq_compilation_generation UNIQUE NULLS DISTINCT (collection_id, generation), 
	CONSTRAINT uq_compilation_request UNIQUE NULLS DISTINCT (workspace_id, requested_by, idempotency_key), 
	CONSTRAINT uq_compilation_scope UNIQUE NULLS DISTINCT (id, workspace_id, collection_id), 
	CONSTRAINT ck_compilation_ancestry CHECK ((origin = 'model' AND parent_run_id IS NULL) OR (origin = 'user_edit' AND parent_run_id IS NOT NULL)), 
	CONSTRAINT ck_compilation_counters CHECK (generation >= 1 AND attempt_count >= 0), 
	CONSTRAINT ck_compilation_origin CHECK (origin IN ('model','user_edit')), 
	CONSTRAINT ck_compilation_status CHECK (status IN ('queued','running','completed','failed','uncertain','cancelled'))
)
""",
    """
CREATE TABLE kb_compiled_documents (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	document_key VARCHAR(120) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	change_sequence INTEGER NOT NULL, 
	created_by VARCHAR(200) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT kb_compiled_documents_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_compiled_document_collection FOREIGN KEY(collection_id, workspace_id) REFERENCES kb_collections (id, workspace_id) ON DELETE RESTRICT, 
	CONSTRAINT uq_compiled_document_key UNIQUE NULLS DISTINCT (workspace_id, collection_id, document_key), 
	CONSTRAINT uq_compiled_document_scope UNIQUE NULLS DISTINCT (id, workspace_id, collection_id), 
	CONSTRAINT ck_compiled_document_sequence CHECK (change_sequence >= 1)
)
""",
    """
CREATE TABLE kb_index_runs (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	generation INTEGER NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	provider_id VARCHAR(64) NOT NULL, 
	dimension INTEGER NOT NULL, 
	vector_collection VARCHAR(120) NOT NULL, 
	config JSONB NOT NULL, 
	input_sha256 VARCHAR(64) NOT NULL, 
	requested_by VARCHAR(200) NOT NULL, 
	idempotency_key VARCHAR(128) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	requested_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	dispatched_at TIMESTAMP WITH TIME ZONE, 
	started_at TIMESTAMP WITH TIME ZONE, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	worker_id VARCHAR(120), 
	lease_expires_at TIMESTAMP WITH TIME ZONE, 
	attempt_count INTEGER NOT NULL, 
	error_code VARCHAR(64), 
	chunks_total INTEGER NOT NULL, 
	pending_batch JSONB, 
	batch_receipts JSONB NOT NULL, 
	manifest_key VARCHAR(512), 
	manifest_sha256 VARCHAR(64), 
	CONSTRAINT kb_index_runs_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_index_run_collection FOREIGN KEY(collection_id, workspace_id) REFERENCES kb_collections (id, workspace_id) ON DELETE RESTRICT, 
	CONSTRAINT kb_index_runs_provider_id_fkey FOREIGN KEY(provider_id) REFERENCES providers (id) ON DELETE RESTRICT, 
	CONSTRAINT kb_index_runs_vector_collection_key UNIQUE NULLS DISTINCT (vector_collection), 
	CONSTRAINT uq_index_generation UNIQUE NULLS DISTINCT (collection_id, generation), 
	CONSTRAINT uq_index_request UNIQUE NULLS DISTINCT (workspace_id, requested_by, idempotency_key), 
	CONSTRAINT uq_index_run_scope UNIQUE NULLS DISTINCT (id, workspace_id, collection_id), 
	CONSTRAINT ck_index_active_completed CHECK (NOT is_active OR status = 'completed'), 
	CONSTRAINT ck_index_counters CHECK (generation >= 1 AND dimension > 0 AND attempt_count >= 0), 
	CONSTRAINT ck_index_status CHECK (status IN ('queued','running','completed','failed','uncertain','cancelled'))
)
""",
    """
CREATE TABLE kb_sources (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	status VARCHAR(32) DEFAULT 'stored'::character varying NOT NULL, 
	latest_revision_no INTEGER NOT NULL, 
	created_by VARCHAR(200) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	serving_revision_no INTEGER DEFAULT 1 NOT NULL, 
	CONSTRAINT kb_sources_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_kb_source_collection FOREIGN KEY(collection_id, workspace_id) REFERENCES kb_collections (id, workspace_id) ON DELETE CASCADE, 
	CONSTRAINT uq_kb_source_scope UNIQUE NULLS DISTINCT (id, collection_id, workspace_id), 
	CONSTRAINT ck_kb_source_latest_revision CHECK (latest_revision_no >= 1), 
	CONSTRAINT ck_kb_source_status CHECK (status IN ('stored')), 
	CONSTRAINT ck_source_serving_revision CHECK (serving_revision_no >= 1 AND serving_revision_no <= latest_revision_no)
)
""",
    """
CREATE TABLE ops_evidence_backups (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	created_by VARCHAR(200) NOT NULL, 
	idempotency_key VARCHAR(128) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	retain_until TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	dispatched_at TIMESTAMP WITH TIME ZONE, 
	started_at TIMESTAMP WITH TIME ZONE, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	lease_expires_at TIMESTAMP WITH TIME ZONE, 
	worker_id VARCHAR(120), 
	blob_key VARCHAR(512), 
	sha256 VARCHAR(64), 
	size_bytes INTEGER, 
	manifest JSONB, 
	error_code VARCHAR(64), 
	delete_action_id VARCHAR(64), 
	CONSTRAINT ops_evidence_backups_pkey PRIMARY KEY (id), 
	CONSTRAINT ops_evidence_backups_delete_action_id_fkey FOREIGN KEY(delete_action_id) REFERENCES ops_actions (id) ON DELETE RESTRICT, 
	CONSTRAINT ops_evidence_backups_workspace_id_fkey FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT, 
	CONSTRAINT uq_ops_backup_request UNIQUE NULLS DISTINCT (workspace_id, created_by, idempotency_key), 
	CONSTRAINT ck_ops_backup_status CHECK (status IN ('queued','running','completed','failed','uncertain','deleting','deleted'))
)
""",
    """
CREATE TABLE workspace_model_defaults (
	workspace_id VARCHAR(64) NOT NULL, 
	capability VARCHAR(16) NOT NULL, 
	provider_id VARCHAR(64) NOT NULL, 
	CONSTRAINT workspace_model_defaults_pkey PRIMARY KEY (workspace_id, capability), 
	CONSTRAINT workspace_model_defaults_workspace_id_provider_id_fkey FOREIGN KEY(workspace_id, provider_id) REFERENCES workspace_allowed_providers (workspace_id, provider_id) ON DELETE CASCADE, 
	CONSTRAINT ck_workspace_default_capability CHECK (capability IN ('chat','embedding','rerank','ocr'))
)
""",
    """
CREATE TABLE chat_conversations (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	assistant_id VARCHAR(64) NOT NULL, 
	assistant_revision INTEGER NOT NULL, 
	owner_ref VARCHAR(200) NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	document_ids JSONB, 
	assistant_snapshot JSONB NOT NULL, 
	last_turn_no INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT chat_conversations_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_chat_conversation_assistant FOREIGN KEY(assistant_id, workspace_id, collection_id) REFERENCES chat_assistants (id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT uq_chat_conversation_scope UNIQUE NULLS DISTINCT (id, workspace_id, collection_id), 
	CONSTRAINT ck_chat_conversation_state CHECK (assistant_revision >= 1 AND last_turn_no >= 0 AND status IN ('active','archived'))
)
""",
    """
CREATE TABLE kb_compilation_artifacts (
	id VARCHAR(64) NOT NULL, 
	run_id VARCHAR(64) NOT NULL, 
	kind VARCHAR(24) NOT NULL, 
	blob_key VARCHAR(512) NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	content_type VARCHAR(120) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT kb_compilation_artifacts_pkey PRIMARY KEY (id), 
	CONSTRAINT kb_compilation_artifacts_run_id_fkey FOREIGN KEY(run_id) REFERENCES kb_compilation_runs (id) ON DELETE CASCADE, 
	CONSTRAINT uq_compilation_artifact_kind UNIQUE NULLS DISTINCT (run_id, kind), 
	CONSTRAINT ck_compilation_artifact_integrity CHECK (size_bytes >= 0 AND char_length(sha256) = 64), 
	CONSTRAINT ck_compilation_artifact_kind CHECK (kind IN ('input_snapshot','raw_response','draft_json','markdown'))
)
""",
    """
CREATE TABLE kb_compilation_reviews (
	id VARCHAR(64) NOT NULL, 
	compilation_run_id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	created_by VARCHAR(200) NOT NULL, 
	idempotency_key VARCHAR(128) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	verdict VARCHAR(32), 
	provider_id VARCHAR(64) NOT NULL, 
	input_sha256 VARCHAR(64) NOT NULL, 
	draft_sha256 VARCHAR(64) NOT NULL, 
	bundle_sha256 VARCHAR(64) NOT NULL, 
	trace JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	request_started_at TIMESTAMP WITH TIME ZONE, 
	usage_id VARCHAR(64), 
	usage_tokens INTEGER, 
	error_code VARCHAR(64), 
	CONSTRAINT kb_compilation_reviews_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_compilation_review_scope FOREIGN KEY(compilation_run_id, workspace_id, collection_id) REFERENCES kb_compilation_runs (id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT kb_compilation_reviews_provider_id_fkey FOREIGN KEY(provider_id) REFERENCES providers (id) ON DELETE RESTRICT, 
	CONSTRAINT kb_compilation_reviews_usage_id_fkey FOREIGN KEY(usage_id) REFERENCES model_usage_records (id) ON DELETE RESTRICT, 
	CONSTRAINT uq_compilation_review_request UNIQUE NULLS DISTINCT (workspace_id, created_by, idempotency_key), 
	CONSTRAINT ck_compilation_review_status CHECK (status IN ('running','completed','failed','uncertain','cancelled')), 
	CONSTRAINT ck_compilation_review_verdict CHECK (verdict IS NULL OR verdict IN ('needs_attention','no_issues_detected'))
)
""",
    """
CREATE TABLE kb_compiled_versions (
	id VARCHAR(64) NOT NULL, 
	document_id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	compilation_run_id VARCHAR(64) NOT NULL, 
	version_no INTEGER NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	state_version INTEGER NOT NULL, 
	input_sha256 VARCHAR(64) NOT NULL, 
	draft_sha256 VARCHAR(64) NOT NULL, 
	markdown_sha256 VARCHAR(64) NOT NULL, 
	bundle_sha256 VARCHAR(64) NOT NULL, 
	provenance JSONB NOT NULL, 
	created_by VARCHAR(200) NOT NULL, 
	idempotency_key VARCHAR(128) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT kb_compiled_versions_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_compiled_version_document FOREIGN KEY(document_id, workspace_id, collection_id) REFERENCES kb_compiled_documents (id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT fk_compiled_version_run FOREIGN KEY(compilation_run_id, workspace_id, collection_id) REFERENCES kb_compilation_runs (id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT uq_compiled_registration UNIQUE NULLS DISTINCT (workspace_id, created_by, idempotency_key), 
	CONSTRAINT uq_compiled_version_no UNIQUE NULLS DISTINCT (document_id, version_no), 
	CONSTRAINT uq_compiled_version_run UNIQUE NULLS DISTINCT (compilation_run_id), 
	CONSTRAINT uq_compiled_version_scope UNIQUE NULLS DISTINCT (id, document_id, workspace_id, collection_id), 
	CONSTRAINT ck_compiled_version_sequence CHECK (version_no >= 1 AND state_version >= 1), 
	CONSTRAINT ck_compiled_version_status CHECK (status IN ('draft','approved','published','superseded','withdrawn'))
)
""",
    """
CREATE TABLE kb_source_revisions (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	source_id VARCHAR(64) NOT NULL, 
	revision_no INTEGER NOT NULL, 
	file_name VARCHAR(255) NOT NULL, 
	content_type VARCHAR(120) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	storage_key VARCHAR(512) NOT NULL, 
	created_by VARCHAR(200) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT kb_source_revisions_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_kb_revision_source FOREIGN KEY(source_id, collection_id, workspace_id) REFERENCES kb_sources (id, collection_id, workspace_id) ON DELETE CASCADE, 
	CONSTRAINT uq_kb_revision_content UNIQUE NULLS DISTINCT (collection_id, sha256), 
	CONSTRAINT uq_kb_revision_no UNIQUE NULLS DISTINCT (source_id, revision_no), 
	CONSTRAINT uq_kb_revision_scope UNIQUE NULLS DISTINCT (id, source_id, collection_id, workspace_id), 
	CONSTRAINT uq_kb_revision_storage_key UNIQUE NULLS DISTINCT (storage_key), 
	CONSTRAINT ck_kb_revision_no CHECK (revision_no >= 1), 
	CONSTRAINT ck_kb_revision_sha256 CHECK (char_length(sha256) = 64), 
	CONSTRAINT ck_kb_revision_size CHECK (size_bytes > 0)
)
""",
    """
CREATE TABLE chat_turns (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	conversation_id VARCHAR(64) NOT NULL, 
	turn_no INTEGER NOT NULL, 
	idempotency_key VARCHAR(128) NOT NULL, 
	request_sha256 VARCHAR(64) NOT NULL, 
	question TEXT NOT NULL, 
	resolved_question TEXT, 
	history_turn_ids JSONB NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	error_code VARCHAR(100), 
	result JSONB, 
	rewrite_trace JSONB, 
	lease_expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT chat_turns_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_chat_turn_conversation FOREIGN KEY(conversation_id, workspace_id, collection_id) REFERENCES chat_conversations (id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT uq_chat_turn_request UNIQUE NULLS DISTINCT (conversation_id, idempotency_key), 
	CONSTRAINT uq_chat_turn_sequence UNIQUE NULLS DISTINCT (conversation_id, turn_no), 
	CONSTRAINT ck_chat_turn_status CHECK (turn_no >= 1 AND status IN ('running','completed','failed','uncertain','cancelled'))
)
""",
    """
CREATE TABLE kb_compilation_edit_previews (
	id VARCHAR(64) NOT NULL, 
	compilation_run_id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	created_by VARCHAR(200) NOT NULL, 
	bundle_sha256 VARCHAR(64) NOT NULL, 
	expected_edit_count INTEGER NOT NULL, 
	content JSONB NOT NULL, 
	reason VARCHAR(2000) NOT NULL, 
	review_id VARCHAR(64), 
	report_sha256 VARCHAR(64), 
	preview_sha256 VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	child_run_id VARCHAR(64), 
	CONSTRAINT kb_compilation_edit_previews_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_compilation_edit_scope FOREIGN KEY(compilation_run_id, workspace_id, collection_id) REFERENCES kb_compilation_runs (id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT kb_compilation_edit_previews_child_run_id_fkey FOREIGN KEY(child_run_id) REFERENCES kb_compilation_runs (id) ON DELETE RESTRICT, 
	CONSTRAINT kb_compilation_edit_previews_review_id_fkey FOREIGN KEY(review_id) REFERENCES kb_compilation_reviews (id) ON DELETE RESTRICT, 
	CONSTRAINT kb_compilation_edit_previews_child_run_id_key UNIQUE NULLS DISTINCT (child_run_id)
)
""",
    """
CREATE TABLE kb_compilation_review_artifacts (
	id VARCHAR(64) NOT NULL, 
	review_id VARCHAR(64) NOT NULL, 
	kind VARCHAR(24) NOT NULL, 
	blob_key VARCHAR(512) NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	content_type VARCHAR(120) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT kb_compilation_review_artifacts_pkey PRIMARY KEY (id), 
	CONSTRAINT kb_compilation_review_artifacts_review_id_fkey FOREIGN KEY(review_id) REFERENCES kb_compilation_reviews (id) ON DELETE RESTRICT, 
	CONSTRAINT uq_compilation_review_artifact UNIQUE NULLS DISTINCT (review_id, kind), 
	CONSTRAINT ck_compilation_review_artifact_hash CHECK (size_bytes >= 0 AND char_length(sha256) = 64), 
	CONSTRAINT ck_compilation_review_artifact_kind CHECK (kind IN ('input_snapshot','raw_response','report_json','markdown'))
)
""",
    """
CREATE TABLE kb_compilation_review_jobs (
	compilation_run_id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	created_by VARCHAR(200) NOT NULL, 
	config JSONB NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	review_id VARCHAR(64), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	dispatched_at TIMESTAMP WITH TIME ZONE, 
	started_at TIMESTAMP WITH TIME ZONE, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	lease_expires_at TIMESTAMP WITH TIME ZONE, 
	worker_id VARCHAR(120), 
	error_code VARCHAR(64), 
	CONSTRAINT kb_compilation_review_jobs_pkey PRIMARY KEY (compilation_run_id), 
	CONSTRAINT fk_compilation_review_job_scope FOREIGN KEY(compilation_run_id, workspace_id, collection_id) REFERENCES kb_compilation_runs (id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT kb_compilation_review_jobs_review_id_fkey FOREIGN KEY(review_id) REFERENCES kb_compilation_reviews (id) ON DELETE RESTRICT, 
	CONSTRAINT ck_compilation_review_job_status CHECK (status IN ('queued','running','completed','failed','uncertain','cancelled'))
)
""",
    """
CREATE TABLE kb_publication_previews (
	id VARCHAR(64) NOT NULL, 
	version_id VARCHAR(64) NOT NULL, 
	document_id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	actor_ref VARCHAR(200) NOT NULL, 
	action VARCHAR(16) NOT NULL, 
	reason VARCHAR(1000) NOT NULL, 
	expected_document_sequence INTEGER NOT NULL, 
	expected_version_sequence INTEGER NOT NULL, 
	expected_active_version_id VARCHAR(64), 
	bundle_sha256 VARCHAR(64) NOT NULL, 
	preview_sha256 VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT kb_publication_previews_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_publication_preview_version FOREIGN KEY(version_id, document_id, workspace_id, collection_id) REFERENCES kb_compiled_versions (id, document_id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT uq_publication_preview_scope UNIQUE NULLS DISTINCT (id, version_id, document_id, workspace_id, collection_id), 
	CONSTRAINT ck_publication_preview_action CHECK (action IN ('approve','publish','withdraw'))
)
""",
    """
CREATE TABLE ocr_processing_runs (
	id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	source_id VARCHAR(64) NOT NULL, 
	revision_id VARCHAR(64) NOT NULL, 
	revision_no INTEGER NOT NULL, 
	source_sha256 VARCHAR(64) NOT NULL, 
	generation INTEGER NOT NULL, 
	status VARCHAR(16) DEFAULT 'queued'::character varying NOT NULL, 
	config JSONB DEFAULT '{}'::jsonb NOT NULL, 
	config_fingerprint VARCHAR(64) NOT NULL, 
	provider_id VARCHAR(64), 
	requested_by VARCHAR(200) NOT NULL, 
	requested_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	dispatched_at TIMESTAMP WITH TIME ZONE, 
	started_at TIMESTAMP WITH TIME ZONE, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	pages_total INTEGER, 
	pages_done INTEGER DEFAULT 0 NOT NULL, 
	pages_failed INTEGER DEFAULT 0 NOT NULL, 
	attempt_count INTEGER DEFAULT 0 NOT NULL, 
	max_attempts INTEGER DEFAULT 2 NOT NULL, 
	worker_id VARCHAR(120), 
	lease_expires_at TIMESTAMP WITH TIME ZONE, 
	error_code VARCHAR(64), 
	error_detail VARCHAR(500), 
	usage_tokens INTEGER, 
	CONSTRAINT ocr_processing_runs_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_ocr_run_revision FOREIGN KEY(revision_id, source_id, collection_id, workspace_id) REFERENCES kb_source_revisions (id, source_id, collection_id, workspace_id) ON DELETE CASCADE, 
	CONSTRAINT uq_ocr_run_generation UNIQUE NULLS DISTINCT (revision_id, generation), 
	CONSTRAINT uq_ocr_run_scope UNIQUE NULLS DISTINCT (id, workspace_id, collection_id), 
	CONSTRAINT ck_ocr_run_counters CHECK (pages_done >= 0 AND pages_failed >= 0 AND attempt_count >= 0), 
	CONSTRAINT ck_ocr_run_generation CHECK (generation >= 1), 
	CONSTRAINT ck_ocr_run_sha256 CHECK (char_length(source_sha256) = 64), 
	CONSTRAINT ck_ocr_run_status CHECK (status IN ('queued','running','completed','failed','uncertain','cancelled'))
)
""",
    """
CREATE TABLE kb_publication_decisions (
	id VARCHAR(64) NOT NULL, 
	preview_id VARCHAR(64) NOT NULL, 
	version_id VARCHAR(64) NOT NULL, 
	document_id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	actor_ref VARCHAR(200) NOT NULL, 
	action VARCHAR(16) NOT NULL, 
	reason VARCHAR(1000) NOT NULL, 
	idempotency_key VARCHAR(128) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	document_sequence INTEGER NOT NULL, 
	bundle_sha256 VARCHAR(64) NOT NULL, 
	before JSONB NOT NULL, 
	after JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT kb_publication_decisions_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_publication_decision_preview FOREIGN KEY(preview_id, version_id, document_id, workspace_id, collection_id) REFERENCES kb_publication_previews (id, version_id, document_id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT uq_publication_decision_preview UNIQUE NULLS DISTINCT (preview_id), 
	CONSTRAINT uq_publication_decision_request UNIQUE NULLS DISTINCT (workspace_id, actor_ref, idempotency_key), 
	CONSTRAINT uq_publication_decision_scope UNIQUE NULLS DISTINCT (id, version_id, document_id, workspace_id, collection_id), 
	CONSTRAINT uq_publication_decision_sequence UNIQUE NULLS DISTINCT (document_id, document_sequence), 
	CONSTRAINT ck_publication_decision_action CHECK (action IN ('approve','publish','withdraw'))
)
""",
    """
CREATE TABLE ocr_run_artifacts (
	id VARCHAR(64) NOT NULL, 
	run_id VARCHAR(64) NOT NULL, 
	kind VARCHAR(24) NOT NULL, 
	page_no INTEGER DEFAULT 0 NOT NULL, 
	blob_key VARCHAR(512) NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	content_type VARCHAR(120) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT ocr_run_artifacts_pkey PRIMARY KEY (id), 
	CONSTRAINT ocr_run_artifacts_run_id_fkey FOREIGN KEY(run_id) REFERENCES ocr_processing_runs (id) ON DELETE CASCADE, 
	CONSTRAINT uq_ocr_artifact_kind_page UNIQUE NULLS DISTINCT (run_id, kind, page_no), 
	CONSTRAINT ck_ocr_artifact_kind CHECK (kind IN ('render_pdf','page_image','raw_response','canonical_json','markdown','manifest')), 
	CONSTRAINT ck_ocr_artifact_page CHECK (page_no >= 0), 
	CONSTRAINT ck_ocr_artifact_sha256 CHECK (char_length(sha256) = 64), 
	CONSTRAINT ck_ocr_artifact_size CHECK (size_bytes > 0)
)
""",
    """
CREATE TABLE ocr_run_pages (
	id VARCHAR(64) NOT NULL, 
	run_id VARCHAR(64) NOT NULL, 
	page_number INTEGER NOT NULL, 
	status VARCHAR(16) DEFAULT 'pending'::character varying NOT NULL, 
	image_key VARCHAR(512), 
	image_sha256 VARCHAR(64), 
	width INTEGER, 
	height INTEGER, 
	raw_key VARCHAR(512), 
	raw_sha256 VARCHAR(64), 
	text TEXT, 
	blocks_count INTEGER DEFAULT 0 NOT NULL, 
	has_tables BOOLEAN DEFAULT false NOT NULL, 
	error_code VARCHAR(64), 
	attempts INTEGER DEFAULT 0 NOT NULL, 
	usage_tokens INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT ocr_run_pages_pkey PRIMARY KEY (id), 
	CONSTRAINT ocr_run_pages_run_id_fkey FOREIGN KEY(run_id) REFERENCES ocr_processing_runs (id) ON DELETE CASCADE, 
	CONSTRAINT uq_ocr_page_number UNIQUE NULLS DISTINCT (run_id, page_number), 
	CONSTRAINT ck_ocr_page_attempts CHECK (attempts >= 0), 
	CONSTRAINT ck_ocr_page_number CHECK (page_number >= 1), 
	CONSTRAINT ck_ocr_page_status CHECK (status IN ('pending','in_flight','completed','blank','failed','uncertain'))
)
""",
    """
CREATE TABLE ocr_spelling_runs (
	id VARCHAR(64) NOT NULL, 
	run_id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	canonical_sha256 VARCHAR(64) NOT NULL, 
	created_by VARCHAR(200) NOT NULL, 
	idempotency_key VARCHAR(128) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	checked_evidence_ids JSONB NOT NULL, 
	suggestions JSONB NOT NULL, 
	trace JSONB NOT NULL, 
	usage_id VARCHAR(64), 
	error_code VARCHAR(64), 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT ocr_spelling_runs_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_ocr_spelling_run FOREIGN KEY(run_id, workspace_id, collection_id) REFERENCES ocr_processing_runs (id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT uq_ocr_spelling_request UNIQUE NULLS DISTINCT (workspace_id, created_by, idempotency_key), 
	CONSTRAINT ck_ocr_spelling_status CHECK (status IN ('running','completed','failed','uncertain','cancelled'))
)
""",
    """
CREATE TABLE ocr_text_versions (
	id VARCHAR(64) NOT NULL, 
	run_id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	version INTEGER NOT NULL, 
	canonical_sha256 VARCHAR(64) NOT NULL, 
	created_by VARCHAR(200) NOT NULL, 
	idempotency_key VARCHAR(128) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	original_sha256 VARCHAR(64) NOT NULL, 
	markdown_sha256 VARCHAR(64) NOT NULL, 
	document_key VARCHAR(512) NOT NULL, 
	markdown_key VARCHAR(512) NOT NULL, 
	changes JSONB NOT NULL, 
	CONSTRAINT ocr_text_versions_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_ocr_text_run FOREIGN KEY(run_id, workspace_id, collection_id) REFERENCES ocr_processing_runs (id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT uq_ocr_text_request UNIQUE NULLS DISTINCT (workspace_id, created_by, idempotency_key), 
	CONSTRAINT uq_ocr_text_scope UNIQUE NULLS DISTINCT (id, run_id, workspace_id, collection_id), 
	CONSTRAINT uq_ocr_text_version UNIQUE NULLS DISTINCT (run_id, version), 
	CONSTRAINT ck_ocr_text_version CHECK (version > 0)
)
""",
    """
CREATE TABLE kb_compilation_inputs (
	id VARCHAR(64) NOT NULL, 
	run_id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	ocr_run_id VARCHAR(64) NOT NULL, 
	canonical_sha256 VARCHAR(64) NOT NULL, 
	manifest_sha256 VARCHAR(64) NOT NULL, 
	text_version_id VARCHAR(64), 
	original_canonical_sha256 VARCHAR(64), 
	CONSTRAINT kb_compilation_inputs_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_compilation_input_ocr FOREIGN KEY(ocr_run_id, workspace_id, collection_id) REFERENCES ocr_processing_runs (id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT fk_compilation_input_run FOREIGN KEY(run_id, workspace_id, collection_id) REFERENCES kb_compilation_runs (id, workspace_id, collection_id) ON DELETE CASCADE, 
	CONSTRAINT fk_compilation_input_text FOREIGN KEY(text_version_id, ocr_run_id, workspace_id, collection_id) REFERENCES ocr_text_versions (id, run_id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT uq_compilation_input_ocr UNIQUE NULLS DISTINCT (run_id, ocr_run_id)
)
""",
    """
CREATE TABLE kb_index_inputs (
	id VARCHAR(64) NOT NULL, 
	run_id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	document_id VARCHAR(64) NOT NULL, 
	version_id VARCHAR(64) NOT NULL, 
	publication_decision_id VARCHAR(64) NOT NULL, 
	bundle_sha256 VARCHAR(64) NOT NULL, 
	version_state INTEGER NOT NULL, 
	CONSTRAINT kb_index_inputs_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_index_input_publication FOREIGN KEY(publication_decision_id, version_id, document_id, workspace_id, collection_id) REFERENCES kb_publication_decisions (id, version_id, document_id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT fk_index_input_run FOREIGN KEY(run_id, workspace_id, collection_id) REFERENCES kb_index_runs (id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT uq_index_input_document UNIQUE NULLS DISTINCT (run_id, document_id), 
	CONSTRAINT uq_index_input_scope UNIQUE NULLS DISTINCT (id, run_id, workspace_id, collection_id)
)
""",
    """
CREATE TABLE kb_index_chunks (
	id VARCHAR(64) NOT NULL, 
	input_id VARCHAR(64) NOT NULL, 
	run_id VARCHAR(64) NOT NULL, 
	workspace_id VARCHAR(64) NOT NULL, 
	collection_id VARCHAR(64) NOT NULL, 
	point_id VARCHAR(36) NOT NULL, 
	ordinal INTEGER NOT NULL, 
	kind VARCHAR(16) NOT NULL, 
	text TEXT NOT NULL, 
	text_sha256 VARCHAR(64) NOT NULL, 
	citations JSONB NOT NULL, 
	structure JSONB, 
	vector JSONB, 
	CONSTRAINT kb_index_chunks_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_index_chunk_input FOREIGN KEY(input_id, run_id, workspace_id, collection_id) REFERENCES kb_index_inputs (id, run_id, workspace_id, collection_id) ON DELETE RESTRICT, 
	CONSTRAINT uq_index_chunk_ordinal UNIQUE NULLS DISTINCT (run_id, ordinal), 
	CONSTRAINT uq_index_chunk_point UNIQUE NULLS DISTINCT (point_id), 
	CONSTRAINT ck_index_chunk_ordinal CHECK (ordinal >= 0)
)
""",
    """
CREATE UNIQUE INDEX uq_chat_turn_running ON chat_turns (conversation_id) WHERE status = 'running'
""",
    """
CREATE INDEX ix_kb_collections_workspace_id ON kb_collections (workspace_id)
""",
    """
CREATE INDEX ix_kb_compilation_artifacts_run_id ON kb_compilation_artifacts (run_id)
""",
    """
CREATE INDEX ix_kb_compilation_edit_previews_compilation_run_id ON kb_compilation_edit_previews (compilation_run_id)
""",
    """
CREATE INDEX ix_kb_compilation_inputs_run_id ON kb_compilation_inputs (run_id)
""",
    """
CREATE INDEX ix_kb_compilation_review_artifacts_review_id ON kb_compilation_review_artifacts (review_id)
""",
    """
CREATE INDEX ix_kb_compilation_review_jobs_status ON kb_compilation_review_jobs (status)
""",
    """
CREATE INDEX ix_kb_compilation_reviews_compilation_run_id ON kb_compilation_reviews (compilation_run_id)
""",
    """
CREATE INDEX ix_kb_compilation_reviews_workspace_id ON kb_compilation_reviews (workspace_id)
""",
    """
CREATE INDEX ix_kb_compilation_runs_collection_id ON kb_compilation_runs (collection_id)
""",
    """
CREATE INDEX ix_kb_compilation_runs_status ON kb_compilation_runs (status)
""",
    """
CREATE INDEX ix_kb_compilation_runs_workspace_id ON kb_compilation_runs (workspace_id)
""",
    """
CREATE INDEX ix_kb_compiled_versions_document_id ON kb_compiled_versions (document_id)
""",
    """
CREATE UNIQUE INDEX uq_compiled_document_published ON kb_compiled_versions (document_id) WHERE status = 'published'
""",
    """
CREATE INDEX ix_kb_index_chunks_run_id ON kb_index_chunks (run_id)
""",
    """
CREATE INDEX ix_kb_index_inputs_run_id ON kb_index_inputs (run_id)
""",
    """
CREATE UNIQUE INDEX uq_index_active ON kb_index_runs (collection_id) WHERE is_active = true
""",
    """
CREATE UNIQUE INDEX uq_index_working ON kb_index_runs (collection_id) WHERE status IN ('queued','running')
""",
    """
CREATE INDEX ix_kb_publication_decisions_document_id ON kb_publication_decisions (document_id)
""",
    """
CREATE INDEX ix_kb_sources_collection_id ON kb_sources (collection_id)
""",
    """
CREATE INDEX ix_kb_sources_workspace_id ON kb_sources (workspace_id)
""",
    """
CREATE INDEX ix_model_usage_records_workspace_id ON model_usage_records (workspace_id)
""",
    """
CREATE INDEX ix_ocr_processing_runs_revision_id ON ocr_processing_runs (revision_id)
""",
    """
CREATE INDEX ix_ocr_processing_runs_status ON ocr_processing_runs (status)
""",
    """
CREATE INDEX ix_ocr_processing_runs_workspace_id ON ocr_processing_runs (workspace_id)
""",
    """
CREATE INDEX ix_ocr_runs_workspace_status ON ocr_processing_runs (workspace_id, status)
""",
    """
CREATE UNIQUE INDEX uq_ocr_run_active ON ocr_processing_runs (revision_id) WHERE status IN ('queued','running')
""",
    """
CREATE INDEX ix_ocr_run_artifacts_run_id ON ocr_run_artifacts (run_id)
""",
    """
CREATE INDEX ix_ocr_run_pages_run_id ON ocr_run_pages (run_id)
""",
    """
CREATE INDEX ix_ocr_spelling_runs_run_id ON ocr_spelling_runs (run_id)
""",
    """
CREATE INDEX ix_ocr_text_versions_run_id ON ocr_text_versions (run_id)
""",
    """
CREATE INDEX ix_ops_actions_workspace_id ON ops_actions (workspace_id)
""",
    """
CREATE INDEX ix_ops_evidence_backups_workspace_id ON ops_evidence_backups (workspace_id)
""",
    """
CREATE INDEX ix_provider_key_audits_key_id ON provider_key_audits (key_id)
""",
    """
CREATE INDEX ix_provider_key_audits_provider_id ON provider_key_audits (provider_id)
""",
    """
CREATE INDEX ix_provider_keys_provider_id ON provider_keys (provider_id)
""",
    """
CREATE INDEX ix_provider_keys_status ON provider_keys (status)
""",
    """
CREATE INDEX ix_providers_is_active ON providers (is_active)
""",
    """
CREATE INDEX ix_resource_lifecycle_actions_workspace_id ON resource_lifecycle_actions (workspace_id)
""",
    """
CREATE INDEX ix_workspace_allowed_providers_provider_id ON workspace_allowed_providers (provider_id)
""",
    """
CREATE INDEX ix_workspace_events_action ON workspace_events (action)
""",
    """
CREATE INDEX ix_workspace_events_created_at ON workspace_events (created_at)
""",
    """
CREATE INDEX ix_workspace_events_workspace_id ON workspace_events (workspace_id)
""",
    """
CREATE INDEX ix_workspace_members_actor_ref ON workspace_members (actor_ref)
""",
    """
CREATE INDEX ix_workspace_members_status ON workspace_members (status)
""",
    """
CREATE INDEX ix_workspace_members_workspace_id ON workspace_members (workspace_id)
""",
    """
CREATE UNIQUE INDEX ix_workspaces_code ON workspaces (code)
""",
    """
CREATE INDEX ix_workspaces_status ON workspaces (status)
""",
)


def upgrade() -> None:
    if not context.is_offline_mode():
        existing = set(sa.inspect(op.get_bind()).get_table_names())
        if existing.intersection(V1_OWNED):
            raise RuntimeError(
                "V1 tables already exist outside the initial migration history; no automatic adoption."
            )
    for statement in DDL:
        op.execute(sa.text(statement))


def downgrade() -> None:
    raise RuntimeError("Source evidence must be preserved; downgrade is disabled.")
