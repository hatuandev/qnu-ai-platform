"""Read-only publication comparison and in-memory source extraction diagnostic.

--ocr makes ONE header-crop request through configured PaddleOCR (normal OCR logs).
It requires an explicit allowed host and never uses the cloud OCR combo chain.
Never saves source revisions, builds vectors, publishes or changes policy/models.
"""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

import pymupdf
from sqlalchemy import text

from app.core.database import AsyncSessionFactory, engine
from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest
from app.modules.knowledge.parsers import get_document_parser
from app.modules.knowledge.services.header_rescue import prepare_header_rescue, rescue_header
from app.modules.knowledge.services.source_artifact import add_layout_issues, build_source_artifact
from app.modules.knowledge.services.source_extraction import build_native_pages
from app.modules.knowledge.services.source_pages import canonical_pages, normalize_source_pages
from app.modules.ocr.service import OCRService
from scripts.audit_rag_floor_stage1 import fingerprint, inspect_publication, serializable


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--ocr-host", help="Explicit destination host authorized for the crop")
    parser.add_argument("--stored-canonical", action="store_true", help="Use pinned native text, skip repeating the PDF parser")
    args = parser.parse_args()
    if args.ocr and not args.ocr_host:
        parser.error("--ocr requires --ocr-host; cloud fallback is never allowed by this diagnostic")
    report = {"ocr_requested": args.ocr}
    try:
        before = await inspect_publication("admissions", args.pdf.name)
        content = args.pdf.read_bytes()
        report["binary_matches_publication"] = hashlib.sha256(content).hexdigest() == before["target"]["origin_file_hash"]
        if not report["binary_matches_publication"]:
            raise ValueError("Binary does not match published source")
        if args.stored_canonical:
            with pymupdf.open(stream=content, filetype="pdf") as document:
                page_count = len(document)
            raw_text = before["target"]["canonical_markdown"]
            pages = [{"page_number": page["page_number"], "extracted_text": page["markdown_content"],
                      "engine_used": "native"} for page in canonical_pages(raw_text, page_count)]
            selected = []
        else:
            parsed = await get_document_parser("pdf").parse(content, args.pdf.name)
            raw_text = parsed.raw_text
            pages, selected, _ = await asyncio.to_thread(build_native_pages, content, parsed)
        report["stored_canonical"] = args.stored_canonical
        report["full_page_ocr_candidates"] = selected
        original = pages[0]["extracted_text"]
        prepared = await asyncio.to_thread(prepare_header_rescue, content, pages[0])
        report["header_candidate"] = {key: value for key, value in (prepared or {}).items() if key != "content"}
        if prepared and args.ocr:
            async with AsyncSessionFactory() as db:
                await db.execute(text("SET TRANSACTION READ ONLY"))
                endpoints = (await db.execute(text("""
                    SELECT api_base_url FROM model_provider_configs WHERE is_active=true
                    AND provider_type IN ('paddleocr','paddleocr_vl','paddle')
                """))).scalars().all()
                if not endpoints or any(urlsplit(url or "").hostname != args.ocr_host for url in endpoints):
                    raise ValueError("Active PaddleOCR destinations do not match the authorized host")
                original_extract = OCRService.extract_document

                async def observe(service, *positional, **keywords):
                    response = await original_extract(service, *positional, **keywords)
                    report["ocr_observation"] = {"engine": response.engine_used,
                        "fallback_triggered": response.fallback_triggered, "raw_text": response.raw_text,
                        "pages": [page.extracted_text for page in response.pages]}
                    return response

                # Observe the REAL request/response; no synthetic OCR or replacement output.
                with patch.object(OCRService, "extract_document", observe):
                    await rescue_header(db, pages[0], prepared, "paddleocr", before["snapshot"]["tenant_id"])
        report["native_page_text_retained"] = pages[0]["extracted_text"].endswith(original)
        report["header_result"] = pages[0].get("metadata_rescue")
        markdown, page_manifest = normalize_source_pages(raw_text, len(pages), pages)
        artifact = build_source_artifact(markdown, len(pages), {})
        add_layout_issues(artifact, pages)
        manifest = resolve_unit_manifest(markdown, artifact)
        by_id = {unit.id: unit for unit in manifest.units}
        graph = artifact["context_graph"]
        report.update(artifact_version=artifact["version"], unit_count=len(manifest.units),
                      graph_hash=graph["digest"], review=artifact["review"],
                      issue_codes=[issue["code"] for issue in artifact["issues"]],
                      metadata_rescue_persistable=page_manifest[0].get("metadata_rescue") == report["header_result"])
        report["diagnostic_rows"] = [
            {"source_unit_id": unit.id, "page": unit.page_number, "raw": unit.text,
             "projection": graph["row_projections"].get(unit.id),
             "context": [{"page": by_id[ref].page_number, "text": by_id[ref].text} for ref in graph["links"].get(unit.id, [])]}
            for unit in manifest.units if not unit.is_container and unit.kind == "table"
            and any(code in unit.text for code in ("7140114", "7140209"))]
        after = await inspect_publication("admissions", args.pdf.name)
        # Snapshot includes resolution time: compare pinned identities/content, not wall-clock fields.
        keys = ("configuration_fingerprint", "snapshot_fingerprint", "collection_metadata_fingerprint",
                "target_data_fingerprint", "inventory")
        report["before"] = {key: fingerprint(before[key]) for key in keys}
        report["after"] = {key: fingerprint(after[key]) for key in keys}
        report["publication_unchanged"] = report["before"] == report["after"]
    finally:
        await engine.dispose()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(serializable(report), ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {key: value for key, value in report.items() if key not in ("diagnostic_rows", "ocr_observation")}
    if summary.get("header_result"):
        summary["header_result"] = {key: value for key, value in summary["header_result"].items() if key != "ocr_text"}
    print(json.dumps(summary, ensure_ascii=True))


if __name__ == "__main__":
    asyncio.run(main())
