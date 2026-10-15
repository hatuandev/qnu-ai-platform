"""Probe dialogue acts over live internal model only; never touches providers.

Chains share one conversation thread so follow-ups see real history. Any
external adapter construction is blocked before sending and recorded. Source,
config and publication stay intact; failures are logged, never retried.
"""

import argparse
import asyncio
import ipaddress
import json
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

from sqlalchemy import text

from app.core.database import AsyncSessionFactory, engine
from app.core.exceptions import AppException
from app.modules.modelops import service as modelops_module
from scripts.audit_rag_floor_stage1 import fingerprint, inspect_publication, trace_case

THREADS = [
    ("explain_many", [
        "tổng hợp các ngành có tổ hợp môn toán, lý, hóa giúp tôi",
        "sao nhiều thế",
    ]),
    ("filter_2026", [
        "tổng hợp các ngành có tổ hợp môn toán, lý, hóa giúp tôi",
        "chỉ lấy năm 2026",
    ]),
    ("reformat_compact", [
        "tổng hợp các ngành có tổ hợp môn toán, lý, hóa giúp tôi",
        "trình bày gọn lại",
    ]),
]


async def run(output: Path, live: bool) -> None:
    if output.exists():
        raise ValueError("Preserve previous reports; choose a new output")
    output.parent.mkdir(parents=True, exist_ok=True)
    before = await inspect_publication("admissions", "TB điểm sàn 26.pdf")
    fields = ("configuration_fingerprint", "snapshot_fingerprint", "target_data_fingerprint",
              "collection_metadata_fingerprint", "inventory")
    report = {"internal_only": True, "results": [], "blocked_destinations": [],
              "before": {key: fingerprint(before[key]) for key in fields}}
    provider_id = before["configuration"]["model_policy"]["preferred_provider_id"]
    async with AsyncSessionFactory() as db:
        await db.execute(text("SET TRANSACTION READ ONLY"))
        endpoint = (await db.execute(text("SELECT api_base_url,provider_type FROM model_provider_configs WHERE id=:id"),
                                    {"id": provider_id})).mappings().one()
    host = urlsplit(endpoint["api_base_url"]).hostname
    address = ipaddress.ip_address(host)
    if endpoint["provider_type"] not in {"vllm", "ollama"} or not (
            address.is_private or address in ipaddress.ip_network("100.64.0.0/10")):
        raise ValueError("Primary is not a verified internal model endpoint")
    from app.modules.modelops import providers as providers_module
    from app.modules.modelops.services import capability_probe as capability_probe_module
    from app.modules.modelops.services import chat_probe as chat_probe_module
    original_factory = providers_module.get_llm_adapter

    def internal_factory(*args, **kwargs):
        if kwargs.get("base_url") != endpoint["api_base_url"] or kwargs.get("provider_type") != endpoint["provider_type"]:
            report["blocked_destinations"].append({"provider_type": kwargs.get("provider_type"),
                                                   "base_url": kwargs.get("base_url")})
            raise AppException("External model blocked by internal-only diagnostic.",
                               code="INTERNAL_ONLY_PROBE", status_code=403)
        return original_factory(*args, **kwargs)

    guard_targets = [providers_module, capability_probe_module, chat_probe_module, modelops_module]

    try:
        if live:
            from contextlib import ExitStack
            with ExitStack() as stack:
                for target in guard_targets:
                    stack.enter_context(patch.object(target, "get_llm_adapter", internal_factory))
                for thread, questions in THREADS:
                    conversation = f"acts476_{thread}_{uuid.uuid4().hex[:8]}"
                    for turn, question in enumerate(questions):
                        try:
                            result = await asyncio.wait_for(trace_case(
                                {"id": f"{thread}#{turn}", "question": question},
                                "admissions", conversation_id=conversation), timeout=240)
                        except Exception as exc:  # recorded, never retried
                            result = {"id": f"{thread}#{turn}", "question": question,
                                      "conversation_id": conversation,
                                      "error_type": type(exc).__name__,
                                      "error_code": getattr(exc, "code", None)}
                        report["results"].append(result)
                        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                        response = result.get("response") or {}
                        decision = response.get("answer_decision") or {}
                        print(json.dumps({"case": f"{thread}#{turn}", "status": response.get("status"),
                            "decision": decision.get("status"), "reason": decision.get("reason"),
                            "act": (decision.get("question_resolution") or {}).get("mode"),
                            "error": result.get("error_type")}, ensure_ascii=False), flush=True)
    finally:
        after = await inspect_publication("admissions", "TB điểm sàn 26.pdf")
        report["unchanged"] = {key: report["before"][key] == fingerprint(after[key]) for key in fields}
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path("storage/rag_enumeration_476/probe_conversation_acts.json"))
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.output, args.live))
