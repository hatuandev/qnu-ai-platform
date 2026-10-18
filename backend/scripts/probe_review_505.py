"""Small opt-in acceptance batch reusing the internal-only probe, not 82 reruns."""

import argparse
import asyncio
import contextlib
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

from app.core.database import AsyncSessionFactory, engine
from app.modules.assistants.runtime import build_runtime_profile
from app.modules.assistants.service import assistant_service
from app.modules.rag.retriever import hybrid_retriever
from scripts.probe_prose_502 import main as probe


async def fingerprint():
    async with AsyncSessionFactory() as db:
        assistant = await assistant_service.get_assistant(db, "admissions")
        profile = build_runtime_profile(assistant)
        snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, profile.collection_id)
        return {"snapshot": snapshot.cache_fingerprint(), "assistant_revision": str(profile.assistant_revision),
            "configuration_fingerprint": hashlib.sha256(json.dumps(
                assistant.config.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()}


async def main(args):
    if not args.live:
        raise SystemExit("Use --live to authorize the internal-only acceptance probe.")
    fixture = json.loads(Path("storage/admissions_eval412_run2.json").read_text(encoding="utf-8"))
    # Fixture shape is the same frozen source used by the existing runner.
    cases = fixture["cases"]
    by_id = {case["id"]: case for case in cases}
    report = {"before": await fingerprint(), "results": []}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        for key in args.ids:
            question = by_id[key]["question"]
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                await probe(SimpleNamespace(live=True, inspect=False, assistant="admissions", question=question))
            events = [json.loads(line) for line in captured.getvalue().splitlines() if line.startswith("{")]
            result = {"id": key, "question": question, **events[-1], "requests": events[:-1]}
            report["results"].append(result)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"id": key, "status": result.get("status"), "reason": result.get("reason"),
                "code": result.get("code"), "citations": result.get("citation_count")}), flush=True)
        report["after"] = await fingerprint()
        report["unchanged"] = report["before"] == report["after"]
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--ids", type=int, nargs="+", required=True)
    parser.add_argument("--output", default="storage/review505-live.json")
    asyncio.run(main(parser.parse_args()))
