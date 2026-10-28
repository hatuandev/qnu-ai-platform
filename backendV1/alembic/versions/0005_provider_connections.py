"""Provider containers, stable child model IDs and scoped shared credentials."""

import json
import uuid
from urllib.parse import urlsplit

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0005_provider_connections"
down_revision = "0004_application_api_keys"
branch_labels = depends_on = None


def upgrade():
    op.add_column(
        "providers",
        sa.Column("is_connection", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("providers", sa.Column("parent_id", sa.String(64), nullable=True))
    op.create_foreign_key(
        "fk_provider_parent", "providers", "providers", ["parent_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_index("ix_providers_parent_id", "providers", ["parent_id"])
    op.create_index("ix_providers_is_connection", "providers", ["is_connection"])
    op.add_column("provider_keys", sa.Column("model_ids", JSONB(), nullable=True))
    # Offline SQL still describes the additive schema; data conversion runs online only.
    if op.get_context().as_sql:
        return
    convert_legacy_providers(op.get_bind())


def convert_legacy_providers(db):
    rows = (
        db.execute(
            sa.text(
                "SELECT id,name,base_url,provider_type,is_active,timeout_seconds,extra_config FROM providers WHERE NOT is_connection AND parent_id IS NULL ORDER BY created_at,id"
            )
        )
        .mappings()
        .all()
    )
    groups = {}
    for row in rows:
        groups.setdefault(row["base_url"].rstrip("/"), []).append(row)
    for endpoint, models in groups.items():
        connection_id = "conn_" + uuid.uuid4().hex[:16]
        name = (urlsplit(endpoint).netloc or "Provider")[:180] + " · " + connection_id[-8:]
        config = {"connection_family": "custom", "key_leases_v1": {}}
        for model in models:
            config["key_leases_v1"].update((model["extra_config"] or {}).get("key_leases_v1", {}))
        db.execute(
            sa.text("""INSERT INTO providers(id,name,provider_type,base_url,model_name,capabilities,is_active,priority,timeout_seconds,extra_config,is_connection)
            VALUES(:id,:name,:type,:url,'','[]'::jsonb,:active,5,:timeout,CAST(:config AS jsonb),true)"""),
            {
                "id": connection_id,
                "name": name,
                "type": models[0]["provider_type"],
                "url": endpoint,
                "active": any(m["is_active"] for m in models),
                "timeout": max(m["timeout_seconds"] for m in models),
                "config": json.dumps(config),
            },
        )
        for model in models:
            db.execute(
                sa.text("UPDATE providers SET parent_id=:parent WHERE id=:id"),
                {"parent": connection_id, "id": model["id"]},
            )
            db.execute(
                sa.text(
                    "UPDATE provider_keys SET provider_id=:parent, model_ids=CAST(:models AS jsonb) WHERE provider_id=:id"
                ),
                {
                    "parent": connection_id,
                    "id": model["id"],
                    "models": json.dumps([model["id"]]),
                },
            )
            db.execute(
                sa.text("UPDATE provider_key_audits SET provider_id=:parent WHERE provider_id=:id"),
                {"parent": connection_id, "id": model["id"]},
            )


def downgrade():
    raise RuntimeError(
        "Stored evidence must be preserved; provider/model bindings cannot be dropped."
    )
