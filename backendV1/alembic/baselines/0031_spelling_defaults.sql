-- Frozen PostgreSQL schema from the complete V1 upgrade chain through 0031_spelling_defaults.
-- Schema-only pg_dump of an isolated empty database. See backendV1/docs/migrations.md.

CREATE TABLE public.app_api_keys (
    id character varying(64) NOT NULL,
    app_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    name character varying(160) NOT NULL,
    key_prefix character varying(32) NOT NULL,
    key_hash character varying(128) NOT NULL,
    status character varying(24) DEFAULT 'active'::character varying NOT NULL,
    allowed_assistant_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    rate_limit_rpm integer DEFAULT 60,
    rate_limit_rpd integer DEFAULT 10000,
    expires_at timestamp with time zone,
    last_used_at timestamp with time zone,
    rotated_from_key_id character varying(64),
    revoked_at timestamp with time zone,
    revoked_reason character varying(255),
    created_by character varying(200) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    idempotency_key character varying(128),
    CONSTRAINT ck_app_key_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'suspended'::character varying, 'revoked'::character varying])::text[])))
);

CREATE TABLE public.app_clients (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    name character varying(160) NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    status character varying(24) DEFAULT 'active'::character varying NOT NULL,
    created_by character varying(200) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_app_client_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'suspended'::character varying, 'revoked'::character varying])::text[])))
);

CREATE TABLE public.app_request_logs (
    id character varying(64) NOT NULL,
    app_id character varying(64) NOT NULL,
    key_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    assistant_id character varying(64) NOT NULL,
    endpoint character varying(128) NOT NULL,
    status_code integer NOT NULL,
    latency_ms integer NOT NULL,
    prompt_tokens integer,
    completion_tokens integer,
    total_tokens integer,
    error_code character varying(64),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.assistant_publication_questions (
    id character varying(64) NOT NULL,
    publication_id character varying(64) NOT NULL,
    question_hash character varying(64) NOT NULL,
    question text NOT NULL,
    times_asked integer DEFAULT 1 NOT NULL,
    last_asked_at timestamp with time zone NOT NULL
);

CREATE TABLE public.assistant_publication_stats (
    publication_id character varying(64) NOT NULL,
    day date NOT NULL,
    sessions integer DEFAULT 0 NOT NULL,
    turns integer DEFAULT 0 NOT NULL,
    insufficient_turns integer DEFAULT 0 NOT NULL,
    error_turns integer DEFAULT 0 NOT NULL,
    tokens bigint DEFAULT '0'::bigint NOT NULL
);

CREATE TABLE public.assistant_publications (
    id character varying(64) NOT NULL,
    assistant_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    slug character varying(64) NOT NULL,
    display_name character varying(160) NOT NULL,
    welcome_message text NOT NULL,
    starter_prompts jsonb DEFAULT '[]'::jsonb NOT NULL,
    max_turns_per_session integer NOT NULL,
    daily_token_budget integer,
    enabled boolean DEFAULT false NOT NULL,
    revision integer NOT NULL,
    updated_by character varying(200) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_assistant_publication_config CHECK (((revision >= 1) AND ((max_turns_per_session >= 1) AND (max_turns_per_session <= 100)) AND ((daily_token_budget IS NULL) OR (daily_token_budget >= 1000)))),
    CONSTRAINT ck_assistant_publication_slug CHECK (((slug)::text ~ '^[a-z0-9][a-z0-9-]{1,58}[a-z0-9]$'::text))
);

CREATE TABLE public.chat_assistants (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    name character varying(160) NOT NULL,
    description text NOT NULL,
    persona text NOT NULL,
    chat_provider_id character varying(64),
    revision integer NOT NULL,
    is_active boolean NOT NULL,
    top_k integer NOT NULL,
    history_turns integer NOT NULL,
    max_output_tokens integer,
    created_by character varying(200) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    rag_policy jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT ck_chat_assistant_config CHECK (((revision >= 1) AND ((top_k >= 1) AND (top_k <= 20)) AND ((history_turns >= 0) AND (history_turns <= 10)) AND (max_output_tokens > 0)))
);

CREATE TABLE public.chat_conversations (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    assistant_id character varying(64) NOT NULL,
    assistant_revision integer NOT NULL,
    owner_ref character varying(200) NOT NULL,
    title character varying(160) NOT NULL,
    status character varying(16) NOT NULL,
    document_ids jsonb,
    assistant_snapshot jsonb NOT NULL,
    last_turn_no integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_chat_conversation_state CHECK (((assistant_revision >= 1) AND (last_turn_no >= 0) AND ((status)::text = ANY ((ARRAY['active'::character varying, 'archived'::character varying])::text[]))))
);

CREATE TABLE public.chat_turns (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    conversation_id character varying(64) NOT NULL,
    turn_no integer NOT NULL,
    idempotency_key character varying(128) NOT NULL,
    request_sha256 character varying(64) NOT NULL,
    question text NOT NULL,
    resolved_question text,
    history_turn_ids jsonb NOT NULL,
    status character varying(16) NOT NULL,
    error_code character varying(100),
    result jsonb,
    rewrite_trace jsonb,
    lease_expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL,
    finished_at timestamp with time zone,
    metadata_filter jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT ck_chat_turn_status CHECK (((turn_no >= 1) AND ((status)::text = ANY ((ARRAY['running'::character varying, 'completed'::character varying, 'failed'::character varying, 'uncertain'::character varying, 'cancelled'::character varying])::text[]))))
);

CREATE TABLE public.kb_answer_review_items (
    id character varying(64) NOT NULL,
    review_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    ordinal integer NOT NULL,
    question text NOT NULL,
    status character varying(24) NOT NULL,
    error_code character varying(100),
    result jsonb,
    index_run_id character varying(64),
    generation integer,
    label character varying(16),
    label_note text,
    labelled_by character varying(200),
    labelled_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    finished_at timestamp with time zone,
    CONSTRAINT ck_answer_review_item_label CHECK (((label IS NULL) OR ((label)::text = ANY ((ARRAY['correct'::character varying, 'missing'::character varying, 'wrong_source'::character varying, 'wrong_year'::character varying])::text[])))),
    CONSTRAINT ck_answer_review_item_ordinal CHECK (((ordinal >= 0) AND (ordinal < 3))),
    CONSTRAINT ck_answer_review_item_status CHECK (((status)::text = ANY ((ARRAY['answered'::character varying, 'insufficient_evidence'::character varying, 'failed'::character varying, 'uncertain'::character varying])::text[])))
);

CREATE TABLE public.kb_answer_reviews (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    assistant_id character varying(64) NOT NULL,
    assistant_revision integer NOT NULL,
    assistant_snapshot jsonb NOT NULL,
    requested_by character varying(200) NOT NULL,
    idempotency_key character varying(128) NOT NULL,
    request_sha256 character varying(64) NOT NULL,
    question_count integer NOT NULL,
    status character varying(16) NOT NULL,
    error_code character varying(100),
    created_at timestamp with time zone NOT NULL,
    finished_at timestamp with time zone,
    CONSTRAINT ck_answer_review_state CHECK (((assistant_revision >= 1) AND ((question_count >= 1) AND (question_count <= 3)))),
    CONSTRAINT ck_answer_review_status CHECK (((status)::text = ANY ((ARRAY['running'::character varying, 'completed'::character varying, 'failed'::character varying, 'uncertain'::character varying])::text[])))
);

CREATE TABLE public.kb_collections (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    created_by character varying(200) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.kb_compilation_artifacts (
    id character varying(64) NOT NULL,
    run_id character varying(64) NOT NULL,
    kind character varying(24) NOT NULL,
    blob_key character varying(512) NOT NULL,
    sha256 character varying(64) NOT NULL,
    size_bytes integer NOT NULL,
    content_type character varying(120) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_compilation_artifact_integrity CHECK (((size_bytes >= 0) AND (char_length((sha256)::text) = 64))),
    CONSTRAINT ck_compilation_artifact_kind CHECK (((kind)::text = ANY ((ARRAY['input_snapshot'::character varying, 'raw_response'::character varying, 'draft_json'::character varying, 'markdown'::character varying, 'segment_manifest'::character varying])::text[])))
);

CREATE TABLE public.kb_compilation_edit_previews (
    id character varying(64) NOT NULL,
    compilation_run_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    created_by character varying(200) NOT NULL,
    bundle_sha256 character varying(64) NOT NULL,
    expected_edit_count integer NOT NULL,
    content jsonb NOT NULL,
    reason character varying(2000) NOT NULL,
    review_id character varying(64),
    report_sha256 character varying(64),
    preview_sha256 character varying(64) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    child_run_id character varying(64)
);

CREATE TABLE public.kb_compilation_inputs (
    id character varying(64) NOT NULL,
    run_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    ocr_run_id character varying(64) NOT NULL,
    canonical_sha256 character varying(64) NOT NULL,
    manifest_sha256 character varying(64) NOT NULL,
    text_version_id character varying(64),
    original_canonical_sha256 character varying(64)
);

CREATE TABLE public.kb_compilation_outputs (
    id character varying(64) NOT NULL,
    run_id character varying(64) NOT NULL,
    generation integer NOT NULL,
    partial boolean NOT NULL,
    draft_blob_key character varying(512) NOT NULL,
    draft_sha256 character varying(64) NOT NULL,
    markdown_blob_key character varying(512) NOT NULL,
    markdown_sha256 character varying(64) NOT NULL,
    coverage jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_compilation_output_generation CHECK ((generation >= 1)),
    CONSTRAINT ck_compilation_output_hash CHECK (((char_length((draft_sha256)::text) = 64) AND (char_length((markdown_sha256)::text) = 64)))
);

CREATE TABLE public.kb_compilation_review_artifacts (
    id character varying(64) NOT NULL,
    review_id character varying(64) NOT NULL,
    kind character varying(24) NOT NULL,
    blob_key character varying(512) NOT NULL,
    sha256 character varying(64) NOT NULL,
    size_bytes integer NOT NULL,
    content_type character varying(120) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_compilation_review_artifact_hash CHECK (((size_bytes >= 0) AND (char_length((sha256)::text) = 64))),
    CONSTRAINT ck_compilation_review_artifact_kind CHECK (((kind)::text = ANY ((ARRAY['input_snapshot'::character varying, 'raw_response'::character varying, 'report_json'::character varying, 'markdown'::character varying, 'segment_manifest'::character varying])::text[])))
);

CREATE TABLE public.kb_compilation_review_jobs (
    compilation_run_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    created_by character varying(200) NOT NULL,
    config jsonb NOT NULL,
    status character varying(16) NOT NULL,
    review_id character varying(64),
    created_at timestamp with time zone NOT NULL,
    dispatched_at timestamp with time zone,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    lease_expires_at timestamp with time zone,
    worker_id character varying(120),
    error_code character varying(64),
    CONSTRAINT ck_compilation_review_job_status CHECK (((status)::text = ANY ((ARRAY['queued'::character varying, 'running'::character varying, 'completed'::character varying, 'failed'::character varying, 'uncertain'::character varying, 'cancelled'::character varying])::text[])))
);

CREATE TABLE public.kb_compilation_review_segment_artifacts (
    id character varying(64) NOT NULL,
    segment_id character varying(64) NOT NULL,
    kind character varying(24) NOT NULL,
    blob_key character varying(512) NOT NULL,
    sha256 character varying(64) NOT NULL,
    size_bytes integer NOT NULL,
    content_type character varying(120) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_compilation_review_segment_artifact_hash CHECK (((size_bytes >= 0) AND (char_length((sha256)::text) = 64))),
    CONSTRAINT ck_compilation_review_segment_artifact_kind CHECK (((kind)::text = ANY ((ARRAY['raw_response'::character varying, 'assessment_json'::character varying, 'markdown'::character varying])::text[])))
);

CREATE TABLE public.kb_compilation_review_segments (
    id character varying(64) NOT NULL,
    review_id character varying(64) NOT NULL,
    segment_index integer NOT NULL,
    status character varying(16) NOT NULL,
    scope jsonb NOT NULL,
    input_sha256 character varying(64) NOT NULL,
    prompt_version character varying(120) NOT NULL,
    schema_sha256 character varying(64),
    config jsonb NOT NULL,
    request_hash character varying(64) NOT NULL,
    attempt_count integer NOT NULL,
    worker_id character varying(120),
    created_at timestamp with time zone NOT NULL,
    started_at timestamp with time zone,
    request_started_at timestamp with time zone,
    finished_at timestamp with time zone,
    usage_id character varying(64),
    usage_tokens integer,
    error_code character varying(64),
    parent_segment_id character varying(64),
    CONSTRAINT ck_compilation_review_segment_counters CHECK (((segment_index >= 1) AND (attempt_count >= 0))),
    CONSTRAINT ck_compilation_review_segment_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'running'::character varying, 'received'::character varying, 'completed'::character varying, 'failed'::character varying, 'uncertain'::character varying])::text[])))
);

