# Review chức năng frontendV1 — Context669

Ngày 2026-10-27. Kết luận: **CHANGES REQUESTED**.

Review độc lập các phần QNU đã có: xác thực, workspace, ModelOps, kho nguồn,
trợ lý, chat, OCR/hậu OCR và Compiler. Giữ nguyên mã ứng dụng đang được phát triển.
Phiên khác đang bổ sung publication trong lúc review; các tệp mới đó chưa nằm
trong phạm vi nghiệm thu này. Mã mẫu KTX vẫn là phạm vi được giữ theo AGENTS.

## Các lỗi cần xử lý

### F1 — P1: Bản nháp Compiler không đổi theo lượt đang mở

- File: `frontendV1/src/features/knowledge/compilation-editor-tab.tsx`, dòng 100–128.
- `isInitialized` chỉ chuyển thành true một lần, không đặt lại khi `runId`,
  collection hoặc workspace thay đổi. Trang cha không ghim `key` theo tài nguyên;
  router hiện không cấu hình remount theo params.
- Tái hiện ở handler: tải A, sửa tiêu đề, giữ component rồi chuyển sang B. Preview
  gửi hash bundle B cùng nội dung đang giữ từ A. Đây là nguy cơ lưu nội dung nhầm
  vào tài liệu B; thử nghiệm dừng ở cổng mutation giả lập, không ghi DB.
- Sửa: ghim vòng đời form theo định danh tài nguyên và hash nguồn; bảo vệ bản nháp
  chưa lưu khi điều hướng. Không trộn ngữ cảnh mới với state cũ.
- Probe `R4_switch_compilation_resets_draft`: **FAIL đúng hành vi trên**.

### F2 — P2: Ba hành động tải dữ liệu Compiler luôn thất bại

- File: `compilation-detail-page.tsx`, dòng 107, 139; `compilation-review-tab.tsx`,
  dòng 134–140, cùng thư mục knowledge.
- Markdown Compiler, raw Compiler và Markdown báo cáo review truyền `undefined`
  vào tham số client bắt buộc. Các hàm request đọc `client.requestBlob`, nên lỗi
  xảy ra trước khi gọi API. Directive TypeScript đang che lỗi này.
- Tái hiện handler thật: cả ba hành động chỉ phát thông báo lỗi; số lần gọi cổng
  `requestBlob` bằng 0.
- Sửa: dùng authenticated `v1Client`, bỏ directive che lỗi và kiểm tra tải binary.
- Probes `R1_compiler_downloads_use_client`, `R1b_review_markdown_uses_client`: **FAIL**.

### F3 — P2: Không đọc được lượt chat thứ 51 trở đi

- File: `frontendV1/src/features/conversations/chat-view.tsx`, dòng 69, 479–480.
- Offset khởi tạo bằng 0, nút tải thêm lại trừ 50 rồi chặn ở 0. API backend thực
  sắp xếp `turn_no` tăng dần (`backendV1/qnu/domains/conversations/history.py`).
- Tái hiện hội thoại 60 lượt: sau ba lần bấm, các offset vẫn `[0,0,0,0]`. Người
  dùng chỉ thấy 50 lượt đầu; câu hỏi/kết quả mới phía sau không xuất hiện.
- Sửa: thống nhất chiều phân trang với backend, tải trang chứa lượt mới nhất và
  ghép lịch sử theo ID khi tải thêm.
- Probe `R2_chat_history_can_reach_turn_51`: **FAIL**.

### F4 — P2: Sửa tiêu đề mục Compiler làm remount ô đang gõ

- File: `frontendV1/src/features/knowledge/compilation-editor-tab.tsx`, dòng 497.
- React key chứa `section.heading.slice(0, 15)`. Gõ trong 15 ký tự đầu thay key của
  cả section, tạo lại subtree chứa input; người dùng có thể mất focus/con trỏ.
- Probe đổi heading A → AX xác nhận key đổi. Chưa chạy DOM sau đăng nhập để đo
  focus trực tiếp; tác động remount được xác định từ React reconciliation.
- Sửa: ID cục bộ ổn định cho mục/đoạn, tách khỏi nội dung đang sửa.
- Probe `R3_heading_edit_keeps_section_identity`: **FAIL**.

### F5 — P2: Danh sách Compiler/review không được làm mới sau thao tác thành công

- File: `frontendV1/src/features/knowledge/compilation-queries.ts`, dòng 484–489,
  526–535, 585–590.
- Query list có `{limit: 20}` hoặc `{limit: 50, offset: 0}`. Invalidation dùng
  object với thuộc tính `undefined`, không phải prefix trước phần tham số.
- Tái hiện với QueryClient thật: sau callback tạo run, list limit=20 vẫn có
  `isInvalidated=false`. Tạo/sửa/review có thể báo thành công nhưng danh sách vẫn
  cũ. Default `refetchOnWindowFocus=false` làm lỗi khó tự hồi phục hơn.
- Sửa: dùng prefix key cho toàn bộ list của đúng session/workspace/collection/run,
  hoặc cập nhật cache chính xác; kiểm tra cả list run và list review.
- Probe `R6_new_compilation_invalidates_visible_list`: **FAIL**.

### F6 — P2: Hai lớp xử lý auto-review không thống nhất trạng thái

