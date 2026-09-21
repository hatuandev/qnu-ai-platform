# NHẬT KÝ LÀM VIỆC — Phiên #192
**Ngày thực hiện**: 2026-09-22 (UTC+7)  
**Tiêu đề**: Bổ Sung Nút Tải Nội Dung Cuộc Trò Chuyện Dạng Tệp Markdown (.md) & Loại Bỏ Fallback Bắt Nhầm Đại Từ Nghi Vấn "Nào"  
**Chuyên gia phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist

---

## 1. Bối Cảnh & Mục Tiêu

1. **Yêu cầu người dùng**: Bổ sung nút tải toàn bộ nội dung cuộc trò chuyện ở định dạng tệp Markdown (`.md`) trực tiếp từ giao diện chat để phục vụ công tác review, kiểm tra chất lượng tư vấn và lưu trữ văn bản.
2. **Phát hiện từ phiên kiểm thử thực tế**:
   - Ở Lượt 3: Câu hỏi *"Phương thức xét tuyển học bạ của trường áp dụng cho những ngành nào?"* bị gán ghép chỉ trả lời cho ngành CNTT.
   - Nguyên nhân: Trong [`service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/service.py) tồn tại một đoạn regex fallback cũ bắt nhầm từ đại từ nghi vấn `"nào"` thành tên thực thể (`target_entity = "Nào"`), ép prompt LLM chỉ được phép trích xuất cho thực thể này.
   - Xử lý triệt để: Gỡ bỏ hoàn toàn đoạn fallback thừa (tuân thủ Boy Scout Rule), sử dụng trực tiếp `analysis.target_entities` đã được kiểm soát bởi bộ lọc đại từ nghi vấn.

---

## 2. Chi Tiết Các Thay Đổi Kỹ Thuật

### 2.1. Frontend — Tính Năng Tải Cuộc Trò Chuyện (.md)
1. **Mô-đun Tiện Ích Mới [`frontend/src/lib/export-markdown.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/lib/export-markdown.ts)**:
   - `formatConversationToMarkdown`: Định dạng toàn bộ tin nhắn thành cấu trúc Markdown chuẩn bao gồm:
     - Header: Tiêu đề cuộc trò chuyện, tên trợ lý, mã trợ lý, mô tả, thời gian xuất, tổng số tin nhắn.
     - Nội dung từng lượt: Phân biệt rõ Người dùng (`👤`) và Trợ lý (`🎓`), đính kèm thời gian từng tin nhắn.
     - Trích dẫn minh chứng: Tên tài liệu, số trang, đoạn trích dẫn gốc (blockquote).
     - Gợi ý câu hỏi tiếp theo (`💡`).
     - Tệp đính kèm (`📎`) kèm dung lượng KB nếu có.
     - Chân trang ghi rõ nguồn gốc từ QNU AI Platform.
   - `downloadMarkdownFile`: Kích hoạt tải tệp trực tiếp trên trình duyệt qua Blob `text/markdown;charset=utf-8` và link ẩn.
2. **Giao Diện Chat Studio [`frontend/src/pages/chat-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/chat-studio-page.tsx)**:
   - Bổ sung nút bấm **Tải về (.md)** kèm icon `Download` (`lucide-react`) cạnh nút **Làm mới** trên thanh công cụ của Chat Studio.
   - Trạng thái `disabled` mượt mà khi chưa có tin nhắn nào trong phiên hội thoại.
   - Thông báo Toast hiển thị tên tệp tải về thành công.
3. **Giao Diện Quản Trị Hội Thoại [`frontend/src/pages/conversations-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/conversations-page.tsx)**:
   - Bổ sung nút **Xuất MD** trên thanh công cụ chi tiết hội thoại của cán bộ hỗ trợ để thuận tiện xuất lịch sử trao đổi của sinh viên sang Markdown khi cần đối soát.

### 2.2. Backend — Loại Bỏ Fallback Bắt Nhầm Thực Thể "Nào"
1. **[`backend/app/modules/rag/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/service.py)**:
   - Xóa bỏ đoạn regex fallback bắt nhầm `"ngành nào"` thành thực thể `"Nào"`.
   - Sử dụng trực tiếp `target_entity_str = ", ".join(analysis.target_entities) if analysis.target_entities else None`.
2. **[`backend/tests/test_rag_entity_scoped_formatting.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_rag_entity_scoped_formatting.py)**:
   - Bổ sung unit test `test_interrogative_pronoun_nganh_nao_has_no_target_entities` xác nhận cụm từ `"áp dụng cho những ngành nào"` không bị bắt nhầm thực thể.
   - Bổ sung mock `semantic_cache.get` ngăn chặn cache hit trong test suite RAG.

---

## 3. Kết Quả Kiểm Thử Toàn Bộ Hệ Thống

- **Backend Pytest**: **`394/394 passed (100%)`**
- **Backend Ruff**: **`0 lỗi`** (`All checks passed!`)
- **Frontend Biome**: **`170 files checked, 0 lỗi`**
- **Frontend TypeScript**: **`0 lỗi`** (`tsc --noEmit` hoàn hảo)
- **Frontend Vite Build**: **`Thành công`** trong 8.37 giây (`dist/` tối ưu production)
