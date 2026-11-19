"""Ownership boundaries between the legacy schema and backendV1.

The legacy backend keeps owning every table it created. backendV1 may only
create or migrate tables that are absent from this snapshot; anything listed
here must never appear in a v1 autogenerate diff.
"""

from __future__ import annotations

from typing import Any

LEGACY_TABLES: frozenset[str] = frozenset(
    {
        "assistant_versions",
        "assistants",
        "conversation_feedbacks",
        "conversation_messages",
        "conversation_threads",
        "document_group_memberships",
        "document_groups",
        "document_revisions",
        "evaluation_datasets",
        "evaluation_result_items",
        "evaluation_runs",
        "evaluation_test_cases",
        "job_records",
        "knowledge_bindings",
        "knowledge_chunk_sets",
        "knowledge_chunks",
        "knowledge_collections",
        "knowledge_documents",
        "knowledge_facts",
        "knowledge_gaps",
        "knowledge_glossary_audits",
        "knowledge_glossary_settings",
        "knowledge_glossary_terms",
        "knowledge_group_sources",
        "knowledge_import_batches",
        "knowledge_import_items",
        "knowledge_index_activations",
        "knowledge_index_revisions",
        "knowledge_source_revisions",
        "knowledge_vector_generations",
        "llm_usage_logs",
        "model_provider_configs",
        "ocr_engines",
        "ocr_job_logs",
        "platform_document_types",
        "provider_api_keys",
        "provider_key_events",
        "repository_documents",
        "repository_file_revisions",
        "tenant_quotas",
        "tool_definitions",
        "tool_execution_logs",
        "workflow_approval_requests",
        "workflow_checkpoints",
        "workflow_definitions",
        "workflow_drafts",
        "workflow_executions",
        "workflow_node_executions",
        "workflow_versions",
    }
)


V1_TABLES = frozenset(
    {
        "ops_actions",
        "ops_storage_cleanup_actions",
        "resource_lifecycle_states",
        "resource_lifecycle_actions",
        "ops_evidence_backups",
        "workspaces",
        "workspace_members",
        "workspace_events",
        "providers",
        "provider_keys",
        "provider_key_audits",
        "model_defaults",
        "workspace_quotas",
        "model_usage_records",
        "modelops_events",
        "kb_collections",
        "kb_folders",
        "kb_sources",
        "kb_source_revisions",
        "kb_upload_requests",
        "kb_preparation_intents",
        "ocr_processing_runs",
        "ocr_run_pages",
        "ocr_run_artifacts",
        "ocr_text_versions",
        "ocr_spelling_runs",
        "ocr_spelling_dispositions",
        "ocr_spelling_reviews",
        "kb_compilation_runs",
        "kb_compilation_inputs",
        "kb_compilation_artifacts",
        "kb_compilation_reviews",
        "kb_compilation_review_artifacts",
        "kb_compilation_edit_previews",
        "kb_compilation_review_jobs",
        "kb_compiled_documents",
        "kb_compiled_versions",
        "kb_review_submissions",
        "kb_review_submission_previews",
        "kb_review_submission_actions",
        "kb_publication_previews",
        "kb_publication_decisions",
        "kb_index_runs",
        "kb_index_sync",
        "kb_index_inputs",
        "kb_index_chunks",
        "kb_index_table_facts",
        "chat_assistants",
        "chat_assistant_collections",
        "assistant_publications",
        "chat_conversations",
        "chat_turns",
        "app_clients",
        "app_api_keys",
        "app_request_logs",
    }
)


def include_object(
    obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
) -> bool:
    """Explicit ownership also excludes unknown tables and the legacy version table."""
    if type_ == "table":
        return name in V1_TABLES
    table = getattr(obj, "table", None)
    return table is None or table.name in V1_TABLES
