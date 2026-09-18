# NHẬT KÝ LÀM VIỆC: TRIỂN KHAI ĐỢT 1 — PUBLISH GATE & KNOWLEDGE GAP INBOX

- **Thời gian**: 2026-09-18 22:30 (UTC+7)
- **Kỹ sư / Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu phiên**: Hiện thực hóa trọn vẹn Đợt 1 nâng cấp QNU AI Platform thành Nền tảng quản trị, tạo lập, kiểm định và vận hành Trợ lý AI chuyên trách cho ĐH Quy Nhơn theo kế hoạch đã phê duyệt:
  1. **Cổng Kiểm Định Xuất Bản 5 Lớp (Publish Gate Engine)**: Ngăn chặn trợ lý chưa sẵn sàng kích hoạt phục vụ rộng rãi.
  2. **Nhân Bản Trợ Lý 1-Click (Clone Assistant)**: Cho phép các khoa/phòng ban nhân bản từ trợ lý mẫu để tùy biến.
  3. **Hòm Thư Lỗ Hổng Tri Thức (Knowledge Gap Inbox & Active Remediation)**: Tự động gom câu hỏi kích hoạt No-Answer Policy, phục vụ vòng lặp học chủ động (Active Learning).

---

## 1. Chi Tiết Thay Đổi Kỹ Thuật

### Backend (FastAPI + SQLAlchemy + Pydantic v2)
| Tệp | Hành động | Lý do & Mô tả |
| :--- | :--- | :--- |
| [`backend/app/modules/assistants/readiness.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/readiness.py) | Tạo mới | Engine đánh giá 5 tiêu chí: Kho tri thức (có doc ready), ModelOps (dự phòng 2 tầng), Chốt chặn công cụ (Tool registry allowlist), Guardrails (chống jailbreak, che PII, hotline No-Answer), TM-08 (kiểm định chất lượng). Tính điểm sẵn sàng % và lọc blockers vs warnings. |
| [`backend/app/modules/assistants/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/schemas.py) | Chỉnh sửa | Bổ sung `ReadinessCheckItem`, `AssistantReadinessResponse`, `AssistantCloneRequest`, `AssistantPublishResponse`. |
| [`backend/app/modules/assistants/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/service.py) | Chỉnh sửa | - Hook tự động ghi nhận câu hỏi vào `knowledge_gaps` trong cả `chat()` và `chat_stream()` khi `status == "insufficient_context"`.<br>- Bổ sung methods `get_readiness`, `publish_assistant` (chặn xuất bản nếu có blocker), `clone_assistant`. |
| [`backend/app/modules/assistants/router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/router.py) | Chỉnh sửa | Khai báo 3 endpoints mới: `GET /{ref}/readiness`, `POST /{ref}/publish`, `POST /{ref}/clone`. |
| [`backend/app/modules/evaluation/models.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/evaluation/models.py) | Chỉnh sửa | Khởi tạo bảng SQLAlchemy `KnowledgeGapRecord` với các trường `assistant_code`, `collection_id`, `question`, `frequency`, `status`, `resolution_notes`, `resolved_by`. |
| [`backend/app/modules/evaluation/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/evaluation/schemas.py) | Chỉnh sửa | Thêm DTOs `KnowledgeGapResponse`, `KnowledgeGapResolveRequest`. |
| [`backend/app/modules/evaluation/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/evaluation/service.py) | Chỉnh sửa | Thêm các hàm `record_gap` (tự động cộng dồn `frequency` nếu câu hỏi lặp lại), `get_gap_inbox`, `resolve_gap`. |
| [`backend/app/modules/evaluation/router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/evaluation/router.py) | Chỉnh sửa | Thêm query params cho `GET /gap-inbox` và endpoint `PATCH /gap-inbox/{gap_id}`. |
| [`backend/tests/test_assistant_readiness.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_assistant_readiness.py) | Tạo mới | Unit test suite 6 ca: readiness checklist 5 tiêu chí, blocker phát hiện, chặn xuất bản với mã lỗi 422, nhân bản trợ lý hợp lệ, từ chối mã trùng lặp, test API endpoint. |
| [`backend/tests/test_knowledge_gaps.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_knowledge_gaps.py) | Tạo mới | Unit test suite 5 ca: tạo mới bản ghi gap, cộng dồn frequency khi hỏi lặp lại, bỏ qua câu hỏi rác (< 5 ký tự), resolve gap kèm ghi chú, test GET & PATCH API endpoint. |

