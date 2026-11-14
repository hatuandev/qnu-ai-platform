# Phiên 960 — Trang Chat V2 nối API hội thoại thật

## 1. Yêu cầu và phạm vi

- Tiếp lộ trình sau phiên 959: thay trang **Chat V2** (`frontendV2/src/routes/chat.tsx`) từ mock tĩnh bằng luồng hội thoại thật (tạo hội thoại, gửi lượt hỏi, hiển thị kết quả/lỗi, chuyển hội thoại).
- Không đổi backend: dùng đúng hợp đồng conversations hiện có (tạo hội thoại, danh sách lọc `assistant_id`, gửi lượt với `Idempotency-Key` và `expected_turn_no`, danh sách lượt tăng dần).
- Giữ nguyên: diff chưa commit của người dùng ngoài phạm vi; dev DB `0026` (0027+0028 chờ duyệt); không commit/push/deploy; không re-index; không chạy pytest (người dùng yêu cầu dừng test); không in token/secret.
- Ràng buộc UI: tái dùng primitive/helper hiện có, semantic token, Lucide, không mock/fake submit, lỗi/trống trung thực.

## 2. Hợp đồng sau thay đổi

1. **Chọn trợ lý và hội thoại:** trang Chat lấy danh sách trợ lý thật; mặc định chọn trợ lý đang hoạt động đầu tiên. Danh sách hội thoại lấy 20 mục mới nhất của trợ lý; mục đầu được chọn sẵn.
2. **Chế độ "Hội thoại mới":** không tạo hội thoại rỗng. Hội thoại chỉ được tạo ở lần gửi đầu tiên, tiêu đề lấy từ câu hỏi (tối đa 160 ký tự). Sau khi tạo, danh sách hội thoại được cập nhật ngay trong cache để selector hiển thị mục mới.
3. **Gửi lượt:** mỗi lượt dùng `Idempotency-Key` sinh riêng; `expected_turn_no` ưu tiên số lượt cục bộ vừa gửi thành công (tránh dùng `last_turn_no` cũ trong lúc danh sách chưa refetch). Lượt gửi đồng bộ nên có bong bóng "đang xử lý" trong lúc chờ (1–3 phút).
4. **Hiển thị kết quả:** lượt trả lời trực tiếp hiện badge tuyến (`Chào hỏi`, `Xã giao`, `Giới thiệu`, `Yêu cầu cần bảo vệ`); lượt RAG dùng chung `AnswerBody`; lượt lỗi hiện diễn giải tiếng Việt kèm mã gốc dạng mono.
5. **Lỗi khi gửi:** API có thể trả lượt `failed` xen lẫn ném lỗi HTTP. UI xử lý cả hai: lượt `failed`/`uncertain` hiện toast tương ứng; lỗi ném ra được ánh xạ riêng cho `conversation_sequence_conflict`, `conversation_busy`, `idempotency_conflict`, `request_aborted`, sau đó tới bảng mã lỗi lượt hỏi.
6. **Trạng thái trung thực:** cảnh báo trợ lý tạm dừng, kho chưa có tài liệu xuất bản (kèm link mở kho), chỉ mục chưa sẵn sàng, lỗi tải hội thoại/lượt hỏi có nút thử lại; trống thì hiện WelcomePanel với gợi ý bắt đầu nhanh.

## 3. Thay đổi

- `frontendV2/src/routes/chat.tsx`: viết lại toàn bộ — bỏ mock (trích dẫn giả, hộp chia sẻ/QR/widget, nút phản hồi, câu hỏi mẫu tuyển sinh), nối API thật; thêm `DRAFT_VALUE`, `WelcomePanel`, `TurnRow`, `PendingRow`, `UserBubble`, `AssistantAvatar`, `turnAnswerText`; auto-scroll có guard; copy câu trả lời.
- `frontendV2/src/api/conversations/queries.ts`: mutation tạo hội thoại chèn hội thoại mới vào đầu cache danh sách (giữ cache cũ nếu có), rồi vẫn invalidate danh sách.
- `frontendV2/src/components/assistants/turn-result.tsx`: component hiển thị kết quả lượt hỏi dùng chung, export kèm `TURN_ERROR_TEXT` (9 mã lỗi).
- `frontendV2/src/components/assistants/assistant-logs.tsx`: dùng lại `TurnResult` thay vì bản sao cục bộ.

