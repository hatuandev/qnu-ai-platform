# NHẬT KÝ LÀM VIỆC: HOÀN THÀNH GIAI ĐOẠN 4 FRONTEND (BỘ TIỆN ÍCH CHUYÊN TRÁCH AI SUITE)
- **Thời gian**: 2026-09-15 20:28
- **Kỹ sư / Agent**: AI Senior Backend Architect & Enterprise Specialist
- **Mục tiêu phiên**: Xây dựng toàn bộ các linh kiện chuyên biệt phục vụ Trí tuệ Nhân tạo (**AI Suite Components**) theo chuẩn thiết kế QLKTX ĐH Quy Nhơn, giải quyết triệt để các bài toán đặc thù của Nền tảng AI: truyền phát token thời gian thực (**SSE Token Streaming**), cuộn ghim đáy thông minh (**`MessageScroller`**), tra cứu dẫn chứng văn bản gốc chống ảo giác (**`CitationSheet`**), thẻ trắc nghiệm chuẩn Bloom (**`QuestionnaireCard`**), thẻ đính kèm tệp (**`Attachment`**), và đồ thị trực quan hóa quy trình điều phối (**`DAGCanvas`** trên nền **`@xyflow/react` v12**).

---

## 1. Tóm Tắt Các Thay Đổi Kỹ Thuật