- File: `compilation-requests.ts`, dòng 131–150; `compilation-queries.ts`, dòng
  286–320, cùng thư mục knowledge.
- Request đã trả `{status: "none", notScheduled: true}` khi chưa có intent; hook
  lại ghi đè thành `notScheduled: false`. Hook không polling khi status=none;
  danh sách review cũng không polling/invalidate khi auto-review tạo review mới.
- Với trường hợp intent/review xuất hiện sau lần fetch đầu, màn hình có thể giữ
  trạng thái cũ cho đến lần tải lại khác. Ngoài ra request đang nhận mọi HTTP404
  thành chưa schedule, che cả lỗi không tìm thấy tài nguyên khác.
- Sửa: chỉ ánh xạ đúng mã lỗi `compilation_auto_review_not_found`, giữ nguyên
  trạng thái, liên kết `autoReview.review_id` với query report và làm mới list.
- Probe `R5_auto_review_preserves_not_scheduled`: **FAIL** tại chỗ ghi đè flag.

### F7 — P2: Lệnh test chuẩn không khởi chạy được sáu tệp

- File: `frontendV1/package.json`, script `test`; các test import module hook qua
  alias `@/` hoặc import trực tiếp TSX.
- `node --experimental-strip-types --test tests/*.test.ts` không phân giải alias
  Vite và không nạp TSX. Kết quả hiện tại: **42 pass, 6 fail, 0 skip**, exit 1.
- Các tệp lỗi: `v1-assistants.test.ts`, `v1-conversations.test.ts`,
  `v1-knowledge.test.ts`, `v1-ocr.test.ts`, `v1-session-secret-regression.test.ts`,
  `v1-sso.test.ts`. Đây là lỗi khởi chạy, không phải sáu assertion nghiệp vụ.
- Sửa runner/import boundary phù hợp; giữ các kiểm tra session/secret thay vì bỏ
  test. Chạy lại toàn bộ bằng đúng lệnh bàn giao.

## Kiểm chứng thực chạy

| Kiểm tra | Kết quả |
| --- | --- |
| `npm test`, cwd `frontendV1` | FAIL, exit 1: 42 pass, 6 tệp fail khởi chạy, 0 skip |
| `npm run build`, cwd `frontendV1` | PASS, exit 0; gồm `tsc --noEmit`; cảnh báo chunk >500kB |
| `npm run lint`, cwd `frontendV1` | FAIL, exit 1: 64 errors, 14 warnings, 6 infos trên 450 tệp |
| Biome phạm vi 96 tệp QNU API/auth/features | FAIL, exit 1: 5 errors, 2 warnings; trong `compilation-detail-page.tsx` |
| Harness review: handler/hook thật, cổng dữ liệu trong bộ nhớ | 7 probes FAIL, xác nhận F1–F6; không sửa app để làm test xanh |
| Browser cổng thử riêng 3009 | Trang đăng nhập hiển thị; chưa kiểm tra các màn sau đăng nhập |
| Backend live / SSO thật / upload / AI inference | NOT RUN trong phiên review |

Lint toàn bộ có lỗi trong mã mẫu nhập trước; vẫn là FAIL. Phạm vi QNU mới cũng
có lỗi, vì vậy không thể quy toàn bộ lỗi cho mẫu KTX. Build đạt không chứng minh
các nút tải, state khi điều hướng hoặc luồng có API thật hoạt động.

Harness nằm ở `storage/artifacts/context668-fe-review/probes.cjs`, kết quả cùng
thư mục. Đây là artifact thử tạm đã bị Git ignore, không phải suite sản phẩm.
Lượt đầu của R1 sai selector nhãn raw; sửa selector trong harness rồi tái hiện cả
hai handler đúng lỗi thiếu client. Các probe khác không cần chỉnh mã sản phẩm.

## Chức năng đang có và giới hạn

| Nhóm | Quan sát từ mã hiện tại |
| --- | --- |
| Workspace/ModelOps | Client v1 thật, token trong bộ nhớ, query gắn session; membership/role hiển thị, provider/key/default/allowlist/quota/audit có màn và request |
| Kho nguồn | Collection, upload PDF/DOCX, revision và tải bản gốc có mã kết nối API |
| Trợ lý/chat | Tạo/sửa/bật tắt, hội thoại, gửi câu hỏi và dẫn nguồn có mã; lỗi lịch sử dài cần sửa |
| OCR/hậu OCR | Yêu cầu/theo dõi OCR, đối chiếu ảnh, sửa nháp, preview trước lưu, kiểm tra chính tả và tải dẫn xuất có mã |
| Compiler | Tạo/theo dõi/đọc bản nháp, citations, bảng nguồn, review và structured edit có mã; các lỗi F1–F6 chặn nghiệm thu |
| Publication | Đang có tệp mới được viết đồng thời; chưa review/kiểm chứng trong snapshot này |
| Index/search, lifecycle ngược, GC/recovery/readiness | Cần đối chiếu tiếp phần FE sau khi các module tương ứng được nối; chưa nghiệm thu FE đầu cuối |

Không kết luận các phần có mã đều hoạt động thực tế. Ưu tiên sửa F1, sau đó
F2–F7 rồi kiểm tra một luồng đầy đủ bằng API/backend và phiên đăng nhập thật.