## 4. Kiểm chứng đã chạy

### 4.1 Tĩnh

- Biome check trên `routes/chat.tsx`, `api/conversations/queries.ts`, `components/assistants/turn-result.tsx`, `components/assistants/assistant-logs.tsx`: **PASS** ("No fixes applied").
- `npx tsc --noEmit` trong `frontendV2`: **exit 0**.

### 4.2 Live UI (Vite 3002, workspace `ws_f617405c3a51`, trợ lý `ast_3f577d75f723`)

Trình duyệt trong app báo `visibilityState=hidden` — `take_screenshot` không khả dụng và click của công cụ không được gửi tới trang; các thao tác được thực hiện bằng sự kiện DOM thật (native setter + `input`, `PointerEvent`/`KeyboardEvent`), đọc trạng thái bằng snapshot cấu trúc.

- Bấm "Hội thoại mới": selector chuyển "Hội thoại mới", hiện WelcomePanel với 3 gợi ý ("Xin chào", "Bạn là trợ lý gì?", "Bạn có thể giúp gì?") và ghi chú kho trống: **PASS**.
- Bấm gợi ý "Xin chào": tạo hội thoại mới tiêu đề "Xin chào", lượt 1 **completed `direct_reply`** route `greeting`; selector cập nhật ngay mục mới: **PASS**.
- Gửi tiếp "Bạn là trợ lý gì?" bằng composer: lượt 2 **completed `direct_reply`** route `identity`, không xảy ra `conversation_sequence_conflict` — xác nhận theo dõi `expected_turn_no`: **PASS**.
- Gửi câu tra cứu "Quy định về học phí năm 2026?": lượt 3 **failed `index_not_ready`**; UI hiện "Kho tri thức chưa có chỉ mục đang hoạt động nên chưa thể trả lời." + mã mono; toast hiện diễn giải + "Lượt hỏi đã được ghi nhận trong hội thoại.": **PASS**.
- Bấm Tải lại: 3 lượt tải lại từ máy chủ, giữ đúng thứ tự 1→2→3: **PASS**.
- Chuyển selector sang "Kiểm thử nhật ký P3": danh sách lượt đổi sang 2 lượt cũ (failed `index_not_ready` + greeting): **PASS**.

### 4.3 NOT RUN / NOT OBSERVED

- **Pytest: NOT RUN** theo yêu cầu dừng test — `NOT RUN ≠ PASS`.
- **NOT OBSERVED:** nhánh câu trả lời RAG `answered` có trích dẫn (kho demo trống), poll lượt `running` (lượt chạy/fail quá nhanh), toast `conversation_busy`/`sequence_conflict` (không dựng tình huống tranh chấp), sao chép thật vào clipboard (trình duyệt ẩn, không xác nhận quyền clipboard), viewport mobile và ảnh chụp.
- Không chạy migration, không re-index, không đổi backend.

## 5. Rủi ro và việc còn lại

- Dữ liệu dev phát sinh trong kiểm thử: hội thoại mới tiêu đề **"Xin chào"** (3 lượt: 2 trả lời trực tiếp + 1 failed `index_not_ready`) bên cạnh `cnv_408c176b53a9` ("Kiểm thử nhật ký P3", 2 lượt) — **chưa xóa**, chờ người dùng quyết định.
- Chat dùng gửi lượt đồng bộ (không streaming); khi kho có tài liệu thật cần đo lại thời gian chờ và hiển thị tiến trình nếu vượt ngưỡng.
- Dev DB vẫn `0026`; migration `0027_drop_ws_model_policy` + `0028` tiếp tục chờ duyệt (#223).
- Bước tiếp theo của lộ trình: **SSO cho `frontendV2`** trước khi thay website trên server.
- Chưa commit/push; working tree còn diff knowledge/lifecycle và nhóm tệp trợ lý/Chat của phiên 959–960.
