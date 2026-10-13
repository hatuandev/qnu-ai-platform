"""Read-only selection diagnosis from previous query plans, no expected answers."""

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.core.database import AsyncSessionFactory, engine
from app.modules.assistants.models import AssistantModel
from app.modules.rag.evidence_model import PROPOSE_INSTRUCTION, structured_call
from app.modules.rag.evidence_pipeline import select_context
from app.modules.rag.evidence_precedence import active_preferences
from app.modules.rag.evidence_runtime import assistant_scope, resolve_evidence_request
from app.modules.rag.evidence_schemas import AnswerProposal, QueryPlan
from app.modules.rag.evidence_validation import bind_quote, numbers_supported, same_source
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import AskRequest


async def main(args):
    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    selected = set(map(int, args.ids.split(",")))
    async with AsyncSessionFactory() as db:
        assistant = (await db.execute(select(AssistantModel).where(AssistantModel.code == "admissions"))).scalar_one()
        snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, assistant.collection_id, tenant_id=assistant.tenant_id)
        output = []
        for item in report["results"]:
            if item["id"] not in selected:
                continue
            req, policy = await resolve_evidence_request(db, AskRequest(question=item["question"],
                collection_id=assistant.collection_id, module_code="admissions", assistant_code="admissions",
                tenant_id=snapshot.tenant_id, workspace_id=snapshot.workspace_id))
            decision = item["response"].get("answer_decision") or {}
            plan = QueryPlan.model_validate(decision["requested"]) if decision else QueryPlan(query=item["question"])
            blocks = await select_context(db, req, snapshot, plan, policy, candidate_mode=False)
            output.append({"id": item["id"], "plan": plan.model_dump(), "blocks": [b.model_dump() for b in blocks]})
            if args.propose:
                proposal = await structured_call(db, req, AnswerProposal, PROPOSE_INSTRUCTION,
                    {"question": req.question, "requested": plan.model_dump(), "evidence": output[-1]["blocks"],
                     "source_preferences": [r.model_dump() for r in active_preferences(policy, plan, blocks)],
                     "assistant_scope": assistant_scope(req)}, max_tokens=4000)
                output[-1]["proposal"] = proposal.model_dump()
                checks = []
                for claim in proposal.claims:
                    try:
                        refs = [bind_quote(r, {b.id: b for b in blocks}) for r in claim.references]
                        checks.append({"claim": claim.id, "same_source": same_source(refs),
                            "numbers_supported": numbers_supported(claim.text, [r["quote"] for r in refs])})
                    except ValueError as exc:
                        checks.append({"claim": claim.id, "error": str(exc)})
                output[-1]["checks"] = checks
        Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps([{ "id": x["id"], "checks": x.get("checks"), "blocks": len(x["blocks"])} for x in output]))
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="storage/admissions_eval417_critical.json")
    parser.add_argument("--ids", default="41,42")
    parser.add_argument("--output", default="storage/evidence417_context.json")
    parser.add_argument("--propose", action="store_true")
    asyncio.run(main(parser.parse_args()))