CREATE TABLE public.kb_compilation_reviews (
    id character varying(64) NOT NULL,
    compilation_run_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    created_by character varying(200) NOT NULL,
    idempotency_key character varying(128) NOT NULL,
    request_hash character varying(64) NOT NULL,
    status character varying(16) NOT NULL,
    verdict character varying(32),
    provider_id character varying(64) NOT NULL,
    input_sha256 character varying(64) NOT NULL,
    draft_sha256 character varying(64) NOT NULL,
    bundle_sha256 character varying(64) NOT NULL,
    trace jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    finished_at timestamp with time zone,
    request_started_at timestamp with time zone,
    usage_id character varying(64),
    usage_tokens integer,
    error_code character varying(64),
    CONSTRAINT ck_compilation_review_status CHECK (((status)::text = ANY ((ARRAY['queued'::character varying, 'running'::character varying, 'completed'::character varying, 'failed'::character varying, 'uncertain'::character varying, 'cancelled'::character varying])::text[]))),
    CONSTRAINT ck_compilation_review_verdict CHECK (((verdict IS NULL) OR ((verdict)::text = ANY ((ARRAY['needs_attention'::character varying, 'no_issues_detected'::character varying])::text[]))))
);

CREATE TABLE public.kb_compilation_runs (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    generation integer NOT NULL,
    topic character varying(2000) NOT NULL,
    status character varying(16) NOT NULL,
    requested_by character varying(200) NOT NULL,
    idempotency_key character varying(128) NOT NULL,
    request_hash character varying(64) NOT NULL,
    input_sha256 character varying(64) NOT NULL,
    provider_id character varying(64),
    config jsonb NOT NULL,
    requested_at timestamp with time zone NOT NULL,
    dispatched_at timestamp with time zone,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    request_started_at timestamp with time zone,
    attempt_count integer NOT NULL,
    worker_id character varying(120),
    lease_expires_at timestamp with time zone,
    usage_id character varying(64),
    usage_tokens integer,
    error_code character varying(64),
    parent_run_id character varying(64),
    origin character varying(16) DEFAULT 'model'::character varying NOT NULL,
    output_id character varying(64),
    CONSTRAINT ck_compilation_ancestry CHECK (((((origin)::text = 'model'::text) AND (parent_run_id IS NULL)) OR (((origin)::text = 'user_edit'::text) AND (parent_run_id IS NOT NULL)))),
    CONSTRAINT ck_compilation_counters CHECK (((generation >= 1) AND (attempt_count >= 0))),
    CONSTRAINT ck_compilation_origin CHECK (((origin)::text = ANY ((ARRAY['model'::character varying, 'user_edit'::character varying])::text[]))),
    CONSTRAINT ck_compilation_status CHECK (((status)::text = ANY ((ARRAY['queued'::character varying, 'running'::character varying, 'completed'::character varying, 'failed'::character varying, 'uncertain'::character varying, 'cancelled'::character varying])::text[])))
);

CREATE TABLE public.kb_compilation_segment_artifacts (
    id character varying(64) NOT NULL,
    segment_id character varying(64) NOT NULL,
    kind character varying(24) NOT NULL,
    blob_key character varying(512) NOT NULL,
    sha256 character varying(64) NOT NULL,
    size_bytes integer NOT NULL,
    content_type character varying(120) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_compilation_segment_artifact_integrity CHECK (((size_bytes >= 0) AND (char_length((sha256)::text) = 64))),
    CONSTRAINT ck_compilation_segment_artifact_kind CHECK (((kind)::text = ANY ((ARRAY['raw_response'::character varying, 'draft_json'::character varying, 'markdown'::character varying])::text[])))
);

CREATE TABLE public.kb_compilation_segments (
    id character varying(64) NOT NULL,
    run_id character varying(64) NOT NULL,
    segment_index integer NOT NULL,
    status character varying(16) NOT NULL,
    scope jsonb NOT NULL,
    input_sha256 character varying(64) NOT NULL,
    prompt_version character varying(120) NOT NULL,
    schema_sha256 character varying(64),
    config jsonb NOT NULL,
    request_hash character varying(64) NOT NULL,
    attempt_count integer NOT NULL,
    worker_id character varying(120),
    created_at timestamp with time zone NOT NULL,
    started_at timestamp with time zone,
    request_started_at timestamp with time zone,
    finished_at timestamp with time zone,
    usage_id character varying(64),
    usage_tokens integer,
    error_code character varying(64),
    parent_segment_id character varying(64),
    CONSTRAINT ck_compilation_segment_counters CHECK (((segment_index >= 1) AND (attempt_count >= 0))),
    CONSTRAINT ck_compilation_segment_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'running'::character varying, 'received'::character varying, 'completed'::character varying, 'failed'::character varying, 'uncertain'::character varying])::text[])))
);

CREATE TABLE public.kb_compiled_documents (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    document_key character varying(120) NOT NULL,
    title character varying(255) NOT NULL,
    change_sequence integer NOT NULL,
    created_by character varying(200) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_compiled_document_sequence CHECK ((change_sequence >= 1))
);

CREATE TABLE public.kb_compiled_versions (
    id character varying(64) NOT NULL,
    document_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    compilation_run_id character varying(64) NOT NULL,
    version_no integer NOT NULL,
    status character varying(16) NOT NULL,
    state_version integer NOT NULL,
    input_sha256 character varying(64) NOT NULL,
    draft_sha256 character varying(64) NOT NULL,
    markdown_sha256 character varying(64) NOT NULL,
    bundle_sha256 character varying(64) NOT NULL,
    provenance jsonb NOT NULL,
    created_by character varying(200) NOT NULL,
    idempotency_key character varying(128) NOT NULL,
    request_hash character varying(64) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    retrieval_metadata jsonb DEFAULT '[]'::jsonb NOT NULL,
    CONSTRAINT ck_compiled_version_sequence CHECK (((version_no >= 1) AND (state_version >= 1))),
    CONSTRAINT ck_compiled_version_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'approved'::character varying, 'published'::character varying, 'superseded'::character varying, 'withdrawn'::character varying])::text[])))
);

CREATE TABLE public.kb_folders (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    parent_id character varying(64),
    name character varying(255) NOT NULL,
    created_by character varying(200) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_kb_folder_name_len CHECK ((char_length((name)::text) >= 1))
);

CREATE TABLE public.kb_index_chunks (
    id character varying(64) NOT NULL,
    input_id character varying(64) NOT NULL,
    run_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    point_id character varying(36) NOT NULL,
    ordinal integer NOT NULL,
    kind character varying(16) NOT NULL,
    text text NOT NULL,
    text_sha256 character varying(64) NOT NULL,
    citations jsonb NOT NULL,
    structure jsonb,
    vector jsonb,
    CONSTRAINT ck_index_chunk_ordinal CHECK ((ordinal >= 0))
);

CREATE TABLE public.kb_index_inputs (
    id character varying(64) NOT NULL,
    run_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    document_id character varying(64) NOT NULL,
    version_id character varying(64) NOT NULL,
    publication_decision_id character varying(64) NOT NULL,
    bundle_sha256 character varying(64) NOT NULL,
    version_state integer NOT NULL
);

CREATE TABLE public.kb_index_runs (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    generation integer NOT NULL,
    status character varying(16) NOT NULL,
    is_active boolean NOT NULL,
    provider_id character varying(64) NOT NULL,
    dimension integer NOT NULL,
    vector_collection character varying(120) NOT NULL,
    config jsonb NOT NULL,
    input_sha256 character varying(64) NOT NULL,
    requested_by character varying(200) NOT NULL,
    idempotency_key character varying(128) NOT NULL,
    request_hash character varying(64) NOT NULL,
    requested_at timestamp with time zone NOT NULL,
    dispatched_at timestamp with time zone,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    worker_id character varying(120),
    lease_expires_at timestamp with time zone,
    attempt_count integer NOT NULL,
    error_code character varying(64),
    chunks_total integer NOT NULL,
    pending_batch jsonb,
    batch_receipts jsonb NOT NULL,
    manifest_key character varying(512),
    manifest_sha256 character varying(64),
    vectors_retired_at timestamp with time zone,
    deactivated_at timestamp with time zone,
    CONSTRAINT ck_index_active_completed CHECK (((NOT is_active) OR ((status)::text = 'completed'::text))),
    CONSTRAINT ck_index_counters CHECK (((generation >= 1) AND (dimension > 0) AND (attempt_count >= 0))),
    CONSTRAINT ck_index_status CHECK (((status)::text = ANY ((ARRAY['queued'::character varying, 'running'::character varying, 'completed'::character varying, 'failed'::character varying, 'uncertain'::character varying, 'cancelled'::character varying])::text[])))
);

CREATE TABLE public.kb_index_sync (
    collection_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    revision integer NOT NULL,
    run_revision integer NOT NULL,
    requested_by character varying(200) NOT NULL,
    status character varying(16) NOT NULL,
    run_id character varying(64),
    error_code character varying(64),
    retry_receipts jsonb NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_index_sync_revision CHECK (((revision >= 1) AND (run_revision >= 0))),
    CONSTRAINT ck_index_sync_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'building'::character varying, 'ready'::character varying, 'empty'::character varying, 'failed'::character varying, 'uncertain'::character varying])::text[])))
);

