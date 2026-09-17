"""Unit & Integration Tests for Knowledge Base, Parsers, Cleaners and Chunkers."""

import io

import docx
import fitz
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.knowledge.chunker import ClauseBasedChunker, SemanticChunker
from app.modules.knowledge.cleaner import clean_markdown_text, extract_sections_metadata
from app.modules.knowledge.parsers import DocxParser, PlainTextParser, PyMuPdfParser


def test_clean_markdown_text():
    """Verify document cleaning strips page numbers and collapses excess spaces."""
    raw = "Cộng hòa xã hội chủ nghĩa Việt Nam\n\n  — 15 —  \n\nQuy chế đào tạo tín chỉ.\n\n\n\nĐiều 1.   Phạm vi áp dụng"
    cleaned = clean_markdown_text(raw)
    assert "— 15 —" not in cleaned
    assert "Điều 1. Phạm vi áp dụng" in cleaned
    assert "\n\n\n\n" not in cleaned


def test_extract_sections_metadata():
    """Verify legal section extraction regex."""
    text = "Điều 1. Phạm vi\nNội dung điều 1...\nĐiều 2. Đối tượng\nNội dung điều 2..."
    sections = extract_sections_metadata(text)
    assert len(sections) == 2
    assert sections[0]["number"] == "1"
    assert sections[1]["number"] == "2"


def test_clause_based_chunker():
    """Verify ClauseBasedChunker splits text on legal articles (Điều) and preserves preamble."""
    text = (
        "QUY CHẾ ĐÀO TẠO ĐẠI HỌC\n\n"
        "Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng\n"
        "1. Quy chế này quy định về đào tạo trình độ đại học theo hệ thống tín chỉ...\n\n"
        "Điều 2. Chương trình đào tạo và thời gian học tập\n"
        "1. Chương trình đào tạo được xây dựng theo đơn vị tín chỉ...\n"
    )
    chunker = ClauseBasedChunker()
    chunks = chunker.chunk(text)
    assert len(chunks) == 3
    assert chunks[1].section is not None
    assert "Điều 1" in chunks[1].section
    assert "Điều 2" in chunks[2].section
    assert chunks[1].chunk_hash != chunks[2].chunk_hash


def test_semantic_chunker():
    """Verify SemanticChunker splits on paragraphs within max token limit."""
    text = "Đoạn văn thứ nhất nói về chỉ tiêu tuyển sinh năm 2026.\n\n" * 20
    chunker = SemanticChunker(max_tokens=100)
    chunks = chunker.chunk(text)
    assert len(chunks) > 1
    for c in chunks:
        assert c.token_count <= 120


@pytest.mark.asyncio
async def test_pymupdf_parser_in_memory():
    """Create an in-memory PDF and verify PyMuPdfParser extracts text accurately."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "QNU Admissions 2026 - Information Guide")
    pdf_bytes = doc.write()
    doc.close()

    parser = PyMuPdfParser()
    parsed = await parser.parse(pdf_bytes, "test_tuyensinh.pdf")
    assert parsed.page_count == 1
    assert "QNU Admissions 2026 - Information Guide" in parsed.raw_text


@pytest.mark.asyncio
async def test_docx_parser_in_memory():
    """Create an in-memory DOCX and verify DocxParser extracts headings and paragraphs."""
    doc = docx.Document()
    doc.add_heading("QUY CHẾ HỌC VỤ", level=1)
    doc.add_paragraph("Điều 1. Đăng ký học phần trong học kỳ chính.")

    # Add table
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Học kỳ"
    table.rows[0].cells[1].text = "Số tín chỉ tối đa"
    table.rows[1].cells[0].text = "Học kỳ 1"
    table.rows[1].cells[1].text = "24"

    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    parser = DocxParser()
    parsed = await parser.parse(docx_bytes, "quyche.docx")
    assert "QUY CHẾ HỌC VỤ" in parsed.raw_text
    assert "Điều 1. Đăng ký học phần" in parsed.raw_text
    assert len(parsed.tables) == 1
    assert "Số tín chỉ tối đa" in parsed.tables[0].markdown_repr


@pytest.mark.asyncio
async def test_plain_text_parser():
    """Verify PlainTextParser handles text files."""
    content = "Khoa Công nghệ thông tin - Trường Đại học Quy Nhơn".encode()
    parser = PlainTextParser()
    parsed = await parser.parse(content, "sample.txt")
    assert parsed.raw_text == "Khoa Công nghệ thông tin - Trường Đại học Quy Nhơn"


@pytest.mark.asyncio
async def test_parse_preview_blank_scan_returns_empty_honestly():
    """Scanned PDF with no text layer must preview empty, never hallucinated."""
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()
    files = {"file": ("blank_scan.pdf", pdf_bytes, "application/pdf")}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/platform/v1alpha1/knowledge/collections/col_demo/parse-preview?strategy=semantic",
            files=files,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["raw_markdown"] == ""
    assert data["chunk_count"] == 0
    assert data["ocr_method"] == "PyMuPdfParser"


@pytest.mark.asyncio
async def test_approve_archived_document_is_rejected():
    """Approving an archived document must fail loudly with 409."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.core.exceptions import AppException
    from app.modules.knowledge.service import knowledge_service

    archived_doc = MagicMock()
    archived_doc.is_active = False
    archived_doc.status = "archived"

    with (
        patch.object(
            knowledge_service, "get_document", new=AsyncMock(return_value=archived_doc)
        ),
        pytest.raises(AppException) as exc_info,
    ):
        await knowledge_service.approve_document(
            db=AsyncMock(), document_id="doc_archived", pages=None
        )
    assert exc_info.value.status_code == 409


