# Context677 — Sửa 4 lỗi frontendV1 sau review676

Người dùng yêu cầu sửa cả4lỗi đã tái hiện trong
[review676](../context676/REVIEW.md). Đã sửa trong frontendV1, không đổi contract
hoặc hành vi backendV1. Giữ những thay đổi chưa commit đang có.

## Kết quả

| Lỗi | Thay đổi và hành vi sau sửa |
|---|---|
| R1 — Nháp OCR tự đổi căn cứ | `writeOcrDraft` giữ version/hash của nháp đã tồn tại. Sửa thêm hoặc hoàn tác một đoạn không làm mất cảnh báo xung đột. Chỉ rebase được người dùng xác nhận mới đổi căn cứ. Xác nhận lưu kiểm lại căn cứ, khóa nút nếu server đã có bản mới và gửi đúng version/hash đã ghim. Callback thuộc phiên đăng nhập cũ không được sửa/xóa/rebase nháp phiên mới. |
| R2 — Năm sai bị bỏ scope | Hai trường năm dùng chung validator. Giá trị không hợp lệ hiện lỗi gắn với input qua aria-invalid/aria-describedby; chặn cả nút và Enter ở tìm kiếm/chat, giữ nguyên câu hỏi. `draftToFilter` không chuyển năm sai thành unset; ô thực sự trống vẫn giữ quy tắc kế thừa của BE. |
| R3 — Search sai bộ sưu tập | IndexPanel ghim component vào session/workspace/collection, xóa state khi đổi phạm vi. Phản hồi muộn của component đã rời bị bỏ qua. Trong cùng phạm vi, chỉ lần tìm mới nhất được ghi kết quả. Toast của tác vụ tạo index thuộc phiên đã rời cũng không được hiện. |
| R4 — Dev-login đua với SSO | Provider nhận thông báo callback SSO đồng bộ để vô hiệu ticket cũ và đưa trạng thái chờ về idle. Kiểm lại cờ SSO ngay trước ghi token; không cho bắt đầu/retry bridge trong lúc SSO xử lý. Callback bắt đầu rồi kết thúc trước phản hồi dev cũng không khôi phục ticket cũ. |

Không tạo danh tính/quyền giả hoặc mở rộng bypass production. Bridge vẫn chỉ
dành cho local dev và token vẫn qua `/auth/me`. Không thay nguồn/raw OCR,
không bỏ optimistic concurrency hoặc tự duyệt/xuất bản tài liệu.

Sáu tệp ứng dụng:

- [ocr-draft-store.ts](../../../frontendV1/src/features/knowledge/ocr-draft-store.ts)
- [ocr-text-review-panel.tsx](../../../frontendV1/src/features/knowledge/ocr-text-review-panel.tsx)
- [metadata-filter-fields.tsx](../../../frontendV1/src/features/rag/metadata-filter-fields.tsx)
- [chat-view.tsx](../../../frontendV1/src/features/conversations/chat-view.tsx)
- [index-panel.tsx](../../../frontendV1/src/features/knowledge/index-panel.tsx)
- [provider.tsx](../../../frontendV1/src/app/auth/v1/provider.tsx)

Thêm5tệp `frontendV1/tests/regression-677-*.test.tsx`,21test. Tám ca từ review676
được đưa vào suite ứng dụng trước khi sửa, xác nhận6FAIL/2PASS. Sau sửa, bổ sung
kiểm tra modal OCR đang mở khi server đổi version; rebase có xác nhận; callback
cũ sau đổi tài khoản; cả năm dữ liệu/năm ban hành và phím Enter trong chat;
scope workspace/session và kết quả tìm về sai thứ tự; callback SSO đã kết thúc.
Không đổi assertion cũ hoặc giảm phạm vi190test đã có.

## Kiểm chứng thực chạy

CWD các lệnh frontend là `frontendV1`; mọi kết quả sau sửa dưới đây exit0.

| Lệnh/kiểm tra | Kết quả |
|---|---|
| 4 tệp regression đầu tiên trước sửa | FAIL6/PASS2/0SKIP, exit1, đúng4lỗi676 |
| Vitest trọng tâm5tệp mới + auth/OCR cũ | PASS30/0FAIL/0SKIP |
| `npm --silent test -- --reporter=json --outputFile=...` | PASS211/0FAIL/0SKIP; giữ190ID cũ, thêm21, mất0 |
| `npm --silent run lint -- --reporter=json` | PASS494tệp,0error/0warning/0info |
| `npm --silent run build` gồm tsc | PASS; còn cảnh báo chunk>500kB đã có trước |
| Probe độc lập676, config riêng, không đổi assertion | PASS8/0FAIL/0SKIP, từ6FAIL/2PASS |
| Probe độc lập674, config riêng | PASS11/0FAIL/0SKIP |
| Bundle guard/template boundary sau build | PASS11/0FAIL/0SKIP |
| Snapshot774tệp trước/sau | Đúng6tệp ứng dụng thay đổi,0ngoài phạm vi; BE qnu và test cũ giữ hash |
| UTF-8 không BOM/LF | PASS cho6tệp source và5tệp test mới |

Lint lần đầu sau full test còn1warning import không dùng trong test mới. Đã bỏ
đúng import đó và chạy lại lint về0warning; không đổi logic/assertion. Full suite
không chạy lặp lại chỉ vì bỏ import. Các probe độc lập và bundle guards sau đó
được chạy lại trên source cuối.

Artifacts: `storage/artifacts/context677-fe-fixes` gồm baseline/focused/full,
lint trước/sau, build, kết quả hai bộ probe, bundle, snapshot và application.diff.
[verification.json](verification.json) ghi số lượng và phạm vi máy đọc được.

Chưa nghiệm thu trình duyệt desktop/mobile/light-dark, SSO/API/model thật hoặc
luồng upload→chat thật. Test UI dùng DOM jsdom và port tổng hợp; không coi các
kết quả này là bằng chứng chất lượng câu trả lời hay upstream đang hoạt động.

Không sửa BE/KTX, credential hoặc cấu hình đang chạy; không migrate/reindex,
gọi model, restart/deploy, commit/push. Không thêm chức năng ngoài4lỗi đã giao.
Tài liệu mới/source dùng UTF-8 không BOM/LF; phần CRLF có sẵn ở hai index lớn
được giữ, chỉ chèn mốc mới, không đổi định dạng toàn tệp.