CREATE TABLE public.kb_preparation_intents (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    source_id character varying(64) NOT NULL,
    revision_id character varying(64) NOT NULL,
    revision_no integer NOT NULL,
    revision_sha256 character varying(64) NOT NULL,
    requested_by character varying(200) NOT NULL,
    idempotency_key character varying(128) NOT NULL,
    request_hash character varying(64) NOT NULL,
    mode character varying(16) NOT NULL,
    status character varying(16) NOT NULL,
    topic character varying(2000) NOT NULL,
    text_version integer NOT NULL,
    text_version_id character varying(64),
    text_canonical_sha256 character varying(64),
    provider_id character varying(64),
    max_output_tokens integer,
    config jsonb NOT NULL,
    ocr_run_id character varying(64),
    compilation_run_id character varying(64),
    error_code character varying(64),
    error_detail character varying(500),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    dispatched_at timestamp with time zone,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    lease_expires_at timestamp with time zone,
    worker_id character varying(120),
    CONSTRAINT ck_preparation_mode CHECK (((mode)::text = ANY ((ARRAY['source'::character varying, 'ai'::character varying, 'auto'::character varying])::text[]))),
    CONSTRAINT ck_preparation_revision CHECK ((revision_no >= 1)),
    CONSTRAINT ck_preparation_sha256 CHECK ((char_length((revision_sha256)::text) = 64)),
    CONSTRAINT ck_preparation_status CHECK (((status)::text = ANY ((ARRAY['queued'::character varying, 'waiting_ocr'::character varying, 'compiling'::character varying, 'ready'::character varying, 'failed'::character varying, 'uncertain'::character varying, 'cancelled'::character varying])::text[]))),
    CONSTRAINT ck_preparation_text_version CHECK ((text_version >= 0))
);

CREATE TABLE public.kb_publication_decisions (
    id character varying(64) NOT NULL,
    preview_id character varying(64) NOT NULL,
    version_id character varying(64) NOT NULL,
    document_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    actor_ref character varying(200) NOT NULL,
    action character varying(16) NOT NULL,
    reason character varying(1000) NOT NULL,
    idempotency_key character varying(128) NOT NULL,
    request_hash character varying(64) NOT NULL,
    document_sequence integer NOT NULL,
    bundle_sha256 character varying(64) NOT NULL,
    before jsonb NOT NULL,
    after jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_publication_decision_action CHECK (((action)::text = ANY ((ARRAY['approve'::character varying, 'publish'::character varying, 'withdraw'::character varying])::text[])))
);

CREATE TABLE public.kb_publication_previews (
    id character varying(64) NOT NULL,
    version_id character varying(64) NOT NULL,
    document_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    actor_ref character varying(200) NOT NULL,
    action character varying(16) NOT NULL,
    reason character varying(1000) NOT NULL,
    expected_document_sequence integer NOT NULL,
    expected_version_sequence integer NOT NULL,
    expected_active_version_id character varying(64),
    bundle_sha256 character varying(64) NOT NULL,
    preview_sha256 character varying(64) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL,
    review_ack jsonb,
    CONSTRAINT ck_publication_preview_action CHECK (((action)::text = ANY ((ARRAY['approve'::character varying, 'publish'::character varying, 'withdraw'::character varying])::text[])))
);

CREATE TABLE public.kb_review_submission_actions (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    document_id character varying(64) NOT NULL,
    version_id character varying(64) NOT NULL,
    submission_id character varying(64) NOT NULL,
    preview_id character varying(64),
    publication_decision_id character varying(64),
    action character varying(20) NOT NULL,
    actor_ref character varying(200) NOT NULL,
    reason character varying(1000) NOT NULL,
    idempotency_key character varying(128),
    request_hash character varying(64),
    document_sequence integer NOT NULL,
    bundle_sha256 character varying(64) NOT NULL,
    before jsonb NOT NULL,
    after jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_review_action_action CHECK (((action)::text = ANY ((ARRAY['submit'::character varying, 'request_changes'::character varying, 'cancel'::character varying, 'approved'::character varying, 'superseded'::character varying])::text[])))
);

CREATE TABLE public.kb_review_submission_previews (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    document_id character varying(64) NOT NULL,
    version_id character varying(64) NOT NULL,
    submission_id character varying(64),
    actor_ref character varying(200) NOT NULL,
    action character varying(20) NOT NULL,
    reason character varying(1000) NOT NULL,
    expected_document_sequence integer NOT NULL,
    expected_version_sequence integer NOT NULL,
    expected_submission_status character varying(20),
    expected_submission_sequence integer,
    bundle_sha256 character varying(64) NOT NULL,
    preview_sha256 character varying(64) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_review_preview_action CHECK (((action)::text = ANY ((ARRAY['submit'::character varying, 'request_changes'::character varying, 'cancel'::character varying])::text[])))
);

CREATE TABLE public.kb_review_submissions (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    document_id character varying(64) NOT NULL,
    version_id character varying(64) NOT NULL,
    bundle_sha256 character varying(64) NOT NULL,
    status character varying(20) NOT NULL,
    state_version integer NOT NULL,
    note character varying(1000) NOT NULL,
    submitted_by character varying(200) NOT NULL,
    submitted_at timestamp with time zone NOT NULL,
    document_sequence integer NOT NULL,
    closed_by character varying(200),
    closed_at timestamp with time zone,
    close_reason character varying(1000),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_review_bundle_sha256 CHECK ((char_length((bundle_sha256)::text) = 64)),
    CONSTRAINT ck_review_sequence CHECK (((state_version >= 1) AND (document_sequence >= 1))),
    CONSTRAINT ck_review_submission_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'changes_requested'::character varying, 'resolved'::character varying, 'cancelled'::character varying])::text[])))
);

CREATE TABLE public.kb_source_revisions (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    source_id character varying(64) NOT NULL,
    revision_no integer NOT NULL,
    file_name character varying(255) NOT NULL,
    content_type character varying(120) NOT NULL,
    size_bytes integer NOT NULL,
    sha256 character varying(64) NOT NULL,
    storage_key character varying(512) NOT NULL,
    created_by character varying(200) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_kb_revision_no CHECK ((revision_no >= 1)),
    CONSTRAINT ck_kb_revision_sha256 CHECK ((char_length((sha256)::text) = 64)),
    CONSTRAINT ck_kb_revision_size CHECK ((size_bytes > 0))
);

CREATE TABLE public.kb_sources (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    title character varying(255) NOT NULL,
    status character varying(32) DEFAULT 'stored'::character varying NOT NULL,
    latest_revision_no integer NOT NULL,
    created_by character varying(200) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    serving_revision_no integer DEFAULT 1 NOT NULL,
    folder_id character varying(64),
    CONSTRAINT ck_kb_source_latest_revision CHECK ((latest_revision_no >= 1)),
    CONSTRAINT ck_kb_source_status CHECK (((status)::text = 'stored'::text)),
    CONSTRAINT ck_source_serving_revision CHECK (((serving_revision_no >= 1) AND (serving_revision_no <= latest_revision_no)))
);

CREATE TABLE public.kb_upload_requests (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    actor_ref character varying(200) NOT NULL,
    idempotency_key character varying(128) NOT NULL,
    request_hash character varying(64) NOT NULL,
    source_id character varying(64) NOT NULL,
    revision_id character varying(64) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_kb_upload_request_hash CHECK ((char_length((request_hash)::text) = 64))
);

CREATE TABLE public.model_defaults (
    id character varying(32) NOT NULL,
    chat_provider_id character varying(64),
    chat_model character varying(200),
    embedding_provider_id character varying(64),
    embedding_model character varying(200),
    rerank_provider_id character varying(64),
    rerank_model character varying(200),
    ocr_provider_id character varying(64),
    ocr_model character varying(200),
    updated_by character varying(200),
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.model_usage_records (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    provider_id character varying(64) NOT NULL,
    actor_ref character varying(200) NOT NULL,
    request_id character varying(128) NOT NULL,
    request_hash character varying(64) NOT NULL,
    capability character varying(16) NOT NULL,
    model_name character varying(200) NOT NULL,
    month_period date NOT NULL,
    reserved_tokens bigint NOT NULL,
    total_tokens bigint,
    cost_usd numeric(20,8),
    status character varying(16) DEFAULT 'reserved'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_model_usage_cost CHECK (((cost_usd IS NULL) OR (cost_usd >= (0)::numeric))),
    CONSTRAINT ck_model_usage_status CHECK (((status)::text = ANY ((ARRAY['reserved'::character varying, 'completed'::character varying, 'failed'::character varying, 'unknown'::character varying])::text[]))),
    CONSTRAINT ck_model_usage_tokens CHECK (((reserved_tokens >= 0) AND ((total_tokens IS NULL) OR (total_tokens >= 0))))
);

CREATE TABLE public.modelops_events (
    id character varying(64) NOT NULL,
    actor_ref character varying(200) NOT NULL,
    action character varying(64) NOT NULL,
    provider_id character varying(64),
    detail jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.ocr_processing_runs (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    source_id character varying(64) NOT NULL,
    revision_id character varying(64) NOT NULL,
    revision_no integer NOT NULL,
    source_sha256 character varying(64) NOT NULL,
    generation integer NOT NULL,
    status character varying(32) DEFAULT 'queued'::character varying NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    config_fingerprint character varying(64) NOT NULL,
    provider_id character varying(64),
    requested_by character varying(200) NOT NULL,
    requested_at timestamp with time zone DEFAULT now() NOT NULL,
    dispatched_at timestamp with time zone,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    pages_total integer,
    pages_done integer DEFAULT 0 NOT NULL,
    pages_failed integer DEFAULT 0 NOT NULL,
    attempt_count integer DEFAULT 0 NOT NULL,
    max_attempts integer DEFAULT 2 NOT NULL,
    worker_id character varying(120),
    lease_expires_at timestamp with time zone,
    error_code character varying(64),
    error_detail character varying(500),
    usage_tokens integer,
    CONSTRAINT ck_ocr_run_counters CHECK (((pages_done >= 0) AND (pages_failed >= 0) AND (attempt_count >= 0))),
    CONSTRAINT ck_ocr_run_generation CHECK ((generation >= 1)),
    CONSTRAINT ck_ocr_run_sha256 CHECK ((char_length((source_sha256)::text) = 64)),
    CONSTRAINT ck_ocr_run_status CHECK (((status)::text = ANY ((ARRAY['queued'::character varying, 'running'::character varying, 'completed'::character varying, 'completed_with_warnings'::character varying, 'failed'::character varying, 'uncertain'::character varying, 'cancelled'::character varying])::text[])))
);

CREATE TABLE public.ocr_run_artifacts (
    id character varying(64) NOT NULL,
    run_id character varying(64) NOT NULL,
    kind character varying(24) NOT NULL,
    page_no integer DEFAULT 0 NOT NULL,
    blob_key character varying(512) NOT NULL,
    sha256 character varying(64) NOT NULL,
    size_bytes integer NOT NULL,
    content_type character varying(120) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_ocr_artifact_kind CHECK (((kind)::text = ANY ((ARRAY['render_pdf'::character varying, 'page_image'::character varying, 'raw_response'::character varying, 'canonical_json'::character varying, 'markdown'::character varying, 'manifest'::character varying, 'native_page'::character varying, 'embedded_image'::character varying, 'provider_document'::character varying])::text[]))),
    CONSTRAINT ck_ocr_artifact_page CHECK ((page_no >= 0)),
    CONSTRAINT ck_ocr_artifact_sha256 CHECK ((char_length((sha256)::text) = 64)),
    CONSTRAINT ck_ocr_artifact_size CHECK ((size_bytes > 0))
);

CREATE TABLE public.ocr_run_pages (
    id character varying(64) NOT NULL,
    run_id character varying(64) NOT NULL,
    page_number integer NOT NULL,
    status character varying(16) DEFAULT 'pending'::character varying NOT NULL,
    image_key character varying(512),
    image_sha256 character varying(64),
    width integer,
    height integer,
    raw_key character varying(512),
    raw_sha256 character varying(64),
    text text,
    blocks_count integer DEFAULT 0 NOT NULL,
    has_tables boolean DEFAULT false NOT NULL,
    error_code character varying(64),
    attempts integer DEFAULT 0 NOT NULL,
    usage_tokens integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_ocr_page_attempts CHECK ((attempts >= 0)),
    CONSTRAINT ck_ocr_page_number CHECK ((page_number >= 1)),
    CONSTRAINT ck_ocr_page_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'in_flight'::character varying, 'completed'::character varying, 'blank'::character varying, 'failed'::character varying, 'uncertain'::character varying])::text[])))
);

