# NHẬT KÝ LÀM VIỆC — PHIÊN #86
# Ngày: 2026-09-18 | Phiên Làm Việc: Đánh Giá Chuyên Sâu Kho Tri Thức

---

## 1. Mục Tiêu & Phạm Vi

- Đánh giá riêng chức năng Kho tri thức theo hai chuẩn `qnu-knowledge-ingestion` và `qnu-rag-pipeline`.
- Rà soát ingestion, OCR, chunking, facts, approval, Qdrant indexing, retrieval, citation, tenant isolation và Frontend fallback.
- Kiểm tra trực tiếp dữ liệu Qdrant hiện có.
- Tạo tài liệu nhận xét chi tiết trong thư mục `docs/` theo yêu cầu người dùng.
- Không sửa mã nguồn, dữ liệu hoặc các file ModelOps đang được phiên khác xử lý.

## 2. Kết Quả Chính

- Kết luận Kho tri thức ở mức **Internal Beta**, điểm tổng hợp đề xuất **6.0/10**.
- Document Intelligence và trải nghiệm đối soát đạt khoảng 7.5–8.0/10.
- Độ tin cậy khi dùng làm nguồn RAG production chỉ khoảng 4.5–5.0/10.
- Phát hiện lệch Qdrant collection:
  - `col_col_question_bank`: 16 points.
  - `col_question_bank`: 0 points.
  - `col_drafting`: 6 points.
- Xác định các rủi ro P0: approved trước khi index thành công, ghost vectors, mock embedding trong runtime, thiếu tenant filter xuyên suốt và lệch tên collection.
- Xác định các rủi ro P1: lexical search dùng `ILIKE`, dense/sparse tuần tự, facts có thể cũ sau hiệu đính, job hoàn tất sớm, chunking policy gán cứng và Frontend LiveMode còn mock fallback.

## 3. Tệp Thay Đổi

| Tệp | Hành động | Mô tả |
| :--- | :--- | :--- |
| [`docs/nhan_xet_kho_tri_thuc_2026-09-18.md`](../nhan_xet_kho_tri_thuc_2026-09-18.md) | Tạo mới | Báo cáo chuyên sâu, scorecard, bằng chứng Qdrant, rủi ro P0/P1/P2, roadmap và production acceptance gate |
| [`docs/memory/PROJECT_CONTEXT.md`](../memory/PROJECT_CONTEXT.md) | Cập nhật | Ghi nhận kết luận và backlog Knowledge Index Integrity |
| [`docs/memory/snapshots/2026-09-18_session_86.md`](../memory/snapshots/2026-09-18_session_86.md) | Tạo mới | Snapshot trạng thái sau phiên đánh giá |
| [`docs/WORK_LOG.md`](../WORK_LOG.md) | Cập nhật | Bổ sung phiên #86 vào nhật ký tổng hợp |

Không cập nhật `docs/quy_trinh/` vì phiên này chỉ đánh giá và lập tài liệu, không thay đổi luồng nghiệp vụ hoặc mã runtime.

## 4. Verification

- Đối chiếu mã nguồn Knowledge, RAG, Storage và Frontend API client: hoàn tất.
- Qdrant collections/points/payload: kiểm tra trực tiếp thành công.
- Kiểm tra Backend API tại port 8001: không kết nối được tại thời điểm rà soát; sử dụng số liệu live của phiên #85 cho phần PostgreSQL/API.
- Không chạy lại Ruff/Pytest/Lint/Typecheck/Build vì phiên này chỉ thay đổi Markdown và worktree đang có mã ModelOps từ phiên song song.
- UTF-8 strict decode: **Pass** cho 5 file tài liệu được tạo/cập nhật.
- Mojibake scan trên 3 file mới: **Pass**, không phát hiện chuỗi lỗi mã hóa hoặc ký tự thay thế Unicode.
- Whitespace và liên kết file: **Pass** sau khi chuẩn hóa phần metadata đầu báo cáo.
- `git diff --check` trên hai file tracked được cập nhật: **Pass**; kiểm tra toàn worktree còn báo hai dòng trắng cuối file thuộc ModelOps session song song, không thuộc phạm vi phiên này.

## 5. Ghi Chú An Toàn Worktree

- Giữ nguyên toàn bộ thay đổi đang có trong Backend/Frontend ModelOps.
- Không thao tác seed data, migration, Qdrant point hoặc collection.
- Việc migrate `col_col_question_bank` chỉ được nêu dưới dạng khuyến nghị, chưa thực hiện.
