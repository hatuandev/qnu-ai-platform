"""Expand knowledge_facts attribute_value to TEXT, attribute_name to VARCHAR(255), entity_name to VARCHAR(512).

Revision ID: 20260920_expand_facts_text
Revises: 20260919_approval_payload_hash
Create Date: 2026-09-20
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260920_expand_facts_text"
down_revision = "20260919_approval_payload_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "knowledge_facts" in table_names:
        cols = {c["name"]: c for c in inspector.get_columns("knowledge_facts")}

        if "attribute_value" in cols:
            op.alter_column(
                "knowledge_facts",
                "attribute_value",
                existing_type=sa.String(length=512),
                type_=sa.Text(),
                existing_nullable=False,
            )

        if "attribute_name" in cols:
            op.alter_column(
                "knowledge_facts",
                "attribute_name",
                existing_type=sa.String(length=128),
                type_=sa.String(length=255),
                existing_nullable=False,
            )

        if "entity_name" in cols:
            op.alter_column(
                "knowledge_facts",
                "entity_name",
                existing_type=sa.String(length=255),
                type_=sa.String(length=512),
                existing_nullable=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "knowledge_facts" in table_names:
        cols = {c["name"]: c for c in inspector.get_columns("knowledge_facts")}

        if "attribute_value" in cols:
            op.alter_column(
                "knowledge_facts",
                "attribute_value",
                existing_type=sa.Text(),
                type_=sa.String(length=512),
                existing_nullable=False,
            )

        if "attribute_name" in cols:
            op.alter_column(
                "knowledge_facts",
                "attribute_name",
                existing_type=sa.String(length=255),
                type_=sa.String(length=128),
                existing_nullable=False,
            )

        if "entity_name" in cols:
            op.alter_column(
                "knowledge_facts",
                "entity_name",
                existing_type=sa.String(length=512),
                type_=sa.String(length=255),
                existing_nullable=False,
            )