CREATE TABLE public.ocr_spelling_defaults (
    id integer NOT NULL,
    ocr boolean NOT NULL,
    pdf_text boolean NOT NULL,
    word_text boolean NOT NULL,
    CONSTRAINT ck_ocr_spelling_defaults_singleton CHECK ((id = 1))
);

CREATE SEQUENCE public.ocr_spelling_defaults_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.ocr_spelling_defaults_id_seq OWNED BY public.ocr_spelling_defaults.id;

CREATE TABLE public.ocr_spelling_dispositions (
    id character varying(64) NOT NULL,
    run_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    check_id character varying(64) NOT NULL,
    evidence_id character varying(128) NOT NULL,
    span_start integer NOT NULL,
    span_end integer NOT NULL,
    created_by character varying(200) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_ocr_spelling_disposition_span CHECK (((span_start >= 0) AND (span_end > span_start)))
);

CREATE TABLE public.ocr_spelling_reviews (
    id character varying(64) NOT NULL,
    run_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    check_id character varying(64) NOT NULL,
    reviewed_version integer NOT NULL,
    reviewed_sha256 character varying(64) NOT NULL,
    reviewed_version_id character varying(64),
    change_count integer NOT NULL,
    reviewed_by character varying(200) NOT NULL,
    idempotency_key character varying(128) NOT NULL,
    request_hash character varying(64) NOT NULL,
    reviewed_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_ocr_spelling_review_version CHECK ((reviewed_version >= 0))
);

CREATE TABLE public.ocr_spelling_runs (
    id character varying(64) NOT NULL,
    run_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    version integer NOT NULL,
    canonical_sha256 character varying(64) NOT NULL,
    created_by character varying(200) NOT NULL,
    idempotency_key character varying(128) NOT NULL,
    request_hash character varying(64) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    status character varying(16) NOT NULL,
    checked_evidence_ids jsonb NOT NULL,
    suggestions jsonb NOT NULL,
    trace jsonb NOT NULL,
    usage_id character varying(64),
    error_code character varying(64),
    expires_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_ocr_spelling_status CHECK (((status)::text = ANY ((ARRAY['running'::character varying, 'completed'::character varying, 'failed'::character varying, 'uncertain'::character varying, 'cancelled'::character varying])::text[])))
);

CREATE TABLE public.ocr_text_versions (
    id character varying(64) NOT NULL,
    run_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    collection_id character varying(64) NOT NULL,
    version integer NOT NULL,
    canonical_sha256 character varying(64) NOT NULL,
    created_by character varying(200) NOT NULL,
    idempotency_key character varying(128) NOT NULL,
    request_hash character varying(64) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    original_sha256 character varying(64) NOT NULL,
    markdown_sha256 character varying(64) NOT NULL,
    document_key character varying(512) NOT NULL,
    markdown_key character varying(512) NOT NULL,
    changes jsonb NOT NULL,
    CONSTRAINT ck_ocr_text_version CHECK ((version > 0))
);

CREATE TABLE public.ops_actions (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    actor_ref character varying(200) NOT NULL,
    kind character varying(24) NOT NULL,
    job_id character varying(64) NOT NULL,
    action character varying(24) NOT NULL,
    status character varying(16) NOT NULL,
    reason character varying(2000) NOT NULL,
    state_sha256 character varying(64) NOT NULL,
    preview_sha256 character varying(64) NOT NULL,
    idempotency_key character varying(128),
    request_hash character varying(64),
    created_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    dispatched_at timestamp with time zone,
    CONSTRAINT ck_ops_action_status CHECK (((status)::text = ANY ((ARRAY['preview'::character varying, 'pending'::character varying, 'dispatched'::character varying, 'superseded'::character varying])::text[]))),
    CONSTRAINT ck_ops_action_type CHECK (((action)::text = ANY ((ARRAY['dispatch'::character varying, 'delete_backup'::character varying])::text[])))
);

CREATE TABLE public.ops_evidence_backups (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    created_by character varying(200) NOT NULL,
    idempotency_key character varying(128) NOT NULL,
    request_hash character varying(64) NOT NULL,
    status character varying(16) NOT NULL,
    retain_until timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    dispatched_at timestamp with time zone,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    lease_expires_at timestamp with time zone,
    worker_id character varying(120),
    blob_key character varying(512),
    sha256 character varying(64),
    size_bytes integer,
    manifest jsonb,
    error_code character varying(64),
    delete_action_id character varying(64),
    CONSTRAINT ck_ops_backup_status CHECK (((status)::text = ANY ((ARRAY['queued'::character varying, 'running'::character varying, 'completed'::character varying, 'failed'::character varying, 'uncertain'::character varying, 'deleting'::character varying, 'deleted'::character varying])::text[])))
);

CREATE TABLE public.ops_storage_cleanup_actions (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    actor_ref character varying(200) NOT NULL,
    status character varying(16) NOT NULL,
    reason character varying(2000) NOT NULL,
    target_hash character varying(64) NOT NULL,
    candidates jsonb NOT NULL,
    preview_sha256 character varying(64) NOT NULL,
    idempotency_key character varying(128),
    request_hash character varying(64),
    result jsonb,
    created_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_storage_cleanup_status CHECK (((status)::text = ANY ((ARRAY['preview'::character varying, 'pending'::character varying, 'completed'::character varying])::text[])))
);

CREATE TABLE public.provider_key_audits (
    id character varying(64) NOT NULL,
    provider_id character varying(64) NOT NULL,
    key_id character varying(64),
    actor_ref character varying(200),
    action character varying(32) NOT NULL,
    reason character varying(512),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.provider_keys (
    id character varying(64) NOT NULL,
    provider_id character varying(64) NOT NULL,
    name character varying(120) NOT NULL,
    secret_encrypted text NOT NULL,
    masked_hint character varying(16) NOT NULL,
    status character varying(32) DEFAULT 'active'::character varying NOT NULL,
    priority integer DEFAULT 5 NOT NULL,
    lease_until timestamp with time zone,
    cooldown_until timestamp with time zone,
    consecutive_failures integer DEFAULT 0 NOT NULL,
    created_by character varying(200),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    model_ids jsonb,
    CONSTRAINT ck_provider_key_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'revoked'::character varying])::text[])))
);

CREATE TABLE public.providers (
    id character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    provider_type character varying(32) NOT NULL,
    base_url character varying(1024) NOT NULL,
    model_name character varying(200) NOT NULL,
    capabilities jsonb DEFAULT '[]'::jsonb NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    priority integer DEFAULT 5 NOT NULL,
    timeout_seconds integer DEFAULT 30 NOT NULL,
    extra_config jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_by character varying(200),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_connection boolean DEFAULT false NOT NULL,
    parent_id character varying(64),
    CONSTRAINT ck_provider_type CHECK (((provider_type)::text = ANY ((ARRAY['openai_compatible'::character varying, 'gemini'::character varying, 'local'::character varying, 'mineru'::character varying, 'ollama'::character varying, 'llamacpp'::character varying])::text[])))
);

CREATE TABLE public.resource_lifecycle_actions (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    actor_ref character varying(200) NOT NULL,
    kind character varying(24) NOT NULL,
    resource_id character varying(64) NOT NULL,
    action character varying(24) NOT NULL,
    reason character varying(2000) NOT NULL,
    parameters jsonb NOT NULL,
    impact jsonb NOT NULL,
    state_sha256 character varying(64) NOT NULL,
    preview_sha256 character varying(64) NOT NULL,
    status character varying(16) NOT NULL,
    idempotency_key character varying(128),
    request_hash character varying(64),
    result jsonb,
    error_code character varying(64),
    created_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    accepted_at timestamp with time zone,
    finished_at timestamp with time zone,
    phase character varying(32),
    progress jsonb DEFAULT '{}'::jsonb NOT NULL,
    worker_id character varying(120),
    lease_expires_at timestamp with time zone,
    attempt_count integer DEFAULT 0 NOT NULL,
    last_error_at timestamp with time zone,
    confirmed_by character varying(200),
    takeover_by character varying(200),
    takeover_at timestamp with time zone,
    CONSTRAINT ck_lifecycle_action_status CHECK (((status)::text = ANY ((ARRAY['preview'::character varying, 'pending'::character varying, 'completed'::character varying, 'failed'::character varying])::text[])))
);

CREATE TABLE public.resource_lifecycle_states (
    workspace_id character varying(64) NOT NULL,
    kind character varying(24) NOT NULL,
    resource_id character varying(64) NOT NULL,
    status character varying(16) NOT NULL,
    revision integer NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_resource_lifecycle_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'archived'::character varying, 'deleted'::character varying])::text[])))
);

CREATE TABLE public.workspace_events (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    actor_ref character varying(200),
    action character varying(64) NOT NULL,
    target_type character varying(64),
    target_id character varying(64),
    detail jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.workspace_members (
    id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    actor_ref character varying(200) NOT NULL,
    display_name character varying(255),
    role character varying(32) DEFAULT 'member'::character varying NOT NULL,
    status character varying(32) DEFAULT 'active'::character varying NOT NULL,
    invited_by character varying(200),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_member_role CHECK (((role)::text = ANY ((ARRAY['admin'::character varying, 'editor'::character varying, 'reviewer'::character varying, 'member'::character varying])::text[]))),
    CONSTRAINT ck_member_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'pending'::character varying, 'revoked'::character varying])::text[])))
);

