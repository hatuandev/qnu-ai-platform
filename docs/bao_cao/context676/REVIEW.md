# Context676 — Review frontendV1 sau prompt Context675

Kết luận: **CHANGES REQUESTED**. Bốn lỗi cũ của Context674 đều vượt qua bộ
probe cũ; các màn cấu hình RAG, metadata, chỉ mục/tìm kiếm và kiểm chứng đã
được bổ sung. Tuy nhiên còn **4 nhóm lỗi được tái hiện độc lập** bên dưới.
Đây là review, không sửa mã ứng dụng hoặc làm thay đổi dữ liệu phục vụ.

Đã đọc AGENTS gốc/v1, PROJECT_CONTEXT, skill clean-code/frontend/admin-design,
quy tắc kiểm chứng/memory; đối chiếu mã FE và contract BE hiện tại. Memory675
chỉ là ngữ cảnh. Git vẫn coi frontendV1/backendV1 là untracked, nên không dùng
Git diff rỗng làm bằng chứng không có thay đổi: đối chiếu snapshot674 và giữ
snapshot hash774 tệp ứng dụng trước/sau review.

## R1 — P1: sửa tiếp có thể tự đổi căn cứ toàn bộ nháp hậu OCR

Vị trí: [ocr-draft-store.ts:203](../../../frontendV1/src/features/knowledge/ocr-draft-store.ts#L203).

`useOcrDraft.update` lấy map thay đổi đang có nhưng luôn gọi `writeOcrDraft`
với `base` hiện tại từ server. Khi nháp bắt đầu ở v0, server đã sang v1,
chỉnh thêm một đoạn hoặc hoàn tác một đoạn có thể đổi căn cứ của **toàn map**
sang v1 mà người dùng chưa chọn chấp nhận căn cứ mới. Những sửa cũ vẫn còn.
`baseMovedOn` trở thành false; cảnh báo xung đột và điều kiện khóa lưu biến mất.
Luồng lưu gửi version/hash của `doc` mới nên server không còn nhận được căn cứ
v0 để phát hiện xung đột với các sửa cũ.

Tái hiện bằng hook thật: tạo nháp ev-1/v0 → cập nhật base prop sang v1 → thêm
ev-2; baseVersion thực tế là1 thay vì giữ0. Tái hiện thêm bằng OcrTabContainer
và OcrTextReviewPanel thật: sửa → server trả v1 → cảnh báo hiện → sửa tiếp →
Áp dụng vào nháp → cảnh báo mất, dù không bấm rebase. Cả hai assertion FAIL.

Cần giữ căn cứ đã ghim của nháp đang tồn tại, chỉ đổi khi người dùng chấp nhận
rebase rõ ràng; kiểm lại căn cứ ở thao tác xác nhận lưu, kể cả modal đang mở.
Không sửa raw OCR hoặc bỏ optimistic concurrency của backend.

## R2 — P2: năm nhập sai bị âm thầm bỏ khỏi phạm vi tìm kiếm/chat

Vị trí: [metadata-filter-fields.tsx:30](../../../frontendV1/src/features/rag/metadata-filter-fields.tsx#L30),
được dùng tại IndexPanel và ChatView.

`parseYear` trả null cho cả ô trống lẫn số ngoài1000–9999; `draftToFilter` bỏ
trường null. Nút tìm/gửi là handler riêng, nên min/max của input không tự
chặn hành động như một form submit được kiểm tra hợp lệ. Ví dụ nhập năm202
và bấm Tìm thử: API nhận `metadata_filter: {}` thay vì báo lỗi nhập liệu.
Phạm vi có thể trở thành không giới hạn hoặc kế thừa năm cũ trong hội thoại.

Probe DOM dùng MetadataFilterFields và IndexPanel thật xác nhận mutation được
gọi với filter rỗng, assertion chặn gửi FAIL. Control nhập2026 PASS và giữ đúng
`data_year: 2026`. Mã ChatView cũng chuyển filter rỗng thành null trong lượt gửi;
chưa chạy thêm chat/API thật cho tình huống này.

Cần phân biệt unset với invalid; hiển thị lỗi cạnh ô và chặn tìm/gửi khi có
giá trị không hợp lệ. Không bỏ trường để nới phạm vi.

## R3 — P2: kết quả tìm kiếm giữ lại hoặc về muộn dưới bộ sưu tập khác

Vị trí: [index-panel.tsx:112](../../../frontendV1/src/features/knowledge/index-panel.tsx#L112)
và [setResult:170](../../../frontendV1/src/features/knowledge/index-panel.tsx#L170).

Kết quả và form là state cục bộ không ghim session/workspace/collection;
`handleSearch` luôn setResult khi promise hoàn tất. CollectionDetailPage và
route hiện không đặt key theo các phạm vi này cho IndexPanel. Khi component
được tái sử dụng, chẳng hạn bộ sưu tập đích đã có dữ liệu trong cache, kết quả
của A vẫn hiện khi props/tiêu đề đã chuyển sang B. Phản hồi A đang chờ cũng có
thể xuất hiện sau khi chuyển sang B. Query key của danh sách index không bảo vệ
state kết quả mutation này.

Hai probe trên IndexPanel thật: tìm A xong rồi rerender B; tìm A đang chờ,
rerender B rồi trả kết quả A. Cả hai FAIL vì đoạn nguồn A vẫn hiện. Đây là lỗi
hiển thị sai phạm vi/nguồn, không phải bằng chứng backend cấp quyền sai.

Cần ghim component/state vào session + workspace + collection và vô hiệu hóa
phản hồi thuộc lần tìm/phạm vi cũ. Chỉ xóa kết quả bằng effect chưa đủ để chặn
promise cũ ghi lại dữ liệu.

## R4 — P2, chỉ local dev: SSO bắt đầu khi auto-login đang chờ vẫn bị đua

Vị trí: [provider.tsx:153](../../../frontendV1/src/app/auth/v1/provider.tsx#L153).

Cờ `ssoCallbackActive` chặn **khởi động** auto-login khi đã bật, nhưng
`isAutoLoginResultCurrent` không đọc cờ này tại thời điểm ghi token. Callback
bắt đầu sau khi bridge đã gửi request, trong lúc token store còn trống, không
đổi epoch/session/attempt. Phản hồi dev vì thế vẫn cài token admin giữa lúc
callback SSO đang xử lý. Bộ test hiện tại chỉ thử callback bật trước khi mount,
hoặc SSO đã ghi token, nên không phủ khoảng thời gian này.

Probe dùng V1AuthProvider, token store và bridge client thật với fetch tổng hợp:
chờ bridge → bật callback → trả dev response; token thực tế là token dev thay
vì giữ null. Assertion FAIL. Các ca logout/unmount/SSO đã có token cũ vẫn PASS.

Cần vô hiệu ticket khi SSO nhận quyền điều khiển, hoặc kiểm lại cờ callback
ngay trước khi ghi token và xử lý trạng thái pending phù hợp. Giữ single-flight
StrictMode, xác minh `/auth/me` và giới hạn local dev của bridge. Không kết luận
đây là lỗ hổng bypass auth ở production.

## Kiểm chứng thực chạy

CWD các lệnh frontend: `frontendV1`. Kết quả chi tiết ở [verification.json](verification.json).

| Kiểm tra | Kết quả |
|---|---|
| `npm --silent test -- --reporter=json --outputFile=...` | PASS190/0FAIL/0SKIP, exit0; giữ đủ156 ID test674, thêm34 |
| `npm --silent run lint -- --reporter=json` | PASS489tệp,0error/0warning/0info, exit0 |
| `npm --silent run build` (Vite + tsc) | PASS exit0; còn cảnh báo chunk lớn hơn500kB |
| Vitest config probe674 | PASS11/0FAIL/0SKIP, exit0 |
| Vitest config probe676, lần cuối | **FAIL6/PASS2/0SKIP**, exit1; 4 nhóm lỗi trên, không lỗi setup |
| Bundle guard + template boundary sau build | PASS11/0FAIL/0SKIP, exit0 |
| Hash774tệp FE/BE trước/sau | PASS,0thay đổi/mất |
| API serving/SSO/model thật, upload→chat, desktop/mobile/light-dark/bàn phím | NOT RUN |

Probe mới nằm trong `frontendV1/storage/artifacts/context676-review`, kết quả và
snapshot trong `storage/artifacts/context676-fe-review`; đều là artifact ignored.
Ports được mô phỏng, dữ liệu tổng hợp, không dùng corpus hoặc credential thật.
Lần chạy sơ bộ chỉ có6test (4FAIL/2PASS); sau khi thêm probe auth và OCR UI, lần
cuối8test (6FAIL/2PASS). Có lỗi đường dẫn ở bước tạo hai probe bổ sung ban đầu;
đã sửa runner, không thay assertion/source để làm test đạt.

Không sửa source/tests/config ứng dụng, backend hoặc KTX; không migrate,
reindex, gọi model, restart/deploy hay Git commit/push. Chỉ thêm báo cáo,
probe artifact và mốc memory cho review. Nên sửa R1 trước rồi R2–R4, sau đó
nghiệm thu UI/API thật trong phạm vi được phép.

Tài liệu mới dùng UTF-8 không BOM/LF, liên kết local đã kiểm tra. WORK_LOG và
PROJECT_CONTEXT có CRLF từ trước; chỉ chèn mốc mới dùng LF và giữ nguyên phần
cũ, không đổi định dạng toàn hai tệp ngoài phạm vi review. Kiểm tra toàn tệp
LF ban đầu vì vậy báo FAIL; kết quả cuối tách rõ nội dung mới và hiện trạng cũ.
