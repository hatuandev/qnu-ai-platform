# NHẬT KÝ LÀM VIỆC — Phiên #47
# Ngày: 2026-09-17 | Mục tiêu: Kích Hoạt Luồng Thực Thi Sơ Đồ DAG Thật 100% Cho 05 Trợ Lý AI QNU

## 1. Thời Gian & Mục Tiêu
- **Thời gian**: 2026-09-17 23:45 (UTC+7)
- **Kỹ sư / Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Khắc phục triệt để tình trạng "chạy giả" (silent fallback) của module Workflow DAG, kích hoạt 100% luồng thực thi sơ đồ DAG thực tế cho 05 Trợ lý AI QNU theo đúng file đặc tả (`configs/workflows/*.v1alpha1.json`), bảo đảm rẽ nhánh có kiểm định trích dẫn (Citation Guardrail) và chính sách từ chối (No-Answer Policy).

## 2. Chi Tiết Thay Đổi Kỹ Thuật (Key Changes)
1. [`backend/app/modules/workflows/schemas.py`](../../backend/app/modules/workflows/schemas.py):
   - Mở rộng `WorkflowEdgeSpec` bổ sung `source_port: str | None = None` và `target_port: str | None = None`.
2. [`backend/app/modules/workflows/service.py`](../../backend/app/modules/workflows/service.py):
   - Cập nhật hàm `_parse_spec_from_json`: Bóc tách an toàn `node_id` và `port` khi `source` và `target` được định nghĩa dưới dạng `dict` `{node_id, port}` hoặc `str`.
   - Giúp cả 05 file JSON mẫu (`admissions`, `regulations`, `drafting`, `library`, `question_bank`) nạp đủ 100% số lượng node thật mà không bị rơi về fallback 3 node tối giản.
3. [`backend/app/modules/workflows/nodes/base.py`](../../backend/app/modules/workflows/nodes/base.py):
   - Bổ sung trường `selected_port: str | None = None` trong `NodeExecutionResult`.
4. [`backend/app/modules/workflows/nodes/citation_guard_node.py`](../../backend/app/modules/workflows/nodes/citation_guard_node.py) [Tạo mới]:
   - Cài đặt `CitationGuardNodeHandler` cho `guard.citation_policy`: Kiểm định tính xác thực của câu trả lời từ RAG, đối soát số lượng trích dẫn và trạng thái RAG. Rẽ nhánh theo cổng `grounded` hoặc `ungrounded`.
5. [`backend/app/modules/workflows/nodes/no_answer_node.py`](../../backend/app/modules/workflows/nodes/no_answer_node.py) [Tạo mới]:
   - Cài đặt `OutputNoAnswerNodeHandler` cho `output.no_answer`: Định dạng câu trả lời từ chối lịch sự, cung cấp Hotline Tuyển sinh `0256.3846.156` hoặc phòng Đào tạo (P.108 A1) khi không có đủ tài liệu căn cứ.
6. [`backend/app/modules/workflows/nodes/extract_fields_node.py`](../../backend/app/modules/workflows/nodes/extract_fields_node.py) [Tạo mới]:
   - Cài đặt `ExtractFieldsNodeHandler` cho `extract.fields`: Trích xuất các trường nghiệp vụ phục vụ soạn thảo văn bản NĐ 30 và ma trận câu hỏi Bloom.
7. [`backend/app/modules/workflows/nodes/__init__.py`](../../backend/app/modules/workflows/nodes/__init__.py) & [`backend/app/modules/workflows/registry.py`](../../backend/app/modules/workflows/registry.py):
   - Đăng ký đầy đủ các Node Handlers mới cùng các aliases vào `NodeHandlerRegistry`.
8. [`backend/app/modules/workflows/engine.py`](../../backend/app/modules/workflows/engine.py):
   - Hỗ trợ tra cứu node kế tiếp theo cổng kết nối (`selected_port` khớp `edge.source_port`).
   - Bổ sung `output.no_answer` và `output.artifact` vào danh sách điều kiện kết thúc luồng.
9. [`backend/tests/test_workflows.py`](../../backend/tests/test_workflows.py):
   - Bổ sung 2 tests mới: `test_all_5_official_workflows_load_without_fallback` và `test_citation_guard_branches_grounded_vs_ungrounded`.
10. [`frontend/src/pages/dag-canvas-page.tsx`](../../frontend/src/pages/dag-canvas-page.tsx) & [`frontend/src/components/admin/in-canvas-test-runner.tsx`](../../frontend/src/components/admin/in-canvas-test-runner.tsx):
    - Chuẩn hóa Node IDs (`chat_output`, `knowledge_answer`, `citation_guard`), trực quan hóa node `no_answer_output` trên sơ đồ, đồng bộ sequential animation.

## 3. Kết Quả Kiểm Thử (Verification)
- **Backend Linter**: `uv run ruff check .` $\rightarrow$ 0 error (All checks passed!).
- **Backend Tests**: `uv run --extra dev pytest` $\rightarrow$ **117/117 passed (100%)** trong 40.87s.
- **Frontend Typecheck**: `npm run typecheck` $\rightarrow$ 0 error (`tsc --noEmit`).
- **Frontend Linter**: Biome check 0 error trên các tệp đã sửa.
- **Frontend Build**: `npm run build` $\rightarrow$ Đóng gói thành công trong 5.76s.