CREATE TABLE public.workspace_quotas (
    workspace_id character varying(64) NOT NULL,
    month_period date NOT NULL,
    monthly_token_limit bigint,
    tokens_used bigint DEFAULT '0'::bigint NOT NULL,
    tokens_reserved bigint DEFAULT '0'::bigint NOT NULL,
    is_blocked boolean DEFAULT false NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_quota_counters CHECK (((tokens_used >= 0) AND (tokens_reserved >= 0))),
    CONSTRAINT ck_quota_limit CHECK (((monthly_token_limit IS NULL) OR (monthly_token_limit >= 0)))
);

CREATE TABLE public.workspaces (
    id character varying(64) NOT NULL,
    code character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    status character varying(32) DEFAULT 'active'::character varying NOT NULL,
    created_by character varying(200),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_workspace_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'suspended'::character varying])::text[])))
);

ALTER TABLE ONLY public.ocr_spelling_defaults ALTER COLUMN id SET DEFAULT nextval('public.ocr_spelling_defaults_id_seq'::regclass);

ALTER TABLE ONLY public.assistant_publication_questions
    ADD CONSTRAINT assistant_publication_questions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.assistant_publications
    ADD CONSTRAINT assistant_publications_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.chat_assistants
    ADD CONSTRAINT chat_assistants_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.chat_conversations
    ADD CONSTRAINT chat_conversations_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.chat_turns
    ADD CONSTRAINT chat_turns_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_answer_review_items
    ADD CONSTRAINT kb_answer_review_items_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_answer_reviews
    ADD CONSTRAINT kb_answer_reviews_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_collections
    ADD CONSTRAINT kb_collections_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_compilation_artifacts
    ADD CONSTRAINT kb_compilation_artifacts_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_compilation_edit_previews
    ADD CONSTRAINT kb_compilation_edit_previews_child_run_id_key UNIQUE (child_run_id);

ALTER TABLE ONLY public.kb_compilation_edit_previews
    ADD CONSTRAINT kb_compilation_edit_previews_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_compilation_inputs
    ADD CONSTRAINT kb_compilation_inputs_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_compilation_outputs
    ADD CONSTRAINT kb_compilation_outputs_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_compilation_review_artifacts
    ADD CONSTRAINT kb_compilation_review_artifacts_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_compilation_review_jobs
    ADD CONSTRAINT kb_compilation_review_jobs_pkey PRIMARY KEY (compilation_run_id);

ALTER TABLE ONLY public.kb_compilation_review_segment_artifacts
    ADD CONSTRAINT kb_compilation_review_segment_artifacts_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_compilation_review_segments
    ADD CONSTRAINT kb_compilation_review_segments_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_compilation_reviews
    ADD CONSTRAINT kb_compilation_reviews_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_compilation_runs
    ADD CONSTRAINT kb_compilation_runs_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_compilation_segment_artifacts
    ADD CONSTRAINT kb_compilation_segment_artifacts_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_compilation_segments
    ADD CONSTRAINT kb_compilation_segments_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_compiled_documents
    ADD CONSTRAINT kb_compiled_documents_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_compiled_versions
    ADD CONSTRAINT kb_compiled_versions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_folders
    ADD CONSTRAINT kb_folders_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_index_chunks
    ADD CONSTRAINT kb_index_chunks_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_index_inputs
    ADD CONSTRAINT kb_index_inputs_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_index_runs
    ADD CONSTRAINT kb_index_runs_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_index_runs
    ADD CONSTRAINT kb_index_runs_vector_collection_key UNIQUE (vector_collection);

ALTER TABLE ONLY public.kb_index_sync
    ADD CONSTRAINT kb_index_sync_pkey PRIMARY KEY (collection_id);

ALTER TABLE ONLY public.kb_preparation_intents
    ADD CONSTRAINT kb_preparation_intents_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_publication_decisions
    ADD CONSTRAINT kb_publication_decisions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_publication_previews
    ADD CONSTRAINT kb_publication_previews_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_review_submission_actions
    ADD CONSTRAINT kb_review_submission_actions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_review_submission_previews
    ADD CONSTRAINT kb_review_submission_previews_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_review_submissions
    ADD CONSTRAINT kb_review_submissions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_source_revisions
    ADD CONSTRAINT kb_source_revisions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_sources
    ADD CONSTRAINT kb_sources_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.kb_upload_requests
    ADD CONSTRAINT kb_upload_requests_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.model_defaults
    ADD CONSTRAINT model_defaults_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.model_usage_records
    ADD CONSTRAINT model_usage_records_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.modelops_events
    ADD CONSTRAINT modelops_events_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ocr_processing_runs
    ADD CONSTRAINT ocr_processing_runs_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ocr_run_artifacts
    ADD CONSTRAINT ocr_run_artifacts_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ocr_run_pages
    ADD CONSTRAINT ocr_run_pages_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ocr_spelling_defaults
    ADD CONSTRAINT ocr_spelling_defaults_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ocr_spelling_dispositions
    ADD CONSTRAINT ocr_spelling_dispositions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ocr_spelling_reviews
    ADD CONSTRAINT ocr_spelling_reviews_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ocr_spelling_runs
    ADD CONSTRAINT ocr_spelling_runs_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ocr_text_versions
    ADD CONSTRAINT ocr_text_versions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ops_actions
    ADD CONSTRAINT ops_actions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ops_evidence_backups
    ADD CONSTRAINT ops_evidence_backups_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ops_storage_cleanup_actions
    ADD CONSTRAINT ops_storage_cleanup_actions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.app_api_keys
    ADD CONSTRAINT pk_app_api_keys PRIMARY KEY (id);

ALTER TABLE ONLY public.app_clients
    ADD CONSTRAINT pk_app_clients PRIMARY KEY (id);

ALTER TABLE ONLY public.app_request_logs
    ADD CONSTRAINT pk_app_request_logs PRIMARY KEY (id);

ALTER TABLE ONLY public.assistant_publication_stats
    ADD CONSTRAINT pk_assistant_publication_stats PRIMARY KEY (publication_id, day);

ALTER TABLE ONLY public.provider_key_audits
    ADD CONSTRAINT provider_key_audits_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.provider_keys
    ADD CONSTRAINT provider_keys_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.providers
    ADD CONSTRAINT providers_name_key UNIQUE (name);

ALTER TABLE ONLY public.providers
    ADD CONSTRAINT providers_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.resource_lifecycle_actions
    ADD CONSTRAINT resource_lifecycle_actions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.resource_lifecycle_states
    ADD CONSTRAINT resource_lifecycle_states_pkey PRIMARY KEY (workspace_id, kind, resource_id);

ALTER TABLE ONLY public.kb_answer_review_items
    ADD CONSTRAINT uq_answer_review_item_ordinal UNIQUE (review_id, ordinal);

ALTER TABLE ONLY public.kb_answer_reviews
    ADD CONSTRAINT uq_answer_review_request UNIQUE (workspace_id, requested_by, idempotency_key);

ALTER TABLE ONLY public.kb_answer_reviews
    ADD CONSTRAINT uq_answer_review_scope UNIQUE (id, workspace_id, collection_id);

ALTER TABLE ONLY public.app_api_keys
    ADD CONSTRAINT uq_app_key_hash UNIQUE (key_hash);

ALTER TABLE ONLY public.assistant_publications
    ADD CONSTRAINT uq_assistant_publication_assistant UNIQUE (assistant_id);

ALTER TABLE ONLY public.assistant_publications
    ADD CONSTRAINT uq_assistant_publication_slug UNIQUE (slug);

ALTER TABLE ONLY public.chat_assistants
    ADD CONSTRAINT uq_chat_assistant_scope UNIQUE (id, workspace_id, collection_id);

ALTER TABLE ONLY public.chat_conversations
    ADD CONSTRAINT uq_chat_conversation_scope UNIQUE (id, workspace_id, collection_id);

ALTER TABLE ONLY public.chat_turns
    ADD CONSTRAINT uq_chat_turn_request UNIQUE (conversation_id, idempotency_key);

ALTER TABLE ONLY public.chat_turns
    ADD CONSTRAINT uq_chat_turn_sequence UNIQUE (conversation_id, turn_no);

ALTER TABLE ONLY public.kb_compilation_artifacts
    ADD CONSTRAINT uq_compilation_artifact_kind UNIQUE (run_id, kind);

ALTER TABLE ONLY public.kb_compilation_runs
    ADD CONSTRAINT uq_compilation_generation UNIQUE (collection_id, generation);

ALTER TABLE ONLY public.kb_compilation_inputs
    ADD CONSTRAINT uq_compilation_input_ocr UNIQUE (run_id, ocr_run_id);

ALTER TABLE ONLY public.kb_compilation_outputs
    ADD CONSTRAINT uq_compilation_output_generation UNIQUE (run_id, generation);

ALTER TABLE ONLY public.kb_compilation_runs
    ADD CONSTRAINT uq_compilation_request UNIQUE (workspace_id, requested_by, idempotency_key);

ALTER TABLE ONLY public.kb_compilation_review_artifacts
    ADD CONSTRAINT uq_compilation_review_artifact UNIQUE (review_id, kind);

ALTER TABLE ONLY public.kb_compilation_reviews
    ADD CONSTRAINT uq_compilation_review_request UNIQUE (workspace_id, created_by, idempotency_key);

ALTER TABLE ONLY public.kb_compilation_review_segment_artifacts
    ADD CONSTRAINT uq_compilation_review_segment_artifact UNIQUE (segment_id, kind);

ALTER TABLE ONLY public.kb_compilation_review_segments
    ADD CONSTRAINT uq_compilation_review_segment_index UNIQUE (review_id, segment_index);

ALTER TABLE ONLY public.kb_compilation_runs
    ADD CONSTRAINT uq_compilation_scope UNIQUE (id, workspace_id, collection_id);

ALTER TABLE ONLY public.kb_compilation_segment_artifacts
    ADD CONSTRAINT uq_compilation_segment_artifact UNIQUE (segment_id, kind);

ALTER TABLE ONLY public.kb_compilation_segments
    ADD CONSTRAINT uq_compilation_segment_index UNIQUE (run_id, segment_index);

ALTER TABLE ONLY public.kb_compiled_documents
    ADD CONSTRAINT uq_compiled_document_key UNIQUE (workspace_id, collection_id, document_key);

ALTER TABLE ONLY public.kb_compiled_documents
    ADD CONSTRAINT uq_compiled_document_scope UNIQUE (id, workspace_id, collection_id);

ALTER TABLE ONLY public.kb_compiled_versions
    ADD CONSTRAINT uq_compiled_registration UNIQUE (workspace_id, created_by, idempotency_key);

ALTER TABLE ONLY public.kb_compiled_versions
    ADD CONSTRAINT uq_compiled_version_no UNIQUE (document_id, version_no);

ALTER TABLE ONLY public.kb_compiled_versions
    ADD CONSTRAINT uq_compiled_version_run UNIQUE (compilation_run_id);

ALTER TABLE ONLY public.kb_compiled_versions
    ADD CONSTRAINT uq_compiled_version_scope UNIQUE (id, document_id, workspace_id, collection_id);

ALTER TABLE ONLY public.kb_index_chunks
    ADD CONSTRAINT uq_index_chunk_ordinal UNIQUE (run_id, ordinal);

