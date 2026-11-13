"""Drop per-workspace model allowlists and defaults; ModelOps resolves system defaults only."""

from alembic import op

revision = "0027_drop_ws_model_policy"
down_revision = "0026_ollama_llamacpp"
branch_labels = depends_on = None


def upgrade() -> None:
    op.drop_table("workspace_model_defaults")
    op.drop_table("workspace_allowed_providers")


def downgrade() -> None:
    op.execute(
        """
        CREATE TABLE workspace_allowed_providers (
            workspace_id VARCHAR(64) NOT NULL,
            provider_id VARCHAR(64) NOT NULL,
            is_default BOOLEAN DEFAULT false NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            CONSTRAINT workspace_allowed_providers_pkey PRIMARY KEY (workspace_id, provider_id),
            CONSTRAINT workspace_allowed_providers_provider_id_fkey FOREIGN KEY(provider_id)
                REFERENCES providers (id) ON DELETE CASCADE,
            CONSTRAINT workspace_allowed_providers_workspace_id_fkey FOREIGN KEY(workspace_id)
                REFERENCES workspaces (id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_workspace_allowed_providers_provider_id"
        " ON workspace_allowed_providers (provider_id)"
    )
    op.execute(
        """
        CREATE TABLE workspace_model_defaults (
            workspace_id VARCHAR(64) NOT NULL,
            capability VARCHAR(16) NOT NULL,
            provider_id VARCHAR(64) NOT NULL,
            CONSTRAINT workspace_model_defaults_pkey PRIMARY KEY (workspace_id, capability),
            CONSTRAINT workspace_model_defaults_workspace_id_provider_id_fkey
                FOREIGN KEY(workspace_id, provider_id)
                REFERENCES workspace_allowed_providers (workspace_id, provider_id) ON DELETE CASCADE,
            CONSTRAINT ck_workspace_default_capability
                CHECK (capability IN ('chat','embedding','rerank','ocr'))
        )
        """
    )