| Cấu Phần | Tệp Tin Mã Nguồn | Đặc Tả Kỹ Thuật & Nghiệp Vụ |
| :--- | :--- | :--- |
| **Hook SSE Streaming** | [`frontend/src/hooks/use-rag-stream.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/hooks/use-rag-stream.ts) | Quản lý vòng đời hội thoại: gửi câu hỏi qua SSE stream (`/platform/v1alpha1/assistants/{code}/chat`), bóc tách token từng phần bằng `eventsource-parser`, quản lý `activeCitation`, hỗ trợ `stopStreaming()` qua `AbortController`, và tích hợp cơ chế dự phòng thông minh (Offline Mock Fallback) chuẩn xác cho 05 Trợ lý QNU khi backend chưa sẵn sàng. |
| **Bong Bóng Tin Nhắn** | [`frontend/src/components/ai/chat-bubble.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ai/chat-bubble.tsx) | Render Markdown chuẩn mực (`react-markdown` + `remark-gfm`), định kiểu bảng biểu sắc nét, khối mã code nền tối nhẹ, danh sách có thứ tự, và hiệu ứng đang tư duy (*Thinking Dots / Pulsing Indicator*). Đổi tên thuộc tính `senderRole` để triệt tiêu hoàn toàn xung đột ARIA roles. |
| **Khung Tin Nhắn Đầy Đủ** | [`frontend/src/components/ai/chat-message.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ai/chat-message.tsx) | Hiển thị tin nhắn người dùng và Trợ lý AI; tích hợp Avatar chuyên trách từng Trợ lý (Tuyển sinh, Quy chế, Thư viện, Soạn thảo, Đề thi), độ trễ phản hồi tính bằng mili-giây, nút sao chép, tạo lại câu trả lời, đánh giá Thumbs Up/Down, các nhãn dẫn chứng (**Citation Badges**), và gợi ý câu hỏi liên quan tiếp theo. |
| **Cuộn Đáy Thông Minh** | [`frontend/src/components/ai/message-scroller.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ai/message-scroller.tsx) | Tự động ghim cuộn xuống đáy khi token đang truyền phát thông qua `MutationObserver`; phát hiện người dùng lăn chuột lên trên để đọc tài liệu cũ và tự động tạm dừng cuộn; hiển thị nút nổi "Xuống tin mới nhất" kèm chấm phát sáng thông báo khi có tin nhắn mới. |
| **Ngăn Kéo Dẫn Chứng** | [`frontend/src/components/ai/citation-sheet.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ai/citation-sheet.tsx) | Drawer trượt từ mép phải (`Sheet`) hiển thị trọn vẹn thông tin minh chứng đối chiếu: Tên tệp văn bản gốc, Điều/Khoản, số trang, điểm số tương đồng RRF k=60, đoạn trích dẫn đối chiếu (Grounding Excerpt), và cam kết chính sách chống ảo giác (Zero-Hallucination Policy). |
| **Thẻ Đính Kèm Tệp** | [`frontend/src/components/ai/attachment.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ai/attachment.tsx) | Thẻ hiển thị tệp tài liệu trong khung chat (PDF, Word, Excel, Hình ảnh), định dạng dung lượng byte, nút gỡ bỏ, và huy hiệu trạng thái OCR đa tầng (Chờ bóc tách, Đang OCR, Hoàn thành). |
| **Thẻ Trắc Nghiệm Bloom** | [`frontend/src/components/ai/questionnaire-card.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ai/questionnaire-card.tsx) | Thẻ câu hỏi trắc nghiệm 4 lựa chọn (A, B, C, D) theo 4 mức độ nhận thức Bloom (Nhận biết, Thông hiểu, Vận dụng, Vận dụng cao); phản hồi đúng/sai tức thì, bung accordion giải thích chi tiết đáp án kèm mã Chuẩn đầu ra (CLO) và trích dẫn giáo trình môn học. |
| **Sơ Đồ Visual DAG Canvas** | [`frontend/src/components/ai/dag-canvas.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ai/dag-canvas.tsx) | Trực quan hóa đồ thị luồng điều phối trên nền **`@xyflow/react` v12** với 5 Custom Nodes đồng bộ màu sắc OKLCH (`ChatInputNode`, `ConditionRouteNode`, `RAGKnowledgeNode`, `GuardrailNode`, `ChatOutputNode`), MiniMap, Controls, và Panels thông số. |
| **Màn Hình Chat Studio** | [`frontend/src/pages/chat-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/chat-studio-page.tsx) | Màn hình tương tác hội thoại toàn năng kết hợp đầy đủ 05 Trợ lý, thanh công cụ đính kèm file, gợi ý câu hỏi mẫu, thẻ trắc nghiệm Bloom thử nghiệm, và ngăn kéo tra cứu dẫn chứng. |
| **Màn Hình Visual DAG** | [`frontend/src/pages/dag-canvas-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/dag-canvas-page.tsx) | Không gian khám phá sơ đồ quy trình điều phối AI cho toàn bộ 05 Trợ lý; tích hợp bảng điều khiển chi tiết Node (Inspector Panel) hiển thị ID, cấu hình schema, và chính sách thực thi (Timeout, Max attempts, Circuit Breaker). |
| **Tích Hợp Khung Vỏ** | [`frontend/src/App.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/App.tsx) | Gắn kết các tuyến đường `/chat` (Chat Studio) và `/nodes` (Visual DAG Studio) vào `AdminShell`; bổ sung nút xem sơ đồ DAG và trò chuyện trên từng thẻ Trợ lý. |

---

## 2. Kết Quả Kiểm Thử & Nghiệm Thu (Verification)

### 2.1. Frontend Checks
* **Biome Linter & Formatter**:
  ```powershell
  npm run lint
  # Checked 48 files in 37ms. No fixes applied. (0 errors, 0 warnings)
  ```
* **TypeScript Strict Typecheck**:
  ```powershell
  npm run typecheck
  # tsc --noEmit -> 0 errors (100% pass)
  ```
* **Vite Production Build**:
  ```powershell
  npm run build
  # ✓ 2418 modules transformed.
  # dist/index.html                   1.48 kB │ gzip:   0.81 kB
  # dist/assets/index-CewllxI-.css   72.25 kB │ gzip:  12.26 kB
  # dist/assets/index-BoEcrnZy.js   881.62 kB │ gzip: 272.00 kB
  # ✓ built in 7.56s
  ```

### 2.2. Backend Regression Checks
* **Ruff Linter**: `uv run ruff check .` $\rightarrow$ `All checks passed!` (0 errors).
* **Pytest Suite**: `uv run --extra dev pytest` $\rightarrow$ `68 passed, 3 warnings in 4.26s` (100% pass).

---

## 3. Trạng Thái Hoàn Thành
- **Giai đoạn 4**: **HOÀN THÀNH 100% (PASSED)**.
- **Bước tiếp theo**: Sẵn sàng triển khai **Giai đoạn 5: Tích Hợp API Thực Tế & Bộ Định Tuyến Hoàn Chỉnh (TanStack Suite, REST & SSE Integration, FinOps Dashboard)** theo kế hoạch phát triển Frontend.
