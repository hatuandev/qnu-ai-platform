# Nhật Ký Làm Việc — 17/09/2026

## Tiêu đề: Cài Đợt 2 Một Lượt — EasyOCR 1.7.2 + Sentence-Transformers 6.0.1, Nối Embedding BGE-M3 Thật

### 1. Bối cảnh
Sau phiên #37 (Docling), rà soát toàn backend tìm package còn thiếu: LLM adapters dùng `httpx` trực tiếp (không cần SDK), reranker dùng endpoint ngoài + fallback RRF (giữ nguyên), chỉ còn 2 món code đã chờ sẵn: `EasyOCRAdapter` (lazy) và embedding BGE-M3 (đang mock `sin`). Quyết định cài một lượt + nối embedding thật ngay.

### 2. Các Thay Đổi Kỹ Thuật Đã Thực Hiện
1. **Cài đặt** (`backend/pyproject.toml`, `uv.lock`): `uv add easyocr sentence-transformers` → easyocr 1.7.2, sentence-transformers 6.0.1 (+15 deps: scikit-image, scikit-learn...). `EasyOCRAdapter.is_available()` lật sang True không cần sửa code.
2. **Nối embedding thật** (`backend/app/modules/rag/vector_indexer.py`):
   - Singleton lười `BAAI/bge-m3` (đúng `EMBEDDING_MODEL` trong config), batch encode qua `asyncio.to_thread`, vector chuẩn hóa, tự ép đúng 1024 chiều Qdrant.
   - Giữ `generate_embedding()` mock cũ cho tương thích + fallback mock trung thực khi thiếu package/model (log warning rõ ràng).
   - `index_chunks` embed batch một lượt (hiệu năng), `search_dense` embed query thật.
3. **Tests mới** (`backend/tests/test_rag.py`, +3): mock deterministic/chuẩn hóa/đúng chiều, `embed_texts` fallback khi không model, `_fit_dim` pad/truncate — tất cả offline, suite không chậm đi.

### 3. Kết Quả Kiểm Thử (Verification)
- Kiểm chứng thật BGE-M3: 3 câu tiếng Việt → vector 1024 chiều, `sim(cùng chủ đề điểm chuẩn)=0.4786 > sim(khác chủ đề thời tiết)=0.4177`.
- `uv run ruff check .`: 0 lỗi.
- `uv run --extra dev pytest -q`: **83/83 passed** (~62s, không test nào tải model nặng).
- Chưa làm (để phiên sau): cross-encoder rerank local `bge-reranker-v2-m3` (model ~1.2GB, endpoint ngoài + fallback RRF hiện vẫn đủ dùng).