def test_to_percent_coordinates_in_range():
    """Percent bboxes must stay within 0-100 and preserve geometry order."""
    from app.modules.knowledge.parsers.blocks import to_percent

    coords = to_percent(50, 100, 300, 400, 595, 842)
    assert 0 <= coords["x"] <= 100
    assert 0 <= coords["y"] <= 100
    assert coords["width"] > 0 and coords["height"] > 0
    assert coords["x"] + coords["width"] <= 100.01


@pytest.mark.asyncio
async def test_pdf_parser_emits_real_geometry_blocks():
    """PyMuPDF parser must attach real text blocks with percent coordinates."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 50), " Dieu 1. Pham vi ap dung", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()

    parser = PyMuPdfParser()
    parsed = await parser.parse(pdf_bytes, "quyche.pdf")
    text_blocks = [b for b in parsed.blocks if b["type"] == "text"]
    assert len(text_blocks) >= 1
    coords = text_blocks[0]["coordinates"]
    assert 0 < coords["x"] < 50
    assert 0 < coords["y"] < 50
    assert "Pham vi" in text_blocks[0]["content_snippet"]


def test_build_studio_pages_merges_chunks_and_boxes():
    """Pure studio builder must group chunks, attach boxes and derive regions."""
    from app.modules.knowledge.service import knowledge_service

    chunks = [
        {"content": "Dieu 1.", "chunk_index": 0, "page_number": 1},
        {"content": "Dieu 2.", "chunk_index": 1, "page_number": 2},
    ]
    page_blocks = {
        1: [
            {
                "type": "text",
                "coordinates": {"x": 5, "y": 6, "width": 90, "height": 8},
                "label": "Khoi van ban 1",
                "content_snippet": "Dieu 1.",
            }
        ]
    }
    pages = knowledge_service.build_studio_pages(
        chunks=chunks, page_blocks=page_blocks, document_id="doc_x"
    )
    assert len(pages) == 2
    assert "Dieu 1." in pages[0]["markdown_content"]
    assert len(pages[0]["bounding_boxes"]) == 1
    assert pages[0]["bounding_boxes"][0]["id"].startswith("box_doc_x_p1_")
    assert len(pages[0]["regions"]) == 1
    assert pages[0]["regions"][0]["reading_order"] == 1
    assert pages[1]["bounding_boxes"] == []
    assert pages[1]["regions"] == []


@pytest.mark.asyncio
async def test_api_studio_view_missing_document_returns_404():
    """GET studio-view must return RFC 7807 404 for unknown documents (no DB)."""
    from unittest.mock import AsyncMock, patch

    from app.core.database import get_db
    from app.core.exceptions import EntityNotFoundError
    from app.modules.knowledge.service import knowledge_service

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch.object(
            knowledge_service,
            "get_document",
            new=AsyncMock(
                side_effect=EntityNotFoundError(
                    "Tài liệu 'doc_missing' không tồn tại.",
                    details={"document_id": "doc_missing"},
                )
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(
                    "/platform/v1alpha1/knowledge/documents/doc_missing/studio-view"
                )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert response.json()["code"] == "entity_not_found"


@pytest.mark.asyncio
async def test_api_page_image_unsupported_type_returns_404():
    """Page preview of non-PDF documents must fail loudly, not silently."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.core.database import get_db
    from app.modules.knowledge.service import knowledge_service

    fake_doc = SimpleNamespace(
        id="doc_x", file_type="docx", file_name="quyche.docx", storage_path="uploads/x"
    )

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch.object(
            knowledge_service, "get_document", new=AsyncMock(return_value=fake_doc)
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.get(
                    "/platform/v1alpha1/knowledge/documents/doc_x/pages/1/image"
                )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_render_page_image_docx_via_gotenberg():
    """DOCX pages must render to PNG through the office converter (mocked)."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    import fitz

    from app.modules.knowledge.service import knowledge_service

    pdf_doc = fitz.open()
    pdf_doc.new_page(width=400, height=500)
    pdf_bytes = pdf_doc.tobytes()
    pdf_doc.close()

    fake_doc = SimpleNamespace(
        id="doc_office", collection_id="col_1", file_type="docx",
        file_name="ke_hoach.docx", storage_path="uploads/col_1/ke_hoach.docx",
    )
    with (
        patch.object(knowledge_service, "get_document", new=AsyncMock(return_value=fake_doc)),
        patch.object(
            knowledge_service, "_convert_office_to_pdf", new=AsyncMock(return_value=pdf_bytes)
        ),
        patch("app.modules.knowledge.service.storage_service") as mock_storage,
    ):
        mock_storage.get = AsyncMock(side_effect=[None, pdf_bytes])
        mock_storage.save = AsyncMock()
        png = await knowledge_service.render_page_image(AsyncMock(), "doc_office", 1)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.asyncio
async def test_office_convert_failure_raises_422():
    """Gotenberg errors must surface as honest 422, never fake images."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    import pytest

    from app.core.exceptions import AppException
    from app.modules.knowledge.service import knowledge_service

    fake_resp = SimpleNamespace(status_code=500, content=b"convert error")
    fake_client = AsyncMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.post = AsyncMock(return_value=fake_resp)
    with (
        patch("httpx.AsyncClient", return_value=fake_client),
        pytest.raises(AppException) as exc_info,
    ):
        await knowledge_service._convert_office_to_pdf(b"xx", "bao_cao.docx")
    assert exc_info.value.code == "office_convert_failed"
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_studio_view_reports_size_and_chunks():
    """Studio view must carry real file size and chunk counts (no more 0 MB)."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.modules.knowledge.service import knowledge_service

    chunks = [
        SimpleNamespace(content="Dieu 1.", chunk_index=0, page_number=1),
        SimpleNamespace(content="Dieu 2.", chunk_index=1, page_number=1),
    ]
    fake_doc = SimpleNamespace(
        id="doc_sz", collection_id="col_1", title="Ke hoach", file_name="kh.docx",
        file_size_bytes=58320, doc_metadata={"ocr_method": "DocxParser"}, chunks=chunks,
    )
    with patch.object(
        knowledge_service, "get_document", new=AsyncMock(return_value=fake_doc)
    ):
        view = await knowledge_service.get_studio_view(AsyncMock(), "doc_sz")
    assert view["file_size_bytes"] == 58320
    assert view["total_chunks"] == 2
    assert view["pages"][0]["word_count"] > 0


@pytest.mark.asyncio
async def test_batch_approve_partial_failure():
    """Batch approve must report per-item results without aborting the batch."""
    from unittest.mock import AsyncMock, patch

    from app.core.exceptions import EntityNotFoundError
    from app.modules.knowledge.service import knowledge_service

    async def fake_approve(db, document_id, pages=None):
        if document_id == "doc_ok":
            return {"document_id": "doc_ok", "status": "approved",
                    "total_chunks": 4, "indexed_chunks": 4}
        raise EntityNotFoundError(f"Tài liệu '{document_id}' không tồn tại.")

    with patch.object(
        knowledge_service, "approve_document", new=AsyncMock(side_effect=fake_approve)
    ):
        result = await knowledge_service.batch_approve_documents(
            AsyncMock(), ["doc_ok", "doc_ok", "doc_missing"]
        )
    assert result["approved"] == ["doc_ok"]
    assert len(result["failed"]) == 1
    assert result["failed"][0]["document_id"] == "doc_missing"
    assert result["indexed_chunks"] == 4


@pytest.mark.asyncio
async def test_download_document_happy_path():
    """Download must return original bytes with attachment disposition."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.modules.knowledge.service import knowledge_service

    fake_doc = SimpleNamespace(
        id="doc_dl", file_name="ke_hoach.docx", file_type="docx", storage_path="u/k.docx"
    )
    with (
        patch.object(knowledge_service, "get_document", new=AsyncMock(return_value=fake_doc)),
        patch(
            "app.modules.knowledge.service.storage_service",
            get=AsyncMock(return_value=b"PK-fake-docx"),
        ),
    ):
        content, filename, media_type = await knowledge_service.download_document(
            AsyncMock(), "doc_dl"
        )
    assert content == b"PK-fake-docx"
    assert filename == "ke_hoach.docx"
    assert "wordprocessingml" in media_type


@pytest.mark.asyncio
async def test_download_missing_original_returns_404():
    """Missing stored bytes must 404 honestly instead of empty download."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    import pytest

    from app.core.exceptions import EntityNotFoundError
    from app.modules.knowledge.service import knowledge_service

    fake_doc = SimpleNamespace(
        id="doc_gone", file_name="a.pdf", file_type="pdf", storage_path="u/a.pdf"
    )
    with (
        patch.object(knowledge_service, "get_document", new=AsyncMock(return_value=fake_doc)),
        patch(
            "app.modules.knowledge.service.storage_service",
            get=AsyncMock(return_value=None),
        ),pytest.raises(EntityNotFoundError)
    ):
        await knowledge_service.download_document(AsyncMock(), "doc_gone")


@pytest.mark.asyncio
async def test_api_reindex_enqueues_job():
    """POST reindex must enqueue a tracked job instead of faking success."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.core.database import get_db
    from app.modules.knowledge.service import knowledge_service

    fake_col = SimpleNamespace(id="col_1", module_code="admissions")

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with (
            patch.object(
                knowledge_service, "get_collection", new=AsyncMock(return_value=fake_col)
            ),
            patch(
                "app.modules.jobs.service.enqueue_arq_job", new=AsyncMock(return_value="arq-1")
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.post("/platform/v1alpha1/knowledge/collections/col_1/reindex")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_api_collection_test_searches_for_real():
    """POST test must run hybrid retrieval, not return canned chunks."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.core.database import get_db
    from app.modules.knowledge.service import knowledge_service
    from app.modules.rag.fusion import FusionCandidate

    fake_col = SimpleNamespace(id="col_1", module_code="admissions")
    candidate = FusionCandidate(
        chunk_id="chk_1", document_id="doc_1", content="Điểm chuẩn 24.5", rrf_score=0.09,
        section="Điều 1", page_number=2,
    )

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with (
            patch.object(
                knowledge_service, "get_collection", new=AsyncMock(return_value=fake_col)
            ),
            patch(
                "app.modules.rag.retriever.hybrid_retriever.retrieve",
                new=AsyncMock(return_value=[candidate]),
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                response = await ac.post(
                    "/platform/v1alpha1/knowledge/collections/col_1/test",
                    params={"query": "điểm chuẩn", "top_k": 5},
                )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["total_found"] == 1
    assert data["items"][0]["chunk_id"] == "chk_1"
    assert data["items"][0]["page_number"] == 2


@pytest.mark.asyncio
async def test_api_parse_preview():
    """Verify POST /platform/v1alpha1/knowledge/collections/{id}/parse-preview endpoint."""
    sample_txt = (
        "Điều 1. Giới thiệu chung về ngành CNTT.\n\nĐiều 2. Chuẩn đầu ra tốt nghiệp.".encode()
    )
    files = {"file": ("demo.txt", sample_txt, "text/plain")}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/platform/v1alpha1/knowledge/collections/col_demo/parse-preview?strategy=clause",
            files=files,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["file_name"] == "demo.txt"
    assert data["chunk_count"] == 2
    assert len(data["preview_chunks"]) == 2


def test_build_studio_pages_per_page_markdown_and_blocks():
    """Verify studio builder preserves per-page markdown and does not clump chunks into page 1."""
    from app.modules.knowledge.service import knowledge_service

    chunks = [
        {"content": "Toan bo noi dung trang 1 va 2.", "chunk_index": 0, "page_number": 1},
    ]
    page_blocks = {
        1: [
            {
                "type": "title",
                "text": "THONG BAO TUYEN SINH 2026",
                "coordinates": {"x": 10, "y": 10, "width": 80, "height": 10},
            }
        ],
        2: [
            {
                "type": "text",
                "text": "Phuong thuc 1: Xet diem thi THPT.",
                "coordinates": {"x": 10, "y": 10, "width": 80, "height": 20},
            }
        ],
    }
    page_markdowns = {
        1: "# THONG BAO TUYEN SINH 2026\n\nNoi dung trang 1.",
        2: "## Phuong thuc xet tuyen\n\n| STT | Nganh |\n| --- | --- |\n| 1 | CNTT |",
    }
    pages = knowledge_service.build_studio_pages(
        chunks=chunks,
        page_blocks=page_blocks,
        document_id="doc_ts",
        page_markdowns=page_markdowns,
    )
    assert len(pages) == 2
    assert "Noi dung trang 1." in pages[0]["markdown_content"]
    assert "Phuong thuc xet tuyen" in pages[1]["markdown_content"]
    assert "| CNTT |" in pages[1]["markdown_content"]
    assert pages[1]["page_number"] == 2
    assert len(pages[1]["bounding_boxes"]) == 1


def test_build_studio_pages_synthesizes_from_blocks_when_chunks_clumped():
    """When chunks are clumped into page 1 without page_markdowns, builder synthesizes per-page markdown from blocks."""
    from app.modules.knowledge.service import knowledge_service

    chunks = [
        {"content": "Chunk duy nhat bi don vao trang 1.", "chunk_index": 0, "page_number": 1},
    ]
    page_blocks = {
        1: [
            {
                "type": "title",
                "text": "Tieu de trang 1",
                "coordinates": {"x": 10, "y": 10, "width": 80, "height": 10},
            }
        ],
        2: [
            {
                "type": "header",
                "text": "Muc II. Phuong thuc",
                "coordinates": {"x": 10, "y": 10, "width": 80, "height": 10},
            },
            {
                "type": "list",
                "text": "Xet tuyen hoc ba",
                "coordinates": {"x": 10, "y": 25, "width": 80, "height": 10},
            },
        ],
    }
    pages = knowledge_service.build_studio_pages(
        chunks=chunks,
        page_blocks=page_blocks,
        document_id="doc_test",
        page_markdowns=None,
    )
    assert len(pages) == 2
    assert "Tieu de trang 1" in pages[0]["markdown_content"]
    assert "Muc II. Phuong thuc" in pages[1]["markdown_content"]
    assert "- Xet tuyen hoc ba" in pages[1]["markdown_content"]
    assert pages[1]["markdown_content"] != ""  # Trang 2 tuyệt đối không bị trắng tinh!


def test_chunkers_track_page_number_from_page_markers():
    """Chunkers must track page numbers accurately from '<!-- Trang X -->' markers."""
    from app.modules.knowledge.chunker import ClauseBasedChunker, SemanticChunker

    text = (
        "<!-- Trang 1 -->\n\n"
        "Điều 1. Ban hành quy chế\n\n"
        "Quy chế này áp dụng cho toàn bộ giảng viên và sinh viên.\n\n"
        "<!-- Trang 2 -->\n\n"
        "Điều 2. Tổ chức thực hiện\n\n"
        "Phòng Đào tạo chủ trì phối hợp với các khoa thực hiện."
    )

    clause_chunks = ClauseBasedChunker().chunk(text)
    assert len(clause_chunks) >= 2
    assert clause_chunks[0].page_number == 1
    assert "Điều 1" in clause_chunks[0].content
    assert clause_chunks[1].page_number == 2
    assert "Điều 2" in clause_chunks[1].content

    sem_chunks = SemanticChunker(max_tokens=30).chunk(text)
    assert len(sem_chunks) >= 2
    pages_found = {c.page_number for c in sem_chunks if c.page_number is not None}
    assert 1 in pages_found
    assert 2 in pages_found


def test_build_studio_pages_rejects_synthetic_placeholders():
    """Studio builder must discard synthetic placeholder strings like 'Đoạn văn bản quy định'."""
    from app.modules.knowledge.service import knowledge_service

    page_blocks = {
        1: [
            {"type": "header", "text": "Tiêu đề đầu trang", "coordinates": {}},
            {"type": "text", "text": "Đoạn văn bản quy định", "coordinates": {}},
            {"type": "table", "text": "Bảng biểu số liệu", "coordinates": {}},
            {"type": "signature", "text": "Con dấu & Chữ ký xác thực", "coordinates": {}},
        ]
    }
    pages = knowledge_service.build_studio_pages(
        chunks=[],
        page_blocks=page_blocks,
        document_id="doc_zero",
        page_markdowns=None,
    )
    assert len(pages) == 1
    # All synthetic strings must be completely rejected — zero mock text in output
    assert "Đoạn văn bản quy định" not in pages[0]["markdown_content"]
    assert "Bảng biểu số liệu" not in pages[0]["markdown_content"]
    assert pages[0]["markdown_content"] == ""

