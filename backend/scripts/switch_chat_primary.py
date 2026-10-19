"""Operator-authorized reorder of existing chat defaults; never edits credentials."""
import argparse
import asyncio
import hashlib
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"backend"))
from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.database import AsyncSessionFactory, engine
from app.modules.modelops.models import ModelProviderConfig
from app.modules.modelops.schemas import SystemModelDefaultsUpdate
from app.modules.modelops.services.model_catalog_service import model_catalog_service

CHAT_FIELDS = {"default_chat_provider_id", "default_chat_model", "chat_combo_chain"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def public_chat(defaults):
    return {key: defaults.get(key) for key in (*sorted(CHAT_FIELDS), "default_chat_mode")}


async def main(args):
    url = make_url(settings.DATABASE_URL)
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    assert settings.ENVIRONMENT in {"development", "dev", "local"}
    assert url.host in {"localhost", "127.0.0.1", "::1"}
    assert audit["observed_database"]["read_only"] == "on"
    assert audit["database"]["database"] == url.database and audit["database"]["host"] == url.host
    assert not args.output.exists(), "Do not overwrite an earlier configuration receipt"
    async with AsyncSessionFactory() as db:
        row = (await db.scalars(select(ModelProviderConfig).where(ModelProviderConfig.id == "system_model_defaults").with_for_update())).one()
        before = json.loads(json.dumps(row.extra_config["defaults"]))
        chain = before["chat_combo_chain"]
        candidates = [item for item in chain if item["model_name"] == args.model and item.get("is_active", True)]
        assert len(candidates) == 1, "Need exactly one already-configured target chat model"
        chosen = candidates[0]
        provider = await db.get(ModelProviderConfig, chosen["provider_id"])
        assert provider and provider.is_active
        assert before["default_chat_mode"] == "combo", "Preserve existing mode; do not invent routing"
        reordered = [chosen, *(item for item in chain if item is not chosen)]
        untouched = {key: value for key, value in before.items() if key not in CHAT_FIELDS}
        await model_catalog_service.update_system_model_defaults(db, SystemModelDefaultsUpdate(
            default_chat_provider_id=chosen["provider_id"], default_chat_model=chosen["model_name"], chat_combo_chain=reordered))
    async with AsyncSessionFactory() as db:
        row = await db.get(ModelProviderConfig, "system_model_defaults")
        after = row.extra_config["defaults"]
        assert after["default_chat_model"] == args.model and after["default_chat_provider_id"] == chosen["provider_id"]
        assert {key: value for key, value in after.items() if key not in CHAT_FIELDS} == untouched
        assert after["chat_combo_chain"][0]["model_name"] == args.model
        result = {"status": "VERIFIED_FRESH_SESSION", "environment": settings.ENVIRONMENT,
            "database": url.database, "before": public_chat(before), "after": public_chat(after),
            "other_defaults_sha256": digest(untouched), "other_defaults_unchanged": True,
            "authorization": "User explicitly requested Qwen3.5 as default primary and live retest",
            "credentials_modified": False, "provider_settings_modified": False}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8", newline="\n")
        print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    logging.getLogger().handlers = [logging.NullHandler()]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    async def execute():
        try: await main(args)
        finally: await engine.dispose()
    asyncio.run(execute())
