"""Probe real enumeration/followups with an internal-only LLM egress guard.

Never replaces model answers or changes provider configuration. An external
fallback attempt is rejected before adapter construction and recorded as failure.
--live creates ordinary test conversations/usage; source/index/model settings stay intact.
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
    original_factory = modelops_module.get_llm_adapter

    def internal_factory(*args, **kwargs):
        if kwargs.get("base_url") != endpoint["api_base_url"] or kwargs.get("provider_type") != endpoint["provider_type"]:
            report["blocked_destinations"].append({"provider_type": kwargs.get("provider_type")})
            raise AppException("External model blocked by internal-only diagnostic.",
                               code="INTERNAL_ONLY_PROBE", status_code=403)
        return original_factory(*args, **kwargs)

    thread = "enum475_" + uuid.uuid4().hex[:16]
    cases = [
        ("initial", "tổng hợp các ngành có tổ hợp môn toán, lý, hóa giúp tôi", thread),
        ("followup", "sao ít thế", thread),
        ("explicit_2025", "Liệt kê đầy đủ các ngành/chương trình có tổ hợp Toán, Lý, Hóa theo cẩm nang tuyển sinh 2025.", None),
        ("missing_2037", "Liệt kê các ngành có tổ hợp Toán, Lý, Hóa năm 2037.", None),
    ]
    try:
        if live:
            with patch.object(modelops_module, "get_llm_adapter", internal_factory):
                for name, question, conversation in cases:
                    result = await asyncio.wait_for(trace_case({"id": name, "question": question}, "admissions",
                        conversation_id=conversation), timeout=180)
                    report["results"].append(result)
                    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                    response = result.get("response") or {}
                    print(json.dumps({"case": name, "status": response.get("status"), "error": result.get("error_code"),
                        "count": (response.get("answer_decision") or {}).get("count"),
                        "elapsed_ms": result["elapsed_ms"]}), flush=True)
    finally:
        after = await inspect_publication("admissions", "TB điểm sàn 26.pdf")
        report["unchanged"] = {key: report["before"][key] == fingerprint(after[key]) for key in fields}
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(run(args.output, args.live))
