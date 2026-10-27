# Context675 — Hoàn thiện frontendV1 theo Context674

User yêu cầu hoàn thiện `frontendV1` theo báo cáo Context674: sửa 4 nhóm lỗi
(F1–F4), nối RAG G1–G3 bằng API backendV1 Context673, giữ các thay đổi đang có và
**không** mở rộng sang RAG mục 5–6. Lần này có sửa ứng dụng.

Trước khi sửa: đọc `AGENTS.md` gốc, `frontendV1/AGENTS.md`, `PROJECT_CONTEXT`,
`docs/bao_cao/context674/REVIEW.md`, `verification.json`, `backendV1/docs/rag-policies.md`;
áp dụng skill `qnu-clean-code-architect`, `qnu-frontend-architect`,
`admin-frontend-design` theo luật repo. Tái lập baseline bằng đúng 5 tệp probe trong
`frontendV1/storage/artifacts/context674-review` (10 FAIL / 1 PASS), và kiểm tra
156 test / lint 472 tệp / build đều đạt trước khi chạm mã.

## Kết quả

**Đã sửa xong F1–F4, nối được G1–G3.** Bộ test chính 156 → **190 PASS/0 FAIL/0 SKIP**
(20 tệp), lint **489 tệp 0 error/0 warning**, build gồm TypeScript PASS, và bộ probe
độc lập của Context674 chuyển từ **10 FAIL/1 PASS** sang **11 PASS/0 FAIL** mà không
đổi assertion nào.

- F1/P1: `runAutoLogin` ghi token ngay khi promise resolve nên phản hồi muộn đè
  phiên SSO mới, đè lần đăng xuất, hoặc chạy sau unmount. Sửa bằng ticket
  `epoch`/`attempt`/`sessionAtStart` **kiểm lại tại thời điểm ghi**, cộng store
  `ssoCallbackActive` để provider (nằm trên router) hoãn auto-login khi
  `signin-oidc` đang đổi token. Cleanup của effect mount **không** tăng epoch, vì
  StrictMode chạy mount→cleanup→mount trên cùng instance và tăng epoch ở cleanup sẽ
  huỷ request duy nhất đang bay.
- F2/P2: draft hậu OCR nằm trong `useState` của panel, mà Radix Tabs unmount
  `TabsContent` không hoạt động → mất bản nháp. Chuyển sang store ngoài theo phiên,
  khoá `sessionId|workspace|collection|source|revision|lượtOCR` + base version/sha;
  đổi lượt OCR và rời trang có xác nhận; xung đột chỉ rebase khi người dùng chọn.
- F3/P2: transport nuốt mọi 404 thành `null`. Nay chỉ **đúng** 404 +
  `published_compilation_not_found` mới là rỗng; trang chi tiết có nhánh lỗi riêng
  kèm nút thử lại, không nói "chưa xuất bản" khi đọc thất bại.
- F4/P2: BE trả `cancelled`/`operation_cancelled`; FE thêm trạng thái kết thúc,
  giải thích do dừng trợ lý hoặc lưu trữ hội thoại, không gợi ý gửi lại như yêu cầu
  mới cùng khoá idempotency.
- G1: `rag_policy` vào type/form (mục gập tiếng Việt)/trang chi tiết/mọi payload
  bật-tắt; tab "Chỉ mục & Tìm kiếm" với endpoint thật, idempotency thật, trạng thái
  thật; chat gửi `metadata_filter` tường minh và xử lý `conversation_scope_conflict`.
- G2: khai báo `retrieval_metadata` (target + giá trị + trích đoạn nguồn) khi đăng
  ký; hiển thị metadata kèm căn cứ trên trang phiên bản; cổng duyệt bắt xác nhận
  metadata riêng rồi gửi **đúng hash backend** trong `review_ack`.
- G3: `trace.verification`/`context`/metadata scope có type và được render;
  `supported` nói rõ là kiểm tra tự động, `unsupported`/`uncertain` cảnh báo kèm lý
  do + trích đoạn; chặn ở `enforce` hiện đúng nguyên nhân kiểm chứng; usage của
  bước sinh và của judge tách riêng, thiếu usage là "không rõ".

## Kiểm chứng thực chạy

Cwd `frontendV1`, dependency sẵn có, không cài thêm, không gọi backend/model.

| Lệnh | Kết quả |
|---|---|
| `npx vitest run` | PASS190/0FAIL/0SKIP, 20 tệp, exit0 |
| `npx biome check . --max-diagnostics=300` | PASS489 tệp, 0error/0warning, exit0 |
| `npm run build` (Vite + `tsc --noEmit`) | PASS, exit0; cảnh báo chunk>500kB có từ trước |
| `npx vitest run tests/dev-auto-login-bundle-672.test.ts tests/v1-session-secret-regression.test.ts tests/dev-auto-login-672.test.ts` | PASS21/0FAIL/0SKIP, exit0 |
| `npx vitest run --config storage/artifacts/context674-review/vitest.review.config.ts` | PASS11/0FAIL/0SKIP, exit0 (baseline 10FAIL/1PASS) |
| Grep `dist/` cho 7 mẫu server-only (`createDevAutoLoginHandler`, `devAutoLoginPlugin`, `sec-fetch-site`, `QNU_DEV_ACCESS_KEY=`, `DEV_AUTO_LOGIN_ENV_KEY`, `AI.Admin`, `act_dev_admin`) | 0 tệp khớp mỗi mẫu |

Test tăng 34 ca: 3 OCR draft, 6 auth race, 19 hợp đồng RAG, 6 UI RAG. Giữ đủ 156 ca
cũ; chỉ hai fixture phải sửa và **không** nới assertion: `tests/compilation-ui-671.test.tsx`
thêm hai prop bắt buộc mới vào lần render, và probe `ocr-draft.test.tsx` thêm
`useBlocker` vào mock router (mã sản phẩm nay dùng hook này).

Probe dùng HTTP/query mô phỏng, component/store/client thật và jsdom. Không kết
luận tương đương browser/live SSO/API/model thật. Không có listener trên
8000/8002/5173 và không được phép khởi động dịch vụ, nên smoke thật
(login→upload→OCR→biên soạn→duyệt→index→chat), kiểm tra desktop/mobile, bàn phím,
light/dark và `vite preview` runtime đều **NOT RUN** kèm điều kiện cần.

## Còn lại

Danh sách provider đã lọc theo capability (`rerank`/`embedding`/`chat`) từ catalog
ModelOps của workspace, nhưng backend chưa công bố quyền riêng ở mức provider RAG nên
chưa có cổng quyền nào thêm để kiểm — không suy đoán thay backend. Ngoài ra:
luồng RAG mới được chứng minh ở mức hợp đồng request và DOM; phạm vi ghim của hội
thoại chỉ hiện qua dòng mô tả từng lượt; trình soạn metadata cần biết chỉ số
mục/đoạn/hàng, chưa có bộ chọn trực quan; cảnh báo chunk>500kB còn.

Artifact ignored: `frontendV1/storage/artifacts/context674-review` (giữ nguyên làm
bằng chứng, đã sửa đúng một dòng mock). Không commit/push, không migrate/restart/
deploy, không đổi credential/cấu hình runtime, không đánh index lại dữ liệu thật,
không chạm màn hình mẫu KTX. [Báo cáo](../bao_cao/context675/REPORT.md),
[verification/hash](../bao_cao/context675/verification.json).
