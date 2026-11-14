# Phiên 961 — Thiết kế lại trang chi tiết trợ lý 5 tab theo mockup

## 1. Yêu cầu và phạm vi

- Người dùng gửi 6 ảnh mockup và phản hồi trang chi tiết trợ lý hiện tại (3 tab) "nhìn nó đơn giản quá", yêu cầu thiết kế lại đúng giao diện đã đề xuất: **5 tab Tổng quan · Cấu hình · Hỏi thử · Kiểm thử câu trả lời · Nhật ký**, bố cục thẻ, hero header và thanh lưu cố định.
- Chỉ sửa frontend V2; không đổi backend, không đổi hợp đồng API, không migration, không re-index.
- Giữ nguyên: diff chưa commit của người dùng ngoài phạm vi; dev DB `0026` (0027+0028 chờ duyệt); không commit/push/deploy; không chạy pytest (người dùng yêu cầu dừng test); không in token/secret.
- Ràng buộc UI: tái dùng primitive/helper hiện có, semantic token, Lucide, không mock/fake submit, lỗi/trống trung thực, dữ liệu thật từ readiness/hội thoại/kiểm thử.

## 2. Hợp đồng sau thay đổi

1. **5 tab URL-driven:** `?tab=overview|config|ask|reviews|logs`, mặc định `overview` (zod `.catch`). Tab Cấu hình dùng `forceMount` + `data-[state=inactive]:hidden` nên bản nháp cấu hình không mất khi chuyển tab trong trang.
2. **Hero header:** icon tile, tên trợ lý, badge sẵn sàng (`readinessHeroLabel` — "Sẵn sàng phục vụ" khi ready), badge "Tạm dừng", mô tả, dòng metadata `Kho tri thức · Cập nhật {ngày} · Phiên bản {n}`; thao tác chính "Hỏi thử" và menu `⋯` gồm "Tải lại trạng thái", "Chỉnh cấu hình", "Mở kho tri thức", "Xóa trợ lý" (xác nhận, xóa thật, điều hướng về danh sách).
3. **Tab Tổng quan:** thẻ "Trạng thái phục vụ" (badge + nút Làm mới + 4 chỉ số Tài liệu xuất bản/Đang phục vụ/Chỉ mục thế hệ/Kiểm tra lúc + cảnh báo `sync_error_code`), thẻ "Cấu hình đang áp dụng" (mô hình, kho, truy xuất, trích dẫn, kiểm chứng, phiên bản + link Chỉnh cấu hình), "Hội thoại gần đây" (5 mục mới nhất, link Nhật ký) và "Kiểm thử gần đây" (lượt kiểm thử mới nhất + trạng thái, link Kiểm thử).
4. **Tab Cấu hình:** form inline dạng thẻ — Thông tin cơ bản (tên/mô tả/persona kèm đếm ký tự theo giới hạn chung), Phạm vi tri thức & mô hình (kho bị khóa sau tạo; model có lựa chọn "Tự động theo hệ thống"), Hành vi trả lời (topK/lượt ghi nhớ/token ra + công tắc hoạt động), "Truy xuất nâng cao" dạng gập (retrieval/context/metadata scope), Kiểm chứng câu trả lời. Lưu dùng `expected_revision` theo baseline; có "Hoàn tác", dải trạng thái "Có thay đổi chưa lưu"/"Đã lưu · phiên bản N", cảnh báo cấu hình đã cũ khi người khác cập nhật, xử lý `assistant_revision_conflict` không mất bản nháp.
5. **Chọn kiểu segmented thay select:** `SegmentedChoice` (RadioGroup ẩn + Label dạng thẻ, hỗ trợ focus ring, disabled) cho cách tìm tri thức, phạm vi dữ kiện và chế độ kiểm chứng — khớp mockup và dễ đọc hơn select.
6. **Nguồn dữ liệu trung thực:** mọi số liệu lấy từ `AssistantReadiness`, catalog model, danh sách hội thoại và `answer_reviews` thật; trạng thái trống có hướng dẫn (kho chưa xuất bản → mở kho; chưa kiểm thử → chạy Hỏi thử).

## 3. Thay đổi

- `frontendV2/src/routes/assistants.$assistantId.tsx`: viết lại — search schema 5 tab, hero header, menu `⋯`, danh sách tab mới, nội dung từng tab; bỏ `AssistantFormDialog` khỏi trang (cấu hình chuyển vào tab), bỏ `PageHeader`/`useCatalogQuery`.
- `frontendV2/src/components/assistants/assistant-form-state.ts` (mới): nguồn duy nhất cho form — hằng giới hạn ký tự, `initialState`, `validateAssistantForm`, `buildAssistantPayload` dùng chung dialog và form inline.
- `frontendV2/src/components/assistants/assistant-advanced-fields.tsx`: thay bảng hint bằng `RETRIEVAL_OPTIONS`/`SCOPE_OPTIONS`/`VERIFICATION_OPTIONS`, thêm `SegmentedChoice`; tách và export `RetrievalFields`, `ContextFields`, `MetadataScopeFields`, `VerificationFields`, `ModelOption`; dialog lẫn form inline dùng lại.
- `frontendV2/src/components/assistants/assistant-config-form.tsx` (mới, ~520 dòng): form cấu hình inline 5 thẻ + thanh lưu sticky; baseline revision, dirty so sánh JSON, tự nhận cập nhật bên ngoài khi chưa bẩn, cảnh báo stale, lỗi/conflict trung thực.
- `frontendV2/src/components/assistants/assistant-overview.tsx` (mới, ~370 dòng): 4 thẻ tổng quan như mục 2.3.
- `frontendV2/src/components/assistants/readiness.ts`: thêm `readinessHeroLabel`.
- `frontendV2/src/components/assistants/assistant-form-dialog.tsx`: dùng `assistant-form-state` thay bản sao state/validate/payload; giữ hành vi revision-conflict cũ.
- `frontendV2/src/components/assistants/assistant-card.tsx`: link tiêu đề mặc định `tab=overview`.
- `frontendV2/src/components/assistants/ask-test-panel.tsx`: copy trỏ sang tab "Cấu hình" khi trợ lý tạm dừng.

