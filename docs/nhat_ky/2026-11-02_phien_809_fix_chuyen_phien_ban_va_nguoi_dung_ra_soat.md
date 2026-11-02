# Phiên 809 — Sửa chuyển phiên bản và bước người dùng rà soát

## Yêu cầu và phạm vi

Sửa hai P2 của review 808 và bảo đảm người dùng có thể xem, sửa sau OCR và sau compiler/AI review. Giữ toàn bộ diff FE807/BE có trước. Chỉ sửa frontend, test và hướng dẫn; không thay backend, ModelOps, DB, index, publication hoặc tiến trình serve chính.

## Thay đổi

- `source-detail-page.tsx`: sau save chọn chính `updated.version`, không refetch query lịch sử cũ rồi đưa bản đó sang compiler.
- `ocr-text-review-panel.tsx`: cùng hành vi trên tuyến Stage OCR, dùng version thực từ response thay vì suy `doc.version + 1`.
- `ocr-queries.ts`: seed snapshot vừa lưu vào cache đúng version và latest của session/source/run trước invalidation. Bảo toàn cache lịch sử và các scope khác. Compiler vẫn nhận version ghim cụ thể, không tự lấy latest âm thầm.
- `compilation-dialog.tsx`: effect khởi tạo được chặn theo lần mở và danh tính workspace/collection/run/revision/text version. Parent tạo object mới cùng giá trị không xóa topic, model, output, review hoặc idempotency key. Mở lại/chuyển căn cứ thật vẫn reset đúng.
- `compilation-review-tab.tsx` và detail page: thêm hướng dẫn người dùng kiểm tra sau báo cáo AI và nút **Xem và chỉnh sửa bản biên soạn** cho người có quyền sửa, compiler completed. Nút chỉ chuyển tab/deep link, không gọi model hay tự lưu.
- Giữ trình sửa compiler hiện có: chỉnh nội dung → preview server → xác nhận tạo lượt dẫn xuất mới → đăng ký đúng bản → duyệt/xuất bản. Bản cũ, citations và nguồn bất biến được giữ. AI review không tự sửa/xuất bản; không bắt buộc phải thay chữ nếu bản đã đúng. Chính sách bỏ AI review/approval có sẵn không bị thay đổi.
- Hướng dẫn sử dụng cập nhật trong `V1_TEST_OCR_QUY_CHE_363.md`.

## Kiểm chứng thực chạy

Từ `frontendV1`:

1. Regression trước sửa: `vitest run tests/compilation-dialog-state-809.test.tsx tests/ocr-review-ux-806.test.tsx --reporter=dot` → exit 1, **2 FAIL / 11 PASS**, đúng mất topic và bàn giao v1 sau save v2. Lượt đầu harness thiếu jsdom/scrollIntoView đã được sửa trong test trước khi ghi nhận hai lỗi hành vi; không đổi kỳ vọng để xanh.
2. Test mở rộng sau sửa → 22 PASS / 1 FAIL do locator test tìm nhầm nhãn nút xác nhận; sửa locator theo nút thật **Xác nhận tạo bản mới**, giữ nguyên kiểm preview/hash/không tự accept.
3. `vitest run --reporter=dot` → exit 0, **77 suites / 684 tests PASS**, 61.63 giây. Bao gồm regression state/cache/historical selection, quyền viewer, chuyển từ báo cáo sang sửa và preview trước xác nhận lưu compiler. Fake API trong test không phải live inference.
4. `npm run build` → exit 0 (Vite + `tsc --noEmit`), có cảnh báo bundle trên 500 kB và cảnh báo configLoader native tương lai; không phải lỗi build.
5. Biome check 10 source/test files có thay đổi → exit 0. UTF-8 không BOM/LF 10 files và `git diff --check` đạt.

Không chạy backend suite vì không thay Python/API contract. Không chạy lại live OCR/compiler/RAG hoặc retry model.

## Kiểm tra giao diện cô lập

Preview dùng component thật `CompilationReviewTab` và CSS build hiện tại, dữ liệu giả chỉ trong `tmp/ui809/`; không truy cập tài liệu/model/API thật.

- Chromium kiểm 390px và 1280px, sáng/tối: **4/4** lần nút chỉnh sửa hiển thị, không tràn ngang toàn trang, không pageerror sau sửa harness.
- Đã xem ảnh 390-light và 1280-dark; hướng dẫn đọc được, mobile nút nằm dưới đoạn mô tả, desktop nằm cùng hàng.
- Lượt preview đầu thiếu mock catalog theo alias nên thiếu auth provider và timeout; sửa riêng harness, kiểm tra cuối đạt. Không sửa ứng dụng để che lỗi môi trường thử.
- Screenshot `tmp/ui809/review-{390,1280}-{light,dark}.png`. Preview port 64809 đã dừng bằng Ctrl+C. Không restart serve chính.

## Giới hạn và trạng thái

Hai lỗi 808 đã có regression đạt trên mã mới. Kiểm chứng này xác nhận hành vi FE và contract nội bộ; chưa nghiệm thu live end-to-end hay chất lượng sửa chính tả của model. Không thay nhánh, commit, push hoặc cleanup dữ liệu. Các junction dependency trong thư mục tạm giữ nguyên, không xóa đệ quy.
