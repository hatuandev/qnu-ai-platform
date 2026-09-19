---
name: qnu-knowledge-ingestion
description: >-
  Use this skill when implementing document parsers (PDF, DOCX, XLSX), tuning chunking strategies (ClauseBasedChunker, SemanticChunker), cleaning OCR/Vietnamese text artifacts, or optimizing the document ingestion pipeline. Do NOT use for general chat or search retrieval logic.
---

# Hướng Dẫn Bóc Tách Tài Liệu & Quản Trị Tri Thức QNU AI Platform

Tài liệu hướng dẫn chuyên sâu cho module **Knowledge & Document Intelligence** ([backend/app/modules/knowledge](backend/app/modules/knowledge)).

---

## 1. Luồng Tiếp Nhận Tài Liệu (Ingestion Pipeline)

Quy trình ingestion diễn ra qua 7 bước nghiêm ngặt:
1. **Tiếp nhận & Tính Checksum**:
   - Khi tải tệp lên, tính mã băm `file_hash = sha256(content)`.
   - Kiểm tra trong bảng `knowledge_documents`: Nếu cùng `collection_id` và cùng `file_hash` đã tồn tại, từ chối tải lên để chống lãng phí lưu trữ và trùng lặp vector.
2. **Lưu trữ tệp gốc**:
   - Gọi `StorageDriver` (`LocalStorageDriver` hoặc `S3StorageDriver`) để lưu trữ an toàn trước khi bóc tách.
3. **Bóc tách nội dung (Document Parser Strategy)**:
   - File PDF: `PyMuPdfParser` bóc tách text, trang và bảng biểu siêu tốc.
   - File Word DOCX: `DocxParser` bảo toàn cấu trúc Heading 1, 2 và Table.
   - File Excel XLSX: `ExcelParser` chuyển đổi mỗi bảng tính thành Bảng Markdown.
   - File Plain Text/CSV: `PlainTextParser`.
4. **Làm sạch văn bản chuyên biệt tiếng Việt ([cleaner.py](backend/app/modules/knowledge/cleaner.py))**:
   - **Khử Mojibake & Chuẩn hóa Unicode NFC**: Sử dụng `unicodedata.normalize("NFC", text)` để đồng nhất bảng mã tiếng Việt dựng sẵn, loại bỏ hoàn toàn ký tự lỗi thay thế `\ufffd` hoặc chuỗi rác do sai encoding.
   - Xóa ngắt dòng giữa câu do scan/OCR (`\n` không cần thiết).
   - Xóa các dòng số trang lẻ loi, header/footer lặp lại.
   - Căn chỉnh lại các cột bảng Markdown bị lệch hoặc rách hàng.
   - Chuẩn hóa cấu trúc tiêu đề pháp quy: *"Điều 1.", "Khoản 2.", "Chương III."*
5. **Cắt đoạn thông minh (Chunking Strategy)**:
   - **`ClauseBasedChunker`** (Dành cho văn bản pháp quy, quyết định, quy chế): Cắt chuẩn xác theo từng **Điều** (*Điều 1, Điều 2...*), gán nhãn `section` vào từng chunk để trích dẫn pháp lý chính xác.
   - **`SemanticChunker`** (Dành cho cẩm nang, tài liệu giới thiệu chung): Cắt theo đoạn văn ngữ nghĩa kèm token overlap.
6. **Trích xuất sự thật dạng bảng (Fact Extraction)**:
   - Trích xuất các thực thể quan trọng (Ngành học, Điểm chuẩn, Chỉ tiêu, Học phí) vào bảng `knowledge_facts`.
7. **Đánh chỉ mục Vector**:
   - Lưu vào PostgreSQL và chuyển sang Qdrant vector index.

---

## 2. Cách Viết Thêm Một Parser Mới

Để hỗ trợ thêm định dạng tài liệu mới (ví dụ: PowerPoint PPTX, Markdown nâng cao, hoặc HTML):
1. Tạo class mới kế thừa `BaseDocumentParser` trong [backend/app/modules/knowledge/parsers/](backend/app/modules/knowledge/parsers/):
   ```python
   from app.modules.knowledge.parsers.base import BaseDocumentParser, ParsedDocument
   
   class PptxParser(BaseDocumentParser):
       async def parse(self, content: bytes, filename: str) -> ParsedDocument:
           # Logic bóc tách tệp trình chiếu
           return ParsedDocument(
               raw_text=extracted_text,
               page_count=slide_count,
               tables=[],
               sections=[]
           )
   ```
2. Đăng ký đuôi mở rộng `.pptx` vào hàm factory `get_document_parser(ext)` tại `parsers/__init__.py`.
3. Viết unit test bổ sung trong `tests/test_knowledge.py`.

