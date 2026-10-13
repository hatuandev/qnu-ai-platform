"""Store long structured-fact text losslessly with deterministic identity."""

import sqlalchemy as sa

from alembic import op

revision = "20261012_fact_long_text_identity"
down_revision = "20261012_fact_temporal_context"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("knowledge_facts")}
    if "entity_key" not in columns:
        op.add_column("knowledge_facts", sa.Column("entity_key", sa.String(64), nullable=True))
    if "entity_label" not in columns:
        op.add_column("knowledge_facts", sa.Column("entity_label", sa.String(512), nullable=True))
    if "entity_text" not in columns:
        op.add_column("knowledge_facts", sa.Column("entity_text", sa.Text(), nullable=True))

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("knowledge_facts")}
    if "ix_knowledge_facts_entity_name" in indexes:
        op.drop_index("ix_knowledge_facts_entity_name", table_name="knowledge_facts")
    op.alter_column(
        "knowledge_facts",
        "entity_name",
        existing_type=sa.String(512),
        type_=sa.Text(),
        existing_nullable=False,
    )

    bind.execute(sa.text("""
        UPDATE knowledge_facts
        SET entity_text = entity_name,
            entity_label = CASE
                WHEN char_length(entity_name) <= 512 THEN entity_name
                ELSE rtrim(left(entity_name, 494)) || ' … #' || left(md5(entity_name), 12)
            END,
            entity_key = 'fact_' || left(md5(
                coalesce(entity_code, '') || '|' || entity_name || '|' ||
                coalesce(raw_data->>'table_id', '') || '|' ||
                coalesce(raw_data->>'row_index', '')
            ), 48)
        WHERE entity_key IS NULL OR entity_label IS NULL OR entity_text IS NULL
    """))
    op.alter_column("knowledge_facts", "entity_key", existing_type=sa.String(64), nullable=False)
    op.alter_column("knowledge_facts", "entity_label", existing_type=sa.String(512), nullable=False)
    op.alter_column("knowledge_facts", "entity_text", existing_type=sa.Text(), nullable=False)

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("knowledge_facts")}
    if "ix_knowledge_facts_entity_key" not in indexes:
        op.create_index("ix_knowledge_facts_entity_key", "knowledge_facts", ["entity_key"])
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_knowledge_facts_search_text
        ON knowledge_facts USING gin (
            to_tsvector(
                'simple',
                coalesce(entity_text, '') || ' ' ||
                coalesce(attribute_name, '') || ' ' ||
                coalesce(attribute_value, '')
            )
        )
    """)


def downgrade():
    bind = op.get_bind()
    long_rows = bind.execute(
        sa.text("SELECT count(*) FROM knowledge_facts WHERE char_length(entity_name) > 512")
    ).scalar_one()
    if long_rows:
        raise RuntimeError("Cannot downgrade: long fact entity text would be truncated.")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_facts_search_text")
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("knowledge_facts")}
    if "ix_knowledge_facts_entity_key" in indexes:
        op.drop_index("ix_knowledge_facts_entity_key", table_name="knowledge_facts")
    op.drop_column("knowledge_facts", "entity_text")
    op.drop_column("knowledge_facts", "entity_label")
    op.drop_column("knowledge_facts", "entity_key")
    op.alter_column(
        "knowledge_facts",
        "entity_name",
        existing_type=sa.Text(),
        type_=sa.String(512),
        existing_nullable=False,
    )
    op.create_index("ix_knowledge_facts_entity_name", "knowledge_facts", ["entity_name"])