ALTER TABLE ONLY public.kb_index_chunks
    ADD CONSTRAINT uq_index_chunk_point UNIQUE (point_id);

ALTER TABLE ONLY public.kb_index_runs
    ADD CONSTRAINT uq_index_generation UNIQUE (collection_id, generation);

ALTER TABLE ONLY public.kb_index_inputs
    ADD CONSTRAINT uq_index_input_document UNIQUE (run_id, document_id);

ALTER TABLE ONLY public.kb_index_inputs
    ADD CONSTRAINT uq_index_input_scope UNIQUE (id, run_id, workspace_id, collection_id);

ALTER TABLE ONLY public.kb_index_runs
    ADD CONSTRAINT uq_index_request UNIQUE (workspace_id, requested_by, idempotency_key);

ALTER TABLE ONLY public.kb_index_runs
    ADD CONSTRAINT uq_index_run_scope UNIQUE (id, workspace_id, collection_id);

ALTER TABLE ONLY public.kb_collections
    ADD CONSTRAINT uq_kb_collection_name UNIQUE (workspace_id, name);

ALTER TABLE ONLY public.kb_collections
    ADD CONSTRAINT uq_kb_collection_scope UNIQUE (id, workspace_id);

ALTER TABLE ONLY public.kb_folders
    ADD CONSTRAINT uq_kb_folder_scope UNIQUE (id, collection_id, workspace_id);

ALTER TABLE ONLY public.kb_source_revisions
    ADD CONSTRAINT uq_kb_revision_content UNIQUE (collection_id, sha256);

ALTER TABLE ONLY public.kb_source_revisions
    ADD CONSTRAINT uq_kb_revision_no UNIQUE (source_id, revision_no);

ALTER TABLE ONLY public.kb_source_revisions
    ADD CONSTRAINT uq_kb_revision_scope UNIQUE (id, source_id, collection_id, workspace_id);

ALTER TABLE ONLY public.kb_source_revisions
    ADD CONSTRAINT uq_kb_revision_storage_key UNIQUE (storage_key);

ALTER TABLE ONLY public.kb_sources
    ADD CONSTRAINT uq_kb_source_scope UNIQUE (id, collection_id, workspace_id);

ALTER TABLE ONLY public.kb_upload_requests
    ADD CONSTRAINT uq_kb_upload_idempotency UNIQUE (workspace_id, actor_ref, idempotency_key);

ALTER TABLE ONLY public.resource_lifecycle_actions
    ADD CONSTRAINT uq_lifecycle_request UNIQUE (workspace_id, actor_ref, idempotency_key);

ALTER TABLE ONLY public.model_usage_records
    ADD CONSTRAINT uq_model_usage_request UNIQUE (workspace_id, request_id);

ALTER TABLE ONLY public.ocr_run_artifacts
    ADD CONSTRAINT uq_ocr_artifact_kind_page UNIQUE (run_id, kind, page_no);

ALTER TABLE ONLY public.ocr_run_pages
    ADD CONSTRAINT uq_ocr_page_number UNIQUE (run_id, page_number);

ALTER TABLE ONLY public.ocr_processing_runs
    ADD CONSTRAINT uq_ocr_run_generation UNIQUE (revision_id, generation);

ALTER TABLE ONLY public.ocr_processing_runs
    ADD CONSTRAINT uq_ocr_run_scope UNIQUE (id, workspace_id, collection_id);

ALTER TABLE ONLY public.ocr_spelling_dispositions
    ADD CONSTRAINT uq_ocr_spelling_disposition UNIQUE (check_id, evidence_id, span_start, span_end);

ALTER TABLE ONLY public.ocr_spelling_runs
    ADD CONSTRAINT uq_ocr_spelling_request UNIQUE (workspace_id, created_by, idempotency_key);

ALTER TABLE ONLY public.ocr_spelling_reviews
    ADD CONSTRAINT uq_ocr_spelling_review_check UNIQUE (check_id);

ALTER TABLE ONLY public.ocr_spelling_reviews
    ADD CONSTRAINT uq_ocr_spelling_review_request UNIQUE (workspace_id, reviewed_by, idempotency_key);

ALTER TABLE ONLY public.ocr_text_versions
    ADD CONSTRAINT uq_ocr_text_request UNIQUE (workspace_id, created_by, idempotency_key);

ALTER TABLE ONLY public.ocr_text_versions
    ADD CONSTRAINT uq_ocr_text_scope UNIQUE (id, run_id, workspace_id, collection_id);

ALTER TABLE ONLY public.ocr_text_versions
    ADD CONSTRAINT uq_ocr_text_version UNIQUE (run_id, version);

ALTER TABLE ONLY public.ops_actions
    ADD CONSTRAINT uq_ops_action_request UNIQUE (workspace_id, actor_ref, idempotency_key);

ALTER TABLE ONLY public.ops_evidence_backups
    ADD CONSTRAINT uq_ops_backup_request UNIQUE (workspace_id, created_by, idempotency_key);

ALTER TABLE ONLY public.kb_preparation_intents
    ADD CONSTRAINT uq_preparation_idempotency UNIQUE (workspace_id, requested_by, idempotency_key);

ALTER TABLE ONLY public.kb_preparation_intents
    ADD CONSTRAINT uq_preparation_scope UNIQUE (id, workspace_id, collection_id);

ALTER TABLE ONLY public.kb_publication_decisions
    ADD CONSTRAINT uq_publication_decision_preview UNIQUE (preview_id);

ALTER TABLE ONLY public.kb_publication_decisions
    ADD CONSTRAINT uq_publication_decision_request UNIQUE (workspace_id, actor_ref, idempotency_key);

ALTER TABLE ONLY public.kb_publication_decisions
    ADD CONSTRAINT uq_publication_decision_scope UNIQUE (id, version_id, document_id, workspace_id, collection_id);

ALTER TABLE ONLY public.kb_publication_decisions
    ADD CONSTRAINT uq_publication_decision_sequence UNIQUE (document_id, document_sequence);

ALTER TABLE ONLY public.kb_publication_previews
    ADD CONSTRAINT uq_publication_preview_scope UNIQUE (id, version_id, document_id, workspace_id, collection_id);

ALTER TABLE ONLY public.assistant_publication_questions
    ADD CONSTRAINT uq_publication_question_hash UNIQUE (publication_id, question_hash);

ALTER TABLE ONLY public.kb_review_submission_actions
    ADD CONSTRAINT uq_review_action_decision UNIQUE (publication_decision_id);

ALTER TABLE ONLY public.kb_review_submission_actions
    ADD CONSTRAINT uq_review_action_idempotency UNIQUE (workspace_id, actor_ref, idempotency_key);

ALTER TABLE ONLY public.kb_review_submission_actions
    ADD CONSTRAINT uq_review_action_preview UNIQUE (preview_id);

ALTER TABLE ONLY public.kb_review_submission_previews
    ADD CONSTRAINT uq_review_preview_scope UNIQUE (id, workspace_id, collection_id);

ALTER TABLE ONLY public.kb_review_submissions
    ADD CONSTRAINT uq_review_submission_scope UNIQUE (id, workspace_id, collection_id);

ALTER TABLE ONLY public.ops_storage_cleanup_actions
    ADD CONSTRAINT uq_storage_cleanup_request UNIQUE (workspace_id, actor_ref, idempotency_key);

ALTER TABLE ONLY public.workspace_members
    ADD CONSTRAINT uq_workspace_member UNIQUE (workspace_id, actor_ref);

ALTER TABLE ONLY public.workspace_events
    ADD CONSTRAINT workspace_events_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.workspace_members
    ADD CONSTRAINT workspace_members_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.workspace_quotas
    ADD CONSTRAINT workspace_quotas_pkey PRIMARY KEY (workspace_id, month_period);

ALTER TABLE ONLY public.workspaces
    ADD CONSTRAINT workspaces_pkey PRIMARY KEY (id);

CREATE INDEX ix_answer_review_assistant ON public.kb_answer_reviews USING btree (workspace_id, assistant_id, created_at);

CREATE INDEX ix_app_api_keys_app_id ON public.app_api_keys USING btree (app_id);

CREATE UNIQUE INDEX ix_app_api_keys_idempotency_key ON public.app_api_keys USING btree (workspace_id, idempotency_key) WHERE (idempotency_key IS NOT NULL);

CREATE INDEX ix_app_api_keys_workspace_id ON public.app_api_keys USING btree (workspace_id);

CREATE INDEX ix_app_clients_workspace_id ON public.app_clients USING btree (workspace_id);

CREATE INDEX ix_app_request_logs_app_id ON public.app_request_logs USING btree (app_id, created_at);

CREATE INDEX ix_app_request_logs_key_id ON public.app_request_logs USING btree (key_id, created_at);

CREATE INDEX ix_app_request_logs_workspace_id ON public.app_request_logs USING btree (workspace_id, created_at);

CREATE INDEX ix_compilation_reuse_key ON public.kb_compilation_runs USING btree (((config ->> 'reuse_key'::text))) WHERE (config ? 'reuse_key'::text);

CREATE INDEX ix_kb_collections_workspace_id ON public.kb_collections USING btree (workspace_id);

CREATE INDEX ix_kb_compilation_artifacts_run_id ON public.kb_compilation_artifacts USING btree (run_id);

CREATE INDEX ix_kb_compilation_edit_previews_compilation_run_id ON public.kb_compilation_edit_previews USING btree (compilation_run_id);

CREATE INDEX ix_kb_compilation_inputs_run_id ON public.kb_compilation_inputs USING btree (run_id);

CREATE INDEX ix_kb_compilation_outputs_run_id ON public.kb_compilation_outputs USING btree (run_id);

CREATE INDEX ix_kb_compilation_review_artifacts_review_id ON public.kb_compilation_review_artifacts USING btree (review_id);

CREATE INDEX ix_kb_compilation_review_jobs_status ON public.kb_compilation_review_jobs USING btree (status);

CREATE INDEX ix_kb_compilation_review_segment_artifacts_segment_id ON public.kb_compilation_review_segment_artifacts USING btree (segment_id);

CREATE INDEX ix_kb_compilation_review_segments_parent_segment_id ON public.kb_compilation_review_segments USING btree (parent_segment_id);

CREATE INDEX ix_kb_compilation_review_segments_review_id ON public.kb_compilation_review_segments USING btree (review_id);

CREATE INDEX ix_kb_compilation_review_segments_status ON public.kb_compilation_review_segments USING btree (status);

CREATE INDEX ix_kb_compilation_reviews_compilation_run_id ON public.kb_compilation_reviews USING btree (compilation_run_id);

CREATE INDEX ix_kb_compilation_reviews_workspace_id ON public.kb_compilation_reviews USING btree (workspace_id);

CREATE INDEX ix_kb_compilation_runs_collection_id ON public.kb_compilation_runs USING btree (collection_id);

CREATE INDEX ix_kb_compilation_runs_status ON public.kb_compilation_runs USING btree (status);

CREATE INDEX ix_kb_compilation_runs_workspace_id ON public.kb_compilation_runs USING btree (workspace_id);

