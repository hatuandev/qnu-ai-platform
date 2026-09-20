# NHẬT KÝ LÀM VIỆC — PHIÊN #150

**Ngày thực hiện**: 20/09/2026  
**Tiêu đề**: Lập Kế Hoạch Chuẩn Hóa Markdown, Qdrant Và Chất Lượng Tri Thức RAG

---

## 1. Mục Tiêu

Chuyển kết quả đối chiếu hai PDF gốc và hai file Markdown đã bóc tách thành một tài liệu triển khai kỹ thuật chi tiết, giúp các phiên vibe coding tiếp theo cải thiện chất lượng dữ liệu trước khi lập chỉ mục Qdrant và tăng độ đúng của câu trả lời LLM.

## 2. Nội Dung Đã Thực Hiện

- Xác định kiến trúc đích từ PDF/DOCX đến Canonical Document Model, Domain Records, Quality Gate, Structured Facts, Chunks và Qdrant.
- Mô tả nguyên nhân gốc gây dữ liệu bảng trùng do kết hợp `page.get_text()` với Markdown table.
- Lập kế hoạch tái dựng bảng nhiều trang, xử lý ô gộp, hàng mồ côi và hai bảng song song.
- Định nghĩa model typed và mã giả Python cho parser, table reconstruction, conflict detector và embedding text.
- Thiết kế record nghiệp vụ riêng cho tuyển sinh và kế hoạch nhiệm vụ.
- Thiết kế record-aware chunking, fact routing, claim–citation guard và revision-safe Qdrant indexing.
- Xây dựng lộ trình sáu đợt, test matrix, quality metrics, anti-patterns và Definition of Done.

## 3. Các Tệp Đã Thay Đổi

| Tệp | Hành động | Mô tả |
| :--- | :--- | :--- |
| `docs/ke_hoach/10_ke_hoach_chuan_hoa_markdown_qdrant_va_chat_luong_rag.md` | NEW | Kế hoạch/hướng dẫn triển khai chi tiết 20 mục cho ingestion và RAG data quality. |
| `docs/ke_hoach/README.md` | MODIFY | Bổ sung Kế hoạch 10 vào mục lục. |
| `docs/nhat_ky/2026-09-20_phien_150_lap_ke_hoach_chuan_hoa_markdown_qdrant_rag.md` | NEW | Nhật ký phiên #150. |
| `docs/WORK_LOG.md` | MODIFY | Đồng bộ phiên #150 vào sổ mục lục. |
| `docs/memory/PROJECT_CONTEXT.md` | MODIFY | Cập nhật trạng thái dự án và backlog triển khai Kế hoạch 10. |
| `docs/memory/snapshots/2026-09-20_session_150.md` | NEW | Snapshot bộ nhớ của phiên #150. |

## 4. Đồng Bộ Quy Trình

Phiên này chỉ tạo tài liệu kế hoạch, chưa thay đổi parser, lifecycle, database schema hoặc luồng Frontend ↔ Backend ↔ Qdrant. Vì vậy chưa cập nhật `docs/quy_trinh/`. Khi bắt đầu triển khai code Đợt 1 của Kế hoạch 10, bắt buộc cập nhật quy trình nạp tri thức tương ứng.

## 5. Kết Quả Kiểm Tra

- Đọc lại file bằng UTF-8: tiếng Việt hiển thị đúng.
- `git diff --check`: không có lỗi whitespace trong file kế hoạch mới.
- Không chạy Ruff/Pytest/Frontend build vì phiên này không thay đổi mã nguồn runtime.

