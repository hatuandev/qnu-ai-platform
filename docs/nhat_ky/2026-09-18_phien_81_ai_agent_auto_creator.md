# Nhật Ký Phát Triển — Phiên #81 (2026-09-18)
## Triển Khai Tính Năng AI Agent Auto-Creator (Tự Sinh Agent Trọn Gói) & Nút Viết Hộ Prompt Chuẩn QNU

---

### 1. Bối Cảnh & Mục Tiêu

Trước đây, khi cán bộ muốn tạo một Trợ lý AI mới hoặc cấu hình chỉ thị hệ thống (System Prompt), cán bộ phải tự soạn thảo văn bản từ đầu hoặc chọn một trong các mẫu cố định có sẵn. Điều này gây khó khăn khi cán bộ chỉ có một ý tưởng nghiệp vụ ngắn gọn (ví dụ: *"Trợ lý Ký túc xá cho tân sinh viên"* hay *"Trợ lý giải đáp học phí & học bổng"*).

Mục tiêu phiên #81:
1. **Backend**: Cung cấp endpoint `POST /platform/v1alpha1/assistants/generate` nhận vào ý tưởng và phân loại gợi ý, sử dụng LLM qua ModelOps để phân tích và sinh ra một bộ đặc tả Trợ lý hoàn chỉnh (Tên chuẩn QNU, Mô tả, Lĩnh vực, System Prompt 5 phần chống hallucination, Câu hỏi mẫu thực tế, Nhiệt độ và Hotline cứu cánh). Cung cấp cơ chế fallback tiếng Việt phong phú để hoạt động ổn định kể cả khi offline.
2. **Frontend Tạo Mới (`/assistants/new`)**: Tích hợp Card **"AI Tự Sinh Agent Trọn Gói (AI Agent Auto-Creator)"** với ô nhập ý tưởng, nút **[✨ Tự Sinh Agent]**, các chip gợi ý nhanh, tự động điền toàn bộ form (kèm tự sinh mã slug không dấu); đồng thời thêm nút **[✨ Viết hộ tôi]** ngay trên ô System Prompt.
3. **Frontend Chi Tiết (`/assistants/:id`)**: Bổ sung nút **[✨ Viết hộ tôi]** ngay trên ô System Prompt giúp cán bộ tối ưu hoặc soạn lại prompt bất kỳ lúc nào dựa trên tên và mô tả hiện thời.

---

### 2. Chi Tiết Thay Đổi Kỹ Thuật

#### Backend:
- `backend/app/modules/assistants/schemas.py`:
  - Thêm schema `AssistantGenerateRequest(idea, category_hint, target_audience)`.
  - Thêm schema `AssistantGenerateResponse(name, description, category, system_prompt, sample_questions, temperature, no_answer_message, suggested_workflow_id)`.
- `backend/app/modules/assistants/service.py`:
  - Hàm `generate_spec(db, request)`: Gọi `modelops_service.generate` với prompt phân tích chuyên gia AI QNU; bóc tách JSON bằng `_extract_json`.
  - Hàm `_build_fallback_spec(idea, category_hint)`: Nhận diện theo từ khóa tiếng Việt (Tuyển sinh, Soạn thảo NĐ 30, Khảo thí Bloom, Thư viện, Ký túc xá) và cấu trúc sẵn system prompt 5 phần chuẩn QNU kèm số liệu Hotline 0256.3846.156.
- `backend/app/modules/assistants/router.py`:
  - Thêm endpoint `POST /generate` mapping tới `assistant_service.generate_spec`.
- `backend/tests/test_assistants.py`:
  - Thêm test case `test_api_generate_assistant_spec` kiểm thử trọn vẹn phản hồi API.

#### Frontend:
- `frontend/src/services/assistants-api.ts`:
  - Định nghĩa interface `AssistantGeneratedSpec` và hàm gọi API `generateAssistantSpec(idea, categoryHint)`.
- `frontend/src/pages/assistant-create-page.tsx`:
  - Thêm Card **AI Tự Sinh Agent Trọn Gói** với `ideaInput`, nút **[✨ Tự Sinh Agent]**, và 4 quick idea chips (`🏠 Ký túc xá & Nội trú`, `🎓 Học bổng & Học phí`, `📚 Thư viện & Giáo trình`, `📑 Soạn thảo NĐ 30`).
  - Hàm `slugify` chuẩn Unicode `\p{M}/gu` tự động tạo mã định danh trợ lý.
  - Thêm nút **[✨ Viết hộ tôi]** phía trên ô textarea của System Prompt.
- `frontend/src/pages/assistant-detail-page.tsx`:
  - Tích hợp nút **[✨ Viết hộ tôi]** phía trên ô System Prompt (Chỉ thị hệ thống) gọi `generateAssistantSpec` từ thông tin hiện có của trợ lý.

---

### 3. Kết Quả Kiểm Thử Toàn Diện

- **Backend Pytest**: `uv run --extra dev pytest tests/test_assistants.py -v` — 9/9 passed (100%).
- **Backend Ruff**: `uv run ruff check .` — 0 lỗi.
- **Frontend Biome**: `npm run lint` — Checked 93 files in 128ms, 0 lỗi.
- **Frontend Typecheck**: `npm run typecheck` — `tsc --noEmit` 0 lỗi.
- **Frontend Build**: `npm run build` — Vite build thành công trong 7.92s.
- **Zero Mojibake Audit**: `python scripts/check_mojibake.py` — 227/227 files sạch 100%.
- **Browser Subagent E2E**: Đã xác thực giao diện và luồng hoạt động thực tế trên trình duyệt:
  - Video quay lại toàn bộ phiên: `assistant_auto_creator_demo_1789700749600.webp`
  - Ảnh chụp màn hình: `ai_creator_card_1789700810739.png`, `auto_generated_form_1789700885074.png`, `sample_questions_step_1789700912426.png`, `detail_page_auto_writer_1789700966084.png`, `detail_page_prompt_writer_1789700991983.png`.