CREATE INDEX ix_kb_compilation_segment_artifacts_segment_id ON public.kb_compilation_segment_artifacts USING btree (segment_id);

CREATE INDEX ix_kb_compilation_segments_parent_segment_id ON public.kb_compilation_segments USING btree (parent_segment_id);

CREATE INDEX ix_kb_compilation_segments_run_id ON public.kb_compilation_segments USING btree (run_id);

CREATE INDEX ix_kb_compilation_segments_status ON public.kb_compilation_segments USING btree (status);

CREATE INDEX ix_kb_compiled_versions_document_id ON public.kb_compiled_versions USING btree (document_id);

CREATE INDEX ix_kb_folders_collection_id ON public.kb_folders USING btree (collection_id);

CREATE INDEX ix_kb_folders_parent_id ON public.kb_folders USING btree (parent_id);

CREATE INDEX ix_kb_folders_workspace_id ON public.kb_folders USING btree (workspace_id);

CREATE INDEX ix_kb_index_chunks_fts ON public.kb_index_chunks USING gin (to_tsvector('simple'::regconfig, text));

CREATE INDEX ix_kb_index_chunks_run_id ON public.kb_index_chunks USING btree (run_id);

CREATE INDEX ix_kb_index_inputs_run_id ON public.kb_index_inputs USING btree (run_id);

CREATE INDEX ix_kb_preparation_intents_compilation_run_id ON public.kb_preparation_intents USING btree (compilation_run_id);

CREATE INDEX ix_kb_preparation_intents_ocr_run_id ON public.kb_preparation_intents USING btree (ocr_run_id);

CREATE INDEX ix_kb_preparation_intents_workspace_id ON public.kb_preparation_intents USING btree (workspace_id);

CREATE INDEX ix_kb_publication_decisions_document_id ON public.kb_publication_decisions USING btree (document_id);

CREATE INDEX ix_kb_review_submissions_workspace_id ON public.kb_review_submissions USING btree (workspace_id);

CREATE INDEX ix_kb_sources_collection_id ON public.kb_sources USING btree (collection_id);

CREATE INDEX ix_kb_sources_folder_id ON public.kb_sources USING btree (folder_id);

CREATE INDEX ix_kb_sources_workspace_id ON public.kb_sources USING btree (workspace_id);

CREATE INDEX ix_model_usage_records_workspace_id ON public.model_usage_records USING btree (workspace_id);

CREATE INDEX ix_ocr_processing_runs_revision_id ON public.ocr_processing_runs USING btree (revision_id);

CREATE INDEX ix_ocr_processing_runs_status ON public.ocr_processing_runs USING btree (status);

CREATE INDEX ix_ocr_processing_runs_workspace_id ON public.ocr_processing_runs USING btree (workspace_id);

CREATE INDEX ix_ocr_run_artifacts_run_id ON public.ocr_run_artifacts USING btree (run_id);

CREATE INDEX ix_ocr_run_pages_run_id ON public.ocr_run_pages USING btree (run_id);

CREATE INDEX ix_ocr_runs_workspace_status ON public.ocr_processing_runs USING btree (workspace_id, status);

CREATE INDEX ix_ocr_spelling_dispositions_check_id ON public.ocr_spelling_dispositions USING btree (check_id);

CREATE INDEX ix_ocr_spelling_reviews_run_id ON public.ocr_spelling_reviews USING btree (run_id);

CREATE INDEX ix_ocr_spelling_runs_run_id ON public.ocr_spelling_runs USING btree (run_id);

CREATE INDEX ix_ocr_text_versions_run_id ON public.ocr_text_versions USING btree (run_id);

CREATE INDEX ix_ops_actions_workspace_id ON public.ops_actions USING btree (workspace_id);

CREATE INDEX ix_ops_evidence_backups_workspace_id ON public.ops_evidence_backups USING btree (workspace_id);

CREATE INDEX ix_ops_storage_cleanup_actions_workspace_id ON public.ops_storage_cleanup_actions USING btree (workspace_id);

CREATE INDEX ix_preparation_source_created ON public.kb_preparation_intents USING btree (source_id, created_at);

CREATE INDEX ix_preparation_status_lease ON public.kb_preparation_intents USING btree (status, lease_expires_at);

CREATE INDEX ix_provider_key_audits_key_id ON public.provider_key_audits USING btree (key_id);

CREATE INDEX ix_provider_key_audits_provider_id ON public.provider_key_audits USING btree (provider_id);

CREATE INDEX ix_provider_keys_provider_id ON public.provider_keys USING btree (provider_id);

CREATE INDEX ix_provider_keys_status ON public.provider_keys USING btree (status);

CREATE INDEX ix_providers_is_active ON public.providers USING btree (is_active);

CREATE INDEX ix_providers_is_connection ON public.providers USING btree (is_connection);

CREATE INDEX ix_providers_parent_id ON public.providers USING btree (parent_id);

CREATE INDEX ix_resource_lifecycle_actions_workspace_id ON public.resource_lifecycle_actions USING btree (workspace_id);

CREATE INDEX ix_review_action_submission ON public.kb_review_submission_actions USING btree (submission_id, created_at);

CREATE INDEX ix_review_preview_created ON public.kb_review_submission_previews USING btree (workspace_id, collection_id, created_at);

CREATE INDEX ix_review_submission_document ON public.kb_review_submissions USING btree (document_id, version_id, submitted_at);

CREATE INDEX ix_review_submission_worklist ON public.kb_review_submissions USING btree (workspace_id, collection_id, status, submitted_at);

CREATE INDEX ix_workspace_events_action ON public.workspace_events USING btree (action);

CREATE INDEX ix_workspace_events_created_at ON public.workspace_events USING btree (created_at);

CREATE INDEX ix_workspace_events_workspace_id ON public.workspace_events USING btree (workspace_id);

CREATE INDEX ix_workspace_members_actor_ref ON public.workspace_members USING btree (actor_ref);

CREATE INDEX ix_workspace_members_status ON public.workspace_members USING btree (status);

CREATE INDEX ix_workspace_members_workspace_id ON public.workspace_members USING btree (workspace_id);

CREATE UNIQUE INDEX ix_workspaces_code ON public.workspaces USING btree (code);

CREATE INDEX ix_workspaces_status ON public.workspaces USING btree (status);

CREATE UNIQUE INDEX uq_chat_turn_running ON public.chat_turns USING btree (conversation_id) WHERE ((status)::text = 'running'::text);

CREATE UNIQUE INDEX uq_compiled_document_published ON public.kb_compiled_versions USING btree (document_id) WHERE ((status)::text = 'published'::text);

CREATE UNIQUE INDEX uq_index_active ON public.kb_index_runs USING btree (collection_id) WHERE (is_active = true);

CREATE UNIQUE INDEX uq_index_working ON public.kb_index_runs USING btree (collection_id) WHERE ((status)::text = ANY ((ARRAY['queued'::character varying, 'running'::character varying])::text[]));

CREATE UNIQUE INDEX uq_ocr_run_active ON public.ocr_processing_runs USING btree (revision_id) WHERE ((status)::text = ANY (ARRAY[('queued'::character varying)::text, ('running'::character varying)::text]));

CREATE UNIQUE INDEX uq_review_submission_pending ON public.kb_review_submissions USING btree (version_id) WHERE ((status)::text = 'pending'::text);