## 4. Kiểm chứng đã chạy

### 4.1 Tĩnh

- `npx biome check` trên 16 tệp `components/assistants` + route: **PASS** ("No fixes applied"; 4 tệp được Biome sửa định dạng trước đó).
- `npx tsc --noEmit` trong `frontendV2`: **exit 0**, không diagnostics.

### 4.2 Live UI (Vite 3002, trợ lý `ast_3f577d75f723`, workspace `ws_f617405c3a51`)

Trình duyệt trong app báo `visibilityState=hidden` — `take_screenshot` không khả dụng; thao tác bằng sự kiện DOM thật (mousedown/click/native setter) và đọc trạng thái bằng truy vấn DOM.

- Mở `/assistants/ast_3f577d75f723`: URL `?tab=overview`, h1 "Trợ lý Kiểm thử P2", đủ 5 tab đúng thứ tự **PASS**.
- Tab Tổng quan: 4 thẻ Trạng thái phục vụ/Cấu hình đang áp dụng/Hội thoại gần đây/Kiểm thử gần đây; readiness "Chưa có nội dung — Kho chưa có tài liệu xuất bản", chỉ số 0/0/—/— **PASS** (trung thực với kho demo trống).
- Tab Cấu hình: 4 thẻ hiển thị, thanh lưu "Đã lưu · phiên bản 1", "Lưu thay đổi"/"Hoàn tác" disabled; đếm ký tự 18/160, 57/2000, 0/4000; kho bị khóa "Kho tri thức Demo"; model "Tự động theo hệ thống"; công tắc "Đang hoạt động" **PASS**.
- Sửa tên bằng native setter + `input`: chuyển "Có thay đổi chưa lưu · Đang dựa trên phiên bản 1 · Kiểm chứng: Tắt", hai nút bật **PASS**; bấm "Hoàn tác": tên trở lại, nút disabled **PASS**.
- Sửa tên rồi chuyển sang Tổng quan và quay lại Cấu hình: giá trị nháp "… (nháp tab)" còn nguyên, nút Lưu vẫn bật — xác nhận `forceMount` **PASS**.
- Tab Hỏi thử: empty state "Kho tri thức chưa có tài liệu xuất bản" + link mở kho **PASS**.
- Tab Kiểm thử câu trả lời: empty state "Chưa có lần kiểm thử nào" + hướng dẫn chạy Hỏi thử **PASS**.
- Tab Nhật ký: "Hội thoại của bạn với trợ lý · 20 hội thoại gần nhất", hiện 2 hội thoại thật ("Xin chào" 3 lượt, "Kiểm thử nhật ký P3" 2 lượt) **PASS**.
- `list_console_messages` (error/warn): **không có thông điệp nào**.

### 4.3 NOT RUN / NOT OBSERVED

- **Pytest: NOT RUN** theo yêu cầu dừng test — `NOT RUN ≠ PASS`; backend không đổi trong phiên.
- **NOT OBSERVED:** lưu thật một thay đổi qua API (chủ động chỉ kiểm tra trạng thái nút, không ghi dữ liệu dev), dải stale và lỗi conflict khi người khác cập nhật, menu `⋯` (xóa trợ lý) trên trình duyệt, hành vi mất nháp khi rời route, viewport mobile và ảnh chụp.
- Không chạy migration, không re-index, không commit/push.

## 5. Rủi ro và việc còn lại

- Bản nháp cấu hình chỉ được giữ trong tab Cấu hình khi chuyển tab nội trang; rời route hoặc tải lại sẽ mất nháp (chưa có hộp thoại chặn điều hướng). Cần cân nhắc nếu người dùng muốn bảo vệ nháp.
- Chưa lưu thật lần nào từ form inline trong phiên; nhánh thành công/`revision_conflict` mới được đọc mã và kiểm tra trạng thái nút, sẽ đo ở lần chỉnh cấu hình thật tiếp theo.
- Dữ liệu kiểm thử cũ trong dev (2 hội thoại) vẫn còn, chưa xóa.
- Dev DB vẫn `0026`; migration `0027_drop_ws_model_policy` + `0028` tiếp tục chờ duyệt (#223).
- Bước tiếp theo của lộ trình: **SSO cho `frontendV2`** trước khi thay website trên server.
- Chưa commit/push; working tree còn nhóm tệp trợ lý/Chat của phiên 959–961.