### Frontend (React 19 + TypeScript + TanStack Query)
| Tệp | Hành động | Lý do & Mô tả |
| :--- | :--- | :--- |
| [`frontend/src/types/assistants.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/types/assistants.ts) | Chỉnh sửa | Định nghĩa TypeScript types cho Readiness, Clone, Publish DTOs. |
| [`frontend/src/types/evaluation.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/types/evaluation.ts) | Chỉnh sửa | Nâng cấp `GapInboxItem` (`collection_id`, `resolution_notes`, `resolved_by`) và `KnowledgeGapResolveRequest`. |
| [`frontend/src/services/assistants-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/assistants-api.ts) | Chỉnh sửa | Thêm `getAssistantReadiness`, `publishAssistant`, `cloneAssistant`. |
| [`frontend/src/services/evaluation-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/evaluation-api.ts) | Chỉnh sửa | Bổ sung query params cho `getGapInbox` và hàm gọi API `resolveGap`. |
| [`frontend/src/pages/assistant-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/assistant-detail-page.tsx) | Chỉnh sửa | - Bổ sung nút **[Nhân bản]** trên top toolbar mở Dialog sao chép cấu hình.<br>- Thêm Card **"Cổng Kiểm Định Xuất Bản (Publish Gate)"** với thanh tiến trình điểm sẵn sàng %, 5 dòng tiêu chí (Kho tri thức, Model, Tools, Guardrails, TM-08) kèm icon Pass/Fail/Warn, nút Kiểm tra lại và Xuất bản chính thức. |
| [`frontend/src/pages/evaluation-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/evaluation-page.tsx) | Chỉnh sửa | - Cập nhật badge số lượng câu hỏi cần xử lý trên Tab.<br>- Nút **[Nạp vào RAG]** dẫn sang `/knowledge`.<br>- Nút **[Đánh dấu đã nạp]** và **[Bỏ qua]** gọi trực tiếp `resolveGapMutation` kèm Sonner toast. |

---

## 2. Đồng Bộ Quy Trình Vận Hành (`docs/quy_trinh/`)

- Đồng bộ tệp [`docs/quy_trinh/07_kiem_dinh_chat_luong_tm08.md`](../quy_trinh/07_kiem_dinh_chat_luong_tm08.md): Bổ sung Mục 4 đặc tả **Hòm Thư Lỗ Hổng Tri Thức (Knowledge Gap Inbox) & Vòng Lặp Học Chủ Động (Active Remediation)** kèm sơ đồ Mermaid chi tiết về luồng tự động ghi nhận câu hỏi khi No-Answer Policy kích hoạt và quy trình xử lý của chuyên viên.

---

## 3. Kết Quả Kiểm Thử Toàn Diện (Verification)

1. **Bộ Kiểm Thử Backend Pytest**:
   - Chạy riêng 2 test suites mới: **11/11 passed (100%)**.
   - Chạy toàn bộ test suite hệ thống: **193/193 passed (100%)**, 0 lỗi.
2. **Kiểm Tra Cú Pháp & Linter Backend**:
   - `uv run ruff check .`: **0 lỗi (All checks passed!)**.
3. **Kiểm Tra Frontend Biome Linter**:
   - `npm run lint`: **124/124 files checked, 0 lỗi, 0 cảnh báo**.
4. **Kiểm Tra Kiểu Dữ Liệu TypeScript**:
   - `npm run typecheck`: **0 lỗi (tsc --noEmit passed)**.
5. **Kiểm Tra Đóng Gói Bundle Vite**:
   - `npm run build`: **Thành công trong 7.74 giây**, bundle sinh ra hoàn chỉnh.
6. **Kiểm Toán Zero Mojibake**:
   - `python scripts/check_mojibake.py`: **272/272 files sạch, 0 lỗi Mojibake/vỡ font**.

---

## 4. Trạng Thái Hoàn Thành Đợt 1

- ✅ Publish Gate 5 Lớp hoàn chỉnh cả Backend + Frontend.
- ✅ Nhân Bản Trợ Lý 1-Click hoàn chỉnh.
- ✅ Knowledge Gap Inbox & Active Learning khép kín luồng từ Chat ➔ DB ➔ UI ➔ Knowledge upload ➔ Resolve.
- Sẵn sàng chuyển sang Đợt 2 theo kế hoạch.