ALTER TABLE ONLY public.chat_assistants
    ADD CONSTRAINT chat_assistants_chat_provider_id_fkey FOREIGN KEY (chat_provider_id) REFERENCES public.providers(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_answer_reviews
    ADD CONSTRAINT fk_answer_review_assistant FOREIGN KEY (assistant_id, workspace_id, collection_id) REFERENCES public.chat_assistants(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_answer_review_items
    ADD CONSTRAINT fk_answer_review_item_review FOREIGN KEY (review_id, workspace_id, collection_id) REFERENCES public.kb_answer_reviews(id, workspace_id, collection_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.app_clients
    ADD CONSTRAINT fk_app_client_workspace FOREIGN KEY (workspace_id) REFERENCES public.workspaces(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.app_api_keys
    ADD CONSTRAINT fk_app_key_client FOREIGN KEY (app_id) REFERENCES public.app_clients(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.app_api_keys
    ADD CONSTRAINT fk_app_key_workspace FOREIGN KEY (workspace_id) REFERENCES public.workspaces(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.assistant_publications
    ADD CONSTRAINT fk_assistant_publication_assistant FOREIGN KEY (assistant_id) REFERENCES public.chat_assistants(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.chat_assistants
    ADD CONSTRAINT fk_chat_assistant_collection FOREIGN KEY (collection_id, workspace_id) REFERENCES public.kb_collections(id, workspace_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.chat_conversations
    ADD CONSTRAINT fk_chat_conversation_assistant FOREIGN KEY (assistant_id, workspace_id, collection_id) REFERENCES public.chat_assistants(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.chat_turns
    ADD CONSTRAINT fk_chat_turn_conversation FOREIGN KEY (conversation_id, workspace_id, collection_id) REFERENCES public.chat_conversations(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_runs
    ADD CONSTRAINT fk_compilation_collection FOREIGN KEY (collection_id, workspace_id) REFERENCES public.kb_collections(id, workspace_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_edit_previews
    ADD CONSTRAINT fk_compilation_edit_scope FOREIGN KEY (compilation_run_id, workspace_id, collection_id) REFERENCES public.kb_compilation_runs(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_inputs
    ADD CONSTRAINT fk_compilation_input_ocr FOREIGN KEY (ocr_run_id, workspace_id, collection_id) REFERENCES public.ocr_processing_runs(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_inputs
    ADD CONSTRAINT fk_compilation_input_run FOREIGN KEY (run_id, workspace_id, collection_id) REFERENCES public.kb_compilation_runs(id, workspace_id, collection_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kb_compilation_inputs
    ADD CONSTRAINT fk_compilation_input_text FOREIGN KEY (text_version_id, ocr_run_id, workspace_id, collection_id) REFERENCES public.ocr_text_versions(id, run_id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_runs
    ADD CONSTRAINT fk_compilation_parent FOREIGN KEY (parent_run_id, workspace_id, collection_id) REFERENCES public.kb_compilation_runs(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_review_jobs
    ADD CONSTRAINT fk_compilation_review_job_scope FOREIGN KEY (compilation_run_id, workspace_id, collection_id) REFERENCES public.kb_compilation_runs(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_reviews
    ADD CONSTRAINT fk_compilation_review_scope FOREIGN KEY (compilation_run_id, workspace_id, collection_id) REFERENCES public.kb_compilation_runs(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compiled_documents
    ADD CONSTRAINT fk_compiled_document_collection FOREIGN KEY (collection_id, workspace_id) REFERENCES public.kb_collections(id, workspace_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compiled_versions
    ADD CONSTRAINT fk_compiled_version_document FOREIGN KEY (document_id, workspace_id, collection_id) REFERENCES public.kb_compiled_documents(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compiled_versions
    ADD CONSTRAINT fk_compiled_version_run FOREIGN KEY (compilation_run_id, workspace_id, collection_id) REFERENCES public.kb_compilation_runs(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_segments
    ADD CONSTRAINT fk_compiler_parent FOREIGN KEY (parent_segment_id) REFERENCES public.kb_compilation_segments(id);

ALTER TABLE ONLY public.kb_index_chunks
    ADD CONSTRAINT fk_index_chunk_input FOREIGN KEY (input_id, run_id, workspace_id, collection_id) REFERENCES public.kb_index_inputs(id, run_id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_index_inputs
    ADD CONSTRAINT fk_index_input_publication FOREIGN KEY (publication_decision_id, version_id, document_id, workspace_id, collection_id) REFERENCES public.kb_publication_decisions(id, version_id, document_id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_index_inputs
    ADD CONSTRAINT fk_index_input_run FOREIGN KEY (run_id, workspace_id, collection_id) REFERENCES public.kb_index_runs(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_index_runs
    ADD CONSTRAINT fk_index_run_collection FOREIGN KEY (collection_id, workspace_id) REFERENCES public.kb_collections(id, workspace_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_folders
    ADD CONSTRAINT fk_kb_folder_collection FOREIGN KEY (collection_id, workspace_id) REFERENCES public.kb_collections(id, workspace_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kb_folders
    ADD CONSTRAINT fk_kb_folder_parent FOREIGN KEY (parent_id) REFERENCES public.kb_folders(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kb_source_revisions
    ADD CONSTRAINT fk_kb_revision_source FOREIGN KEY (source_id, collection_id, workspace_id) REFERENCES public.kb_sources(id, collection_id, workspace_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kb_sources
    ADD CONSTRAINT fk_kb_source_collection FOREIGN KEY (collection_id, workspace_id) REFERENCES public.kb_collections(id, workspace_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kb_sources
    ADD CONSTRAINT fk_kb_source_folder FOREIGN KEY (folder_id) REFERENCES public.kb_folders(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.ocr_processing_runs
    ADD CONSTRAINT fk_ocr_run_revision FOREIGN KEY (revision_id, source_id, collection_id, workspace_id) REFERENCES public.kb_source_revisions(id, source_id, collection_id, workspace_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.ocr_spelling_dispositions
    ADD CONSTRAINT fk_ocr_spelling_disposition_check FOREIGN KEY (check_id) REFERENCES public.ocr_spelling_runs(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.ocr_spelling_dispositions
    ADD CONSTRAINT fk_ocr_spelling_disposition_run FOREIGN KEY (run_id, workspace_id, collection_id) REFERENCES public.ocr_processing_runs(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.ocr_spelling_reviews
    ADD CONSTRAINT fk_ocr_spelling_review_check FOREIGN KEY (check_id) REFERENCES public.ocr_spelling_runs(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.ocr_spelling_reviews
    ADD CONSTRAINT fk_ocr_spelling_review_run FOREIGN KEY (run_id, workspace_id, collection_id) REFERENCES public.ocr_processing_runs(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.ocr_spelling_reviews
    ADD CONSTRAINT fk_ocr_spelling_review_version FOREIGN KEY (reviewed_version_id) REFERENCES public.ocr_text_versions(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.ocr_spelling_runs
    ADD CONSTRAINT fk_ocr_spelling_run FOREIGN KEY (run_id, workspace_id, collection_id) REFERENCES public.ocr_processing_runs(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.ocr_text_versions
    ADD CONSTRAINT fk_ocr_text_run FOREIGN KEY (run_id, workspace_id, collection_id) REFERENCES public.ocr_processing_runs(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_preparation_intents
    ADD CONSTRAINT fk_preparation_revision FOREIGN KEY (revision_id, source_id, collection_id, workspace_id) REFERENCES public.kb_source_revisions(id, source_id, collection_id, workspace_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kb_preparation_intents
    ADD CONSTRAINT fk_preparation_source FOREIGN KEY (source_id, collection_id, workspace_id) REFERENCES public.kb_sources(id, collection_id, workspace_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.providers
    ADD CONSTRAINT fk_provider_parent FOREIGN KEY (parent_id) REFERENCES public.providers(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_publication_decisions
    ADD CONSTRAINT fk_publication_decision_preview FOREIGN KEY (preview_id, version_id, document_id, workspace_id, collection_id) REFERENCES public.kb_publication_previews(id, version_id, document_id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_publication_previews
    ADD CONSTRAINT fk_publication_preview_version FOREIGN KEY (version_id, document_id, workspace_id, collection_id) REFERENCES public.kb_compiled_versions(id, document_id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.assistant_publication_questions
    ADD CONSTRAINT fk_publication_questions_publication FOREIGN KEY (publication_id) REFERENCES public.assistant_publications(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.assistant_publication_stats
    ADD CONSTRAINT fk_publication_stats_publication FOREIGN KEY (publication_id) REFERENCES public.assistant_publications(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kb_review_submission_actions
    ADD CONSTRAINT fk_review_action_preview FOREIGN KEY (preview_id, workspace_id, collection_id) REFERENCES public.kb_review_submission_previews(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_review_submission_actions
    ADD CONSTRAINT fk_review_action_submission FOREIGN KEY (submission_id, workspace_id, collection_id) REFERENCES public.kb_review_submissions(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_review_submission_previews
    ADD CONSTRAINT fk_review_preview_submission FOREIGN KEY (submission_id, workspace_id, collection_id) REFERENCES public.kb_review_submissions(id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_review_submission_previews
    ADD CONSTRAINT fk_review_preview_version FOREIGN KEY (version_id, document_id, workspace_id, collection_id) REFERENCES public.kb_compiled_versions(id, document_id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_review_segments
    ADD CONSTRAINT fk_review_segment_parent FOREIGN KEY (parent_segment_id) REFERENCES public.kb_compilation_review_segments(id);

ALTER TABLE ONLY public.kb_review_submissions
    ADD CONSTRAINT fk_review_submission_collection FOREIGN KEY (collection_id, workspace_id) REFERENCES public.kb_collections(id, workspace_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_review_submissions
    ADD CONSTRAINT fk_review_submission_version FOREIGN KEY (version_id, document_id, workspace_id, collection_id) REFERENCES public.kb_compiled_versions(id, document_id, workspace_id, collection_id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_collections
    ADD CONSTRAINT kb_collections_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kb_compilation_artifacts
    ADD CONSTRAINT kb_compilation_artifacts_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.kb_compilation_runs(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kb_compilation_edit_previews
    ADD CONSTRAINT kb_compilation_edit_previews_child_run_id_fkey FOREIGN KEY (child_run_id) REFERENCES public.kb_compilation_runs(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_edit_previews
    ADD CONSTRAINT kb_compilation_edit_previews_review_id_fkey FOREIGN KEY (review_id) REFERENCES public.kb_compilation_reviews(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_outputs
    ADD CONSTRAINT kb_compilation_outputs_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.kb_compilation_runs(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kb_compilation_review_artifacts
    ADD CONSTRAINT kb_compilation_review_artifacts_review_id_fkey FOREIGN KEY (review_id) REFERENCES public.kb_compilation_reviews(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_review_jobs
    ADD CONSTRAINT kb_compilation_review_jobs_review_id_fkey FOREIGN KEY (review_id) REFERENCES public.kb_compilation_reviews(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_review_segment_artifacts
    ADD CONSTRAINT kb_compilation_review_segment_artifacts_segment_id_fkey FOREIGN KEY (segment_id) REFERENCES public.kb_compilation_review_segments(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kb_compilation_review_segments
    ADD CONSTRAINT kb_compilation_review_segments_review_id_fkey FOREIGN KEY (review_id) REFERENCES public.kb_compilation_reviews(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kb_compilation_review_segments
    ADD CONSTRAINT kb_compilation_review_segments_usage_id_fkey FOREIGN KEY (usage_id) REFERENCES public.model_usage_records(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_reviews
    ADD CONSTRAINT kb_compilation_reviews_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.providers(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_reviews
    ADD CONSTRAINT kb_compilation_reviews_usage_id_fkey FOREIGN KEY (usage_id) REFERENCES public.model_usage_records(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_runs
    ADD CONSTRAINT kb_compilation_runs_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.providers(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_runs
    ADD CONSTRAINT kb_compilation_runs_usage_id_fkey FOREIGN KEY (usage_id) REFERENCES public.model_usage_records(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_compilation_segment_artifacts
    ADD CONSTRAINT kb_compilation_segment_artifacts_segment_id_fkey FOREIGN KEY (segment_id) REFERENCES public.kb_compilation_segments(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kb_compilation_segments
    ADD CONSTRAINT kb_compilation_segments_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.kb_compilation_runs(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kb_compilation_segments
    ADD CONSTRAINT kb_compilation_segments_usage_id_fkey FOREIGN KEY (usage_id) REFERENCES public.model_usage_records(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_index_runs
    ADD CONSTRAINT kb_index_runs_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.providers(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_index_sync
    ADD CONSTRAINT kb_index_sync_collection_id_workspace_id_fkey FOREIGN KEY (collection_id, workspace_id) REFERENCES public.kb_collections(id, workspace_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.kb_index_sync
    ADD CONSTRAINT kb_index_sync_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.kb_index_runs(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.kb_preparation_intents
    ADD CONSTRAINT kb_preparation_intents_compilation_run_id_fkey FOREIGN KEY (compilation_run_id) REFERENCES public.kb_compilation_runs(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_preparation_intents
    ADD CONSTRAINT kb_preparation_intents_ocr_run_id_fkey FOREIGN KEY (ocr_run_id) REFERENCES public.ocr_processing_runs(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.kb_review_submission_actions
    ADD CONSTRAINT kb_review_submission_actions_publication_decision_id_fkey FOREIGN KEY (publication_decision_id) REFERENCES public.kb_publication_decisions(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.model_usage_records
    ADD CONSTRAINT model_usage_records_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.providers(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.model_usage_records
    ADD CONSTRAINT model_usage_records_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.ocr_run_artifacts
    ADD CONSTRAINT ocr_run_artifacts_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.ocr_processing_runs(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.ocr_run_pages
    ADD CONSTRAINT ocr_run_pages_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.ocr_processing_runs(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.ops_actions
    ADD CONSTRAINT ops_actions_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.ops_evidence_backups
    ADD CONSTRAINT ops_evidence_backups_delete_action_id_fkey FOREIGN KEY (delete_action_id) REFERENCES public.ops_actions(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.ops_evidence_backups
    ADD CONSTRAINT ops_evidence_backups_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.ops_storage_cleanup_actions
    ADD CONSTRAINT ops_storage_cleanup_actions_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.provider_key_audits
    ADD CONSTRAINT provider_key_audits_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.providers(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.provider_keys
    ADD CONSTRAINT provider_keys_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.providers(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.resource_lifecycle_actions
    ADD CONSTRAINT resource_lifecycle_actions_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.resource_lifecycle_states
    ADD CONSTRAINT resource_lifecycle_states_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.workspace_events
    ADD CONSTRAINT workspace_events_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.workspace_members
    ADD CONSTRAINT workspace_members_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.workspace_quotas
    ADD CONSTRAINT workspace_quotas_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(id) ON DELETE RESTRICT;
