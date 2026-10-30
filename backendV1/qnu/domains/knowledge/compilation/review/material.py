"""Build exhaustive units from the compiler snapshot, keeping table context and literals."""

import json
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.compilation.artifacts import read
from qnu.domains.knowledge.compilation.models import CompilationRun
from qnu.domains.knowledge.publication.evidence import VersionBundle, load_bundle
from qnu.ports.blob_store import BlobStore


@dataclass(frozen=True, slots=True)
class ReviewMaterial:
    bundle: VersionBundle
    payload: dict


def source_units(documents: list[dict]) -> list[dict]:
    units = []
    for doc in documents:
        for page in doc["pages"]:
            for block in page["blocks"]:
                base = {
                    "ocr_run_id": doc["ocr_run_id"],
                    "page": page["page_number"],
                    "identity": doc["identity"],
                    "bbox": block["bbox"],
                    "kind": block["type"],
                    **{
                        key: block[key]
                        for key in ("evidence_id", "origin", "requires_review", "label")
                        if key in block
                    },
                }
                table = block.get("table")
                if table is not None and table["status"] == "parsed":
                    for row_index, row in enumerate(table["rows"]):
                        for col_index, cell in enumerate(row):
                            units.append(
                                {
                                    **base,
                                    "id": doc["ocr_run_id"] + ":" + cell["evidence_id"],
                                    "evidence_id": cell["evidence_id"],
                                    "text": cell["text"],
                                    "kind": "table_cell",
                                    "table_id": doc["ocr_run_id"] + ":" + block["evidence_id"],
                                    "row": row_index + 1,
                                    "column": col_index + 1,
                                    "row_span": cell["row_span"],
                                    "col_span": cell["col_span"],
                                    "header": cell["header"],
                                }
                            )
                else:
                    units.append(
                        {
                            **base,
                            "id": doc["ocr_run_id"] + ":" + block["evidence_id"],
                            "text": block["text"],
                        }
                    )
    return units


def draft_units(draft: dict) -> list[dict]:
    units = [{"id": "title", "kind": "title", "text": draft["title"]}]
    for section_no, section in enumerate(draft["sections"], start=1):
        heading_id = f"section:{section_no}:heading"
        units.append({"id": heading_id, "kind": "heading", "text": section["heading"]})
        for paragraph_no, paragraph in enumerate(section["paragraphs"], start=1):
            units.append(
                {
                    "id": f"section:{section_no}:paragraph:{paragraph_no}",
                    "kind": "paragraph",
                    "text": paragraph["text"],
                    "heading": section["heading"],
                    "citations": paragraph["citations"],
                }
            )
    for table_no, entry in enumerate(draft["source_tables"], start=1):
        for row_no, row in enumerate(entry["table"].get("rows", []), start=1):
            for col_no, cell in enumerate(row, start=1):
                units.append(
                    {
                        "id": f"table:{table_no}:row:{row_no}:cell:{col_no}",
                        "kind": "table_cell",
                        "text": cell["text"],
                        "source_id": entry["citation"].split(":", 1)[0] + ":" + cell["evidence_id"],
                        "row": row_no,
                        "column": col_no,
                        "header": cell["header"],
                        "row_span": cell["row_span"],
                        "col_span": cell["col_span"],
                    }
                )
    for index, unknown in enumerate(draft["unknowns"], start=1):
        units.append({"id": f"unknown:{index}", "kind": "unknown", "text": unknown})
    return units


async def load_material(db: AsyncSession, blob: BlobStore, run: CompilationRun) -> ReviewMaterial:
    await db.refresh(run)
    bundle = await load_bundle(
        db, blob, run.workspace_id, run.collection_id, run.id, require_current=True
    )
    _, raw = await read(db, blob, run, "input_snapshot")
    snapshot = json.loads(raw)
    return ReviewMaterial(
        bundle,
        {
            "topic": run.topic,
            "documents": snapshot["documents"],
            "draft": bundle.content,
            "source_units": source_units(snapshot["documents"]),
            "draft_units": draft_units(bundle.content),
        },
    )
