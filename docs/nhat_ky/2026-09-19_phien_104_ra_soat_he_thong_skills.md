# Nhật Ký Phiên #104 — Rà Soát Hệ Thống Skills

- **Thời gian**: 2026-09-19 13:55 (UTC+7)
- **Mục tiêu**: Đánh giá sâu hệ thống skill QNU, tập trung vào chi phí token, ranh giới kích hoạt, độ trùng lặp và mức độ đồng bộ với codebase hiện tại.

## Kết Quả Rà Soát

| Skill | Dung lượng | Nhận xét chính |
| :--- | ---: | :--- |
| `qnu-backend-architect` | 4.391 byte | Tương đối gọn; cần thống nhất lệnh pytest và chỉ kích hoạt khi thực sự sửa module Backend. |
| `qnu-frontend-architect` | 14.705 byte | Nặng nhất; trùng nhiều với `AGENTS.md`; quy tắc Offline Seed Fallback xung đột với LiveMode fail-closed. |
| `qnu-chatbot-builder` | 7.073 byte | Quy trình 7 bước hữu ích nhưng trùng gần nguyên vẹn mục Assistant Lifecycle trong `AGENTS.md`; cần tránh kích hoạt khi chỉ hỏi/review trợ lý. |
| `qnu-rag-pipeline` | 4.292 byte | Kích thước hợp lý nhưng có đường dẫn repo cũ và mô tả payload `is_active` không còn khớp `document_status`/`is_retrievable`. |
| `qnu-knowledge-ingestion` | 3.999 byte | Gọn và có ranh giới tương đối tốt; cần sửa liên kết repo cũ và dừng phạm vi tại bước tạo index. |
| `qnu-modelops-resilience` | 2.729 byte | Gọn nhất; ranh giới Provider/Quota/Circuit Breaker rõ. |
| `qnu-clean-code-architect` | 9.878 byte | Trigger rộng nhất và trùng mạnh với `AGENTS.md`; nên tắt implicit invocation, chỉ dùng rõ ràng cho refactor/cleanup/code review. |

Tổng 7 skill là **47.067 byte**, ước tính khoảng **10.300 token** nếu cùng được nạp. Không có skill nào chứa `agents/openai.yaml`, nên chưa có cấu hình `policy.allow_implicit_invocation: false`.

## Các Điểm Không Đồng Bộ

1. Có 10 liên kết `file:///` trỏ về đường dẫn cũ `D:/DuAnPhanMem/DeTaiAI/qnu-ai-platform`.
2. Skill Frontend yêu cầu tự nạp seed khi Backend ngắt kết nối, trong khi `AGENTS.md` yêu cầu LiveMode hiển thị lỗi/trống và cấm dữ liệu nghiệp vụ giả.
3. Skill Backend dùng `uv run pytest -v`, còn quy chuẩn dự án dùng `uv run --extra dev pytest -v`.
4. Skill Clean Code đề nghị `ruff --fix` toàn repo; thao tác này có thể sửa lan sang phần đang được session khác phát triển.
5. Skill RAG mô tả Qdrant payload `is_active=true`, trong khi code hiện tại dùng `document_status`, `is_retrievable`, `tenant_id`, `workspace_id`.

## Khuyến Nghị

- Mỗi task chỉ chọn **1 skill chính**, thêm tối đa **1 skill hỗ trợ** khi thật sự đi qua ranh giới domain.
- Tắt implicit invocation cho `qnu-clean-code-architect`; thu hẹp trigger Chatbot và Frontend bằng loại tác vụ/tệp cụ thể.
- Rút skill cốt lõi về khoảng 60–100 dòng; chuyển ví dụ dài, sơ đồ và bảng token sang `references/` để chỉ đọc khi cần.
- Chỉ giữ một nguồn sự thật: `AGENTS.md` định tuyến và nguyên tắc tối thiểu; chi tiết domain nằm trong skill, không sao chép hai lần.
- Sửa đường dẫn cũ và các quy tắc đã lệch code trước khi tiếp tục mở rộng skill.

Tham chiếu: [OpenAI Docs về Skills](https://developers.openai.com/es-419/docs/build-skills) — skill dùng progressive disclosure và có thể tắt implicit invocation bằng `agents/openai.yaml`.

## Verification

- Đây là phiên review tài liệu, không thay đổi skill, code, runtime hay dữ liệu.
- Không chạy lint/typecheck/build/pytest vì không có thay đổi mã nguồn.
