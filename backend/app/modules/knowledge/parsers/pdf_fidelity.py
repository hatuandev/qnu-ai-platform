"""Repeat native capture against original PDF bytes before accepting derived content."""

from __future__ import annotations

import copy
import hashlib

import pymupdf

from app.modules.knowledge.normalization.qnu_markdown import QnuStructuredDocument
from app.modules.knowledge.parsers.pdf_evidence import capture_native_page
from app.modules.knowledge.parsers.pdf_structure import build_pdf_document


def verify_pdf_source(document: QnuStructuredDocument, content: bytes, evidence: dict) -> None:
    """Rebuild the core using fresh source geometry, not a stored proposal as proof.

    OCR stays in its hash-checked sidecar. A separate authenticated figure-review
    verifier checks user transcriptions; this verifier only permits that overlay
    on the exact retained figure, never on text/table blocks.
    """
    source_hash = hashlib.sha256(content).hexdigest()
    if document.source.sha256 != source_hash or evidence.get("source_sha256") != source_hash:
        raise ValueError("PDF_SOURCE_HASH_MISMATCH")
    replay = copy.deepcopy(evidence)
    with pymupdf.open(stream=content, filetype="pdf") as pdf:
        if len(pdf) != len(replay["pages"]):
            raise ValueError("PDF_PAGE_INVENTORY_MISMATCH")
        for index, page in enumerate(pdf):
            if replay["pages"][index]["page"] != index + 1:
                raise ValueError("PDF_PAGE_ORDER_MISMATCH")
            # A new header policy invalidates new extraction caches, but does not
            # reinterpret a previously saved v5 document during integrity checks.
            fresh = capture_native_page(page, allow_unshaded_headers=
                document.document_meta.get('builder_version') != 'pdf-evidence-structure/v5')
            if fresh != replay["pages"][index]["native"]:
                raise ValueError("PDF_NATIVE_EVIDENCE_MISMATCH")
    expected = build_pdf_document(replay, filename=document.source.filename, sha256=source_hash,
        legacy_v5=document.document_meta.get('builder_version') == 'pdf-evidence-structure/v5')
    if len(expected.blocks) != len(document.blocks):
        raise ValueError("PDF_BLOCK_INVENTORY_MISMATCH")
    for actual, checked in zip(document.blocks, expected.blocks, strict=True):
        comparable = actual.model_copy(deep=True)
        receipt = comparable.attributes.pop("source_figure_review", None)
        if receipt is not None and comparable.type == "figure":
            comparable.body = checked.body
            visual = {"figure_content_unverified", "visual_content_untranscribed"}
            if [f for f in comparable.quality_flags if f.code not in visual] != [
                f for f in checked.quality_flags if f.code not in visual
            ]:
                raise ValueError("PDF_FIGURE_FLAGS_MISMATCH")
            comparable.quality_flags = checked.quality_flags
        if comparable.model_dump() != checked.model_dump():
            raise ValueError("PDF_CANONICAL_SOURCE_MISMATCH")
