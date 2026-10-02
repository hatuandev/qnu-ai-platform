"""Remove retired local model providers and routing entries.

Revision ID: 20261002_remove_local_models
Revises: 20261002_normalize_provider_key_status
Create Date: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261002_remove_local_models"
down_revision: str | Sequence[str] | None = "20261002_normalize_provider_key_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LOCAL_PROVIDER_IDS = (
    "prov_local",
    "prov_ollama",
    "prov_sentence_transformers",
    "prov_docling",
    "prov_easyocr",
)


def upgrade() -> None:
    local_ids = ", ".join(f"'{provider_id}'" for provider_id in _LOCAL_PROVIDER_IDS)
    op.execute(
        sa.text(
            """
            UPDATE model_provider_configs
            SET extra_config = jsonb_set(
                COALESCE(extra_config, '{}'::jsonb),
                '{defaults}',
                jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                COALESCE(extra_config->'defaults', '{}'::jsonb),
                                '{default_embedding_provider_id}',
                                '"prov_cloudflare"'::jsonb,
                                true
                            ),
                            '{default_embedding_model}',
                            '"@cf/baai/bge-m3"'::jsonb,
                            true
                        ),
                        '{default_reranker_provider_id}',
                        '"prov_cloudflare"'::jsonb,
                        true
                    ),
                    '{default_reranker_model}',
                    '"@cf/baai/bge-reranker-base"'::jsonb,
                    true
                ),
                true
            )
            WHERE id = 'system_model_defaults'
            """
        )
    )
    for chain_name in (
        "embedding_combo_chain",
        "reranker_combo_chain",
        "ocr_combo_chain",
        "chat_combo_chain",
    ):
        op.execute(
            sa.text(
                f"""
                UPDATE model_provider_configs
                SET extra_config = jsonb_set(
                    extra_config,
                    '{{defaults,{chain_name}}}',
                    COALESCE(
                        (
                            SELECT jsonb_agg(item ORDER BY ordinality)
                            FROM jsonb_array_elements(
                                COALESCE(extra_config->'defaults'->'{chain_name}', '[]'::jsonb)
                            ) WITH ORDINALITY AS entries(item, ordinality)
                            WHERE COALESCE(item->>'provider_id', '') NOT IN ({local_ids})
                        ),
                        '[]'::jsonb
                    ),
                    true
                )
                WHERE id = 'system_model_defaults'
                """
            )
        )
    op.execute(
        sa.text(
            f"""
            UPDATE model_provider_configs
            SET extra_config = jsonb_set(
                extra_config,
                '{{defaults,model_combos}}',
                COALESCE(
                    (
                        SELECT jsonb_agg(
                            (combo - 'models' - 'description')
                            || jsonb_build_object(
                                'models', COALESCE(
                                    (
                                        SELECT jsonb_agg(model ORDER BY model_ordinality)
                                        FROM jsonb_array_elements(
                                            COALESCE(combo->'models', '[]'::jsonb)
                                        ) WITH ORDINALITY AS model_entries(model, model_ordinality)
                                        WHERE COALESCE(model->>'provider_id', '') NOT IN ({local_ids})
                                          AND lower(COALESCE(model->>'provider_type', '')) NOT IN (
                                            'local', 'local_vllm', 'ollama', 'vllm',
                                            'sentence_transformers', 'docling', 'easyocr'
                                          )
                                    ),
                                    '[]'::jsonb
                                ),
                                'description', CASE COALESCE(combo->>'task_type', '')
                                    WHEN 'ocr' THEN 'Chuỗi OCR dự phòng qua API provider'
                                    WHEN 'embedding' THEN 'Chuỗi embedding dự phòng qua API provider'
                                    WHEN 'reranker' THEN 'Chuỗi reranker dự phòng qua API provider'
                                    WHEN 'chat' THEN 'Chuỗi chat dự phòng qua API provider'
                                    ELSE 'Chuỗi mô hình dự phòng qua API provider'
                                END
                            )
                            ORDER BY combo_ordinality
                        )
                        FROM jsonb_array_elements(
                            COALESCE(extra_config->'defaults'->'model_combos', '[]'::jsonb)
                        ) WITH ORDINALITY AS combo_entries(combo, combo_ordinality)
                    ),
                    '[]'::jsonb
                ),
                true
            )
            WHERE id = 'system_model_defaults'
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            UPDATE model_provider_configs
            SET extra_config = jsonb_set(
                extra_config,
                '{{defaults,vision_adapter,models}}',
                COALESCE(
                    (
                        SELECT jsonb_agg(model ORDER BY ordinality)
                        FROM jsonb_array_elements(
                            COALESCE(extra_config->'defaults'->'vision_adapter'->'models', '[]'::jsonb)
                        ) WITH ORDINALITY AS entries(model, ordinality)
                        WHERE COALESCE(model->>'provider_id', '') NOT IN ({local_ids})
                          AND lower(COALESCE(model->>'provider_type', '')) NOT IN (
                            'local', 'local_vllm', 'ollama', 'vllm',
                            'sentence_transformers', 'docling', 'easyocr'
                          )
                    ),
                    '[]'::jsonb
                ),
                true
            )
            WHERE id = 'system_model_defaults'
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            DELETE FROM model_provider_configs
            WHERE id IN ({local_ids})
               OR lower(provider_type) IN (
                    'local', 'local_vllm', 'ollama', 'vllm',
                    'sentence_transformers', 'docling', 'easyocr'
               )
            """
        )
    )


def downgrade() -> None:
    # Provider credentials and local model routing are intentionally not recreated.
    pass
