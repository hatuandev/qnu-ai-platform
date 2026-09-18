# NHẬT KÝ LÀM VIỆC — PHIÊN #88
# Ngày: 2026-09-18 | Phiên Làm Việc: Đánh Giá Chuyên Sâu Hệ Thống RAG

---

## 1. Mục Tiêu & Phạm Vi

- Đánh giá toàn bộ RAG từ dữ liệu Knowledge đã duyệt đến câu trả lời của Assistant.
- Rà soát Qdrant dense retrieval, PostgreSQL FTS, RRF, reranker, Structured Fact Layer, cache, ModelOps synthesis, citation/no-answer và evaluation.
- Kiểm tra read-only dữ liệu PostgreSQL và Qdrant hiện có.
- Chạy test RAG hiện tại và kiểm tra Ruff trong phạm vi module.
- Tạo tài liệu nhận xét chi tiết trong `docs/` theo yêu cầu người dùng.
- Không sửa mã nguồn RAG/ModelOps/Assistant đang được phiên khác thay đổi.

## 2. Kết Quả Chính

- Kết luận RAG ở mức **Internal Beta / RAG Engineering Preview**, điểm tổng hợp đề xuất **5.0/10**.
- Kiến trúc pipeline đạt khoảng 6.5–7.0/10, nhưng độ tin cậy dữ liệu live chỉ khoảng 2.5–3.0/10.
- Worktree hiện đã bổ sung ModelOps answer synthesis và PostgreSQL FTS `ts_rank`, là hai cải tiến đúng hướng.
- Phát hiện các rủi ro P0:
  - Sparse retrieval lấy chunks từ tài liệu `pending`.
  - `col_question_bank` có 788 facts và toàn bộ là orphan facts trỏ tới document không tồn tại.
  - Qdrant collection chuẩn `col_question_bank` rỗng; 16/17 vectors nằm ở `col_col_question_bank` legacy.
  - Mock embedding có thể chạy trong LiveMode.
  - Tenant/workspace chưa được enforce xuyên suốt DB, Qdrant, facts và cache.
  - Chat LiveMode còn business mock fallback.
- Đề xuất gói ưu tiên **RAG Data Integrity & Groundedness** trước khi tiếp tục tối ưu prompt/model/UI.

## 3. Dữ Liệu Live Ghi Nhận

- PostgreSQL:
  - `col_drafting`: 1 document `processed`, 6 chunks, 7 facts.
  - `col_question_bank`: 2 documents `pending`, 17 chunks, 788 orphan facts.
  - Admissions, Regulations và Library: 0 document/chunk/fact.
- Qdrant:
  - `col_drafting`: 6 points, vector 1024 chiều.
  - `col_question_bank`: 0 points.
  - `col_col_question_bank`: 16 points, vector 1024 chiều.
- Chất lượng chunks Question Bank: 8/17 thiếu page, 17/17 thiếu section.
- Truy vấn sparse thực tế đã trả chunks của document pending; Fact lookup đã trả facts từ document ID không tồn tại.

## 4. Tệp Thay Đổi

| Tệp | Hành động | Mô tả |
| :--- | :--- | :--- |
| [`docs/nhan_xet_rag_hien_tai_2026-09-18.md`](../nhan_xet_rag_hien_tai_2026-09-18.md) | Tạo mới | Báo cáo scorecard, dữ liệu live, P0/P1/P2, kiến trúc mục tiêu, roadmap và production gate cho RAG |
| [`docs/memory/PROJECT_CONTEXT.md`](../memory/PROJECT_CONTEXT.md) | Cập nhật | Ghi nhận kết luận phiên #88 và backlog RAG Data Integrity |
| [`docs/memory/snapshots/2026-09-18_session_88.md`](../memory/snapshots/2026-09-18_session_88.md) | Tạo mới | Snapshot trạng thái sau phiên đánh giá |
| [`docs/WORK_LOG.md`](../WORK_LOG.md) | Cập nhật | Bổ sung phiên #88 vào nhật ký tổng hợp |

Không cập nhật `docs/quy_trinh/` vì phiên này chỉ đánh giá và lập tài liệu, không thay đổi luồng nghiệp vụ hoặc mã runtime.

## 5. Verification

- `uv run --extra dev pytest tests/test_rag.py -v`: **10/10 passed**, 3 warnings.
- `uv run ruff check app/modules/rag tests/test_rag.py`: **1 lỗi import order** trong test mới thuộc session song song.
- PostgreSQL read-only: kết nối thành công, đã đối chiếu collection/document/chunk/fact/status/provenance.
- Qdrant read-only: kết nối thành công, đã đối chiếu collections, point counts, payload và vector dimension.
- Backend HTTP port 8001: không phản hồi tại thời điểm đánh giá.
- UTF-8 strict decode, mojibake scan, Markdown links và whitespace của tài liệu phiên #88: **Pass**.

## 6. Ghi Chú An Toàn Worktree

- Không sửa lỗi Ruff trong `tests/test_rag.py` vì tệp đang được phiên khác chỉnh sửa.
- Không thay đổi database, Qdrant, Redis cache, Assistant, Workflow hoặc Provider.
- Tất cả truy vấn PostgreSQL/Qdrant trong phiên này là read-only.

