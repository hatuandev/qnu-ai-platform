"""Credential-free ModelOps audit for this evidence evaluation."""

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.core.database import AsyncSessionFactory, engine
from app.modules.modelops.models import (
    LLMUsageLog,
    ModelProviderConfig,
    ProviderApiKey,
    ProviderKeyEvent,
)


async def main(args):
    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    conversations = [r["conversation_id"] for r in report["results"]]
    async with AsyncSessionFactory() as db:
        usage = (await db.execute(select(LLMUsageLog).where(LLMUsageLog.conversation_id.in_(conversations)))).scalars().all()
        providers = (await db.execute(select(ModelProviderConfig).where(ModelProviderConfig.id.in_(
            [report["assistant"]["config"]["model_policy"][k] for k in ["preferred_provider_id", "fallback_provider_id"]])))).scalars().all()
        keys = (await db.execute(select(ProviderApiKey).where(ProviderApiKey.provider_id.in_([p.id for p in providers])))).scalars().all()
        events = (await db.execute(select(ProviderKeyEvent).where(ProviderKeyEvent.provider_id.in_([p.id for p in providers]))
                                  .order_by(ProviderKeyEvent.created_at.desc()).limit(30))).scalars().all()
        output = {"providers": [{"id": p.id, "name": p.name, "timeout_seconds": p.timeout_seconds} for p in providers],
            "keys": [{k: str(getattr(key, k)) for k in ["provider_id", "status", "is_active", "consecutive_failures", "last_error_code", "last_error_at", "cooldown_until", "lease_until", "quota_limit", "usage_tokens"]} for key in keys],
            "fallback": [{"conversation": u.conversation_id, "provider": u.provider, "model": u.model_name,
                          "fallback_reason": u.error_message, "at": str(u.created_at)} for u in usage if u.error_message],
            "events": [{k: str(getattr(e, k)) for k in ["provider_id", "event_type", "reason", "created_at"]} for e in events]}
        Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(output, ensure_ascii=True))
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="storage/admissions_eval417_full.json")
    parser.add_argument("--output", default="storage/models417_audit.json")
    asyncio.run(main(parser.parse_args()))
