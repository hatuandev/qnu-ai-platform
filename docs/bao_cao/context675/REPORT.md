# Context675 — Hoàn thiện frontendV1 theo báo cáo Context674

Tiếp nối Context674 (verdict CHANGES_REQUESTED: 4 nhóm lỗi F1–F4 và 3 khoảng trống
tích hợp G1–G3). Lần này **có sửa ứng dụng** trong `frontendV1`, giữ nguyên các thay
đổi đang có, không mở rộng sang RAG mục 5–6 (không cài Meilisearch/Haystack, không
tách truy vấn, không dựng engine tính toán bảng/số liệu), không chạm màn hình mẫu
KTX và không mở egress của chúng.

Không migrate/restart/deploy, không đổi credential hay cấu hình runtime, không
đánh index lại dữ liệu thật, không gọi model để làm test xanh. Không commit/push.

## 1. Đã sửa gì

### F1/P1 — Bỏ qua đăng nhập admin local (`src/app/auth/v1/provider.tsx`)

`runAutoLogin` trước đây cài token ngay khi promise resolve, nên phản hồi muộn ghi
đè phiên SSO mới, đè lần đăng xuất, hoặc chạy sau khi provider unmount.

Cách sửa: mỗi lần chạy auto-login nhận một **ticket** gồm `epoch`, `attempt` và
`sessionAtStart` (sessionId của token store tại thời điểm gửi). Kết quả chỉ được
ghi khi **kiểm lại tại đúng thời điểm ghi**:

- `mountedRef` còn true,
- `ticket.epoch === authEpochRef.current` (epoch tăng ở `signIn`, `signInWithSso`,
  `signOut`, và khi đổi phiên),
- `ticket.attempt === autoLoginAttemptRef.current` (lần thử mới thay thế lần cũ),
- cờ chặn dev-login chưa được bật,
- `getTokenState().sessionId === ticket.sessionAtStart` và `token === null`.

Bổ sung store `ssoCallbackActive` (`dev-auto-login.ts`, export qua barrel auth):
`signin-oidc.tsx` bật trong effect mount và tắt khi unmount; provider đọc bằng
`useSyncExternalStore` và **không chạy auto-login khi callback SSO đang xử lý**, vì
provider nằm trên router nên không thể suy ra từ route.

Cleanup của effect mount **không** tăng epoch: StrictMode của React 19 chạy
`mount → cleanup → mount` trên cùng instance, tăng epoch ở cleanup sẽ huỷ request
duy nhất đang bay và làm hỏng single-flight. Chỉ `mountedRef` được hạ; epoch chỉ
tăng bởi hành động thật của người dùng.

Vẫn lấy token từ backend và xác minh `/auth/me`; không tạo actor/role giả trong FE.
Không sửa `get_actor`, không bỏ kiểm tra API/workspace. Cầu nối chỉ nằm ở Vite dev
server (`apply: "serve"`), credential ở tiến trình Node.

### F2/P2 — Giữ bản nháp hậu OCR khi đổi tab

`ocr-text-review-panel.tsx` giữ draft trong `useState`, mà Radix Tabs unmount
`TabsContent` không hoạt động → mất bản nháp.

Cách sửa: store ngoài `src/features/knowledge/ocr-draft-store.ts` (dùng
`useSyncExternalStore`), khoá theo `sessionId|workspace|collection|source|revision|lượtOCR`,
lưu `baseVersion`/`baseSha256` của căn cứ. `ocr-tab-container.tsx` đọc draft để
đánh dấu tab, hỏi xác nhận khi đổi lượt OCR và dùng `useBlocker` +
`enableBeforeUnload` khi rời trang còn nháp. Khi server đã có bản mới, panel hiện
cảnh báo và **không tự đổi căn cứ**: người dùng chọn "Áp dụng nháp lên v{n}" (gọi
`rebase` sau xác nhận) hoặc "Huỷ nháp và dùng bản mới"; nút Lưu bị vô hiệu khi căn
cứ đã trôi. Đăng xuất/đổi phiên xoá toàn bộ draft cũ. Không sửa raw OCR, giữ
optimistic concurrency và xử lý 409.

### F3/P2 — Không biến lỗi đọc thành "chưa xuất bản"

`publication-requests.ts`: chỉ **đúng** HTTP 404 + `published_compilation_not_found`
mới trả `null`; mọi 404 khác (kể cả `resource_unavailable`, `compiled_document_not_found`),
lỗi quyền, lỗi kho, lỗi mạng và 5xx đều ném lại. Trang chi tiết có nhánh
`publishedQuery.isError` riêng: tiêu đề "Không đọc được trạng thái xuất bản", mô tả
theo mã lỗi (`describePublishedReadError`) và nút "Thử lại" gọi `refetch` — kể cả
khi thông tin tài liệu đã có trong cache.

### F4/P2 — Lượt hỏi bị hủy có trạng thái kết thúc

`TurnStatus` thêm `cancelled`; `chat-message-item.tsx` có nhánh riêng: giải thích
do trợ lý bị dừng hoặc hội thoại được lưu trữ, không có thân câu trả lời rỗng, không
có spinner vô hạn, không mời "thử lại với cùng khóa" như một lỗi, giữ lịch sử và
các câu trả lời đã hoàn tất trước đó. Polling dừng ở trạng thái kết thúc vì điều
kiện chỉ poll khi `status === "running"`.

### G1 — Nối cấu hình RAG, index và tìm kiếm

- `src/features/rag/types.ts` phản chiếu `RagPolicy`, `MetadataFilter`,
  `MetadataValues`, `RetrievalAnnotation`, `VerificationTrace`, `ContextTrace`,
  `RetrievalTrace` và các mã `reason` mới; `DEFAULT_RAG_POLICY` giữ đúng mặc định
  backend (dense, cửa sổ 0, kiểm chứng `off`).
- `src/features/rag/schemas.ts`: form phẳng + zod, `toRagPolicy`/`toRagPolicyForm`.
  `toRagPolicy` bỏ provider rerank ngoài `hybrid_rerank` và bỏ provider kiểm chứng
  khi `off`; không có đường nào tự nâng dense→hybrid hay tự bật judge.
- Form tạo/sửa trợ lý có mục gập "Truy xuất & kiểm chứng nâng cao (RAG)"; payload
  create/update và các lệnh bật/tắt (`assistant-detail-page`, `assistants-panel`)
  đều gửi `rag_policy` đầy đủ. Trang chi tiết hiển thị `RagPolicySummary`.
- `index-types.ts` / `index-requests.ts` / `index-queries.ts` / `index-panel.tsx`:
  tab "Chỉ mục & Tìm kiếm" trong trang bộ sưu tập, dùng đúng endpoint backend,
  `Idempotency-Key` thật (`created: false` hiển thị là replay), polling 3 giây khi
  lượt đang chạy, bảng trạng thái/mã lỗi thật, cảnh báo thiếu generation hoạt động,
  và form tìm kiếm thử có trạng thái rỗng/lỗi trung thực.
- Chat có panel "Phạm vi metadata" gửi `metadata_filter` tường minh cho lượt kế
  tiếp; cảnh báo trước khi đặt giá trị lệch phạm vi trợ lý đã ghim và tự mở panel
  khi backend trả `conversation_scope_conflict`. Không dùng câu trả lời cũ làm căn cứ.

### G2 — Metadata truy xuất và xác nhận khi duyệt

- `publication-types.ts`: `VersionResponse.retrieval_metadata` +
  `retrieval_metadata_sha256`, `CreateDocumentRequest`/`RegisterVersionRequest`
  nhận `retrieval_metadata`, `ReviewAckInput` nhận `retrieval_metadata_sha256`.
- `retrieval-metadata-editor.tsx`: khai báo target (`document`, `paragraph:s:p`,
  `table:citation:row:r[:column:c]`), giá trị (năm dữ liệu, năm ban hành, khoảng
  hiệu lực, ngành, đợt) và trích đoạn nguồn; kiểm tra trước khi gửi phản chiếu luật
  backend (target `document` không nhận năm dữ liệu/ngành/đợt, không trùng target,
  mỗi giá trị phải có câu trích, ngày bắt đầu ≤ ngày kết thúc). Không suy đoán nhãn
  từ tên tệp.
- `register-document-dialog.tsx`: mục gập "Metadata truy xuất (tuỳ chọn)", chặn gửi
  khi còn lỗi, gửi `retrieval_metadata` cho cả tạo tài liệu và thêm phiên bản.
- `retrieval-metadata-view.tsx` + `compiled-version-detail-page.tsx`: hiển thị
  metadata kèm từng câu trích và hash rút gọn ngay dưới tiêu đề phiên bản để người
  duyệt thấy trước khi bấm duyệt.
- `review-gate-dialog.tsx`: khi phiên bản có metadata, phát sinh checkbox xác nhận
  riêng; nút "Xem trước duyệt" bị chặn cho tới khi xác nhận. Payload gửi **đúng**
  `retrieval_metadata_sha256` backend trả về — người dùng không nhập/copy hash.
  `publication_metadata_review_required` bỏ xác nhận và refetch để buộc xem lại.
  Giữ nguyên preview, idempotency, giải trình findings; model không tự duyệt.

### G3 — Hiển thị kết quả kiểm chứng

`verification-panel.tsx` render `trace.verification`: `off`/`not_run` không hiện gì;
`supported` mô tả là kiểm tra tự động, **không phải bảo đảm tuyệt đối**;
`unsupported`/`uncertain` hiện `role="alert"` với lý do và trích đoạn, có nút mở
bằng chứng; báo cáo đầy đủ trong khối gập. `chat-message-item.tsx` phân biệt
`answer_not_supported`/`answer_verification_uncertain` thành nhánh "Câu trả lời
không được phát hành" nêu đúng nguyên nhân kiểm chứng thay vì lỗi kết nối, và vẫn
cho đối chiếu nguồn. Usage của bước sinh ghi "Token sinh", của judge ghi "Token
kiểm chứng"; thiếu usage là "không rõ", không phải 0; token sinh không được gọi là
tổng pipeline.

## 2. Phần RAG đã nối được

| Hạng mục | Trạng thái |
|---|---|
| `rag_policy` trong type/form/trang chi tiết/ payload bật-tắt | Nối, mặc định tương thích backend |
| Cấu hình candidate budget, rerank provider, context window/bytes, verification mode/provider/budget | Nối trong mục gập của form trợ lý |
| `metadata_filter` cấp trợ lý và cấp lượt hỏi | Nối; lượt hỏi gửi tường minh, rỗng thì bỏ trường để backend kế thừa |
| Xung đột phạm vi (`conversation_scope_conflict`) | Cảnh báo trước + mở panel sửa |
| Tạo index generation, theo dõi lượt chạy | Nối endpoint thật, idempotency thật |
| Tìm kiếm thử (dense/hybrid/rerank, metadata filter) | Nối endpoint thật, trạng thái trung thực |
| Khai báo `retrieval_metadata` khi đăng ký tài liệu/phiên bản | Nối |
| Hiển thị metadata + căn cứ trên trang phiên bản | Nối |
| Xác nhận metadata + gửi `retrieval_metadata_sha256` khi duyệt | Nối, hash lấy từ backend |
| Hiển thị verification/context/metadata scope, usage tách biệt | Nối |
| Lượt hỏi bị hủy | Nối |
| Provider catalog theo capability + quyền workspace | Nối — lọc `rerank`/`embedding`/`chat` từ catalog ModelOps của workspace |

## 3. Kiểm tra thực chạy

Cwd `frontendV1`, dùng dependency sẵn có, không cài thêm, không gọi backend/model.

| Lệnh | Kết quả |
|---|---|
| `npx vitest run` | **PASS 190/190**, 20 tệp, 0 FAIL, 0 SKIP, exit 0 |
| `npx biome check . --max-diagnostics=300` | **PASS 489 tệp**, 0 error / 0 warning, exit 0 |
| `npm run build` (Vite + `tsc --noEmit`) | **PASS**, exit 0; cảnh báo chunk > 500 kB vẫn còn (có từ trước) |
| `npx vitest run tests/dev-auto-login-bundle-672.test.ts tests/v1-session-secret-regression.test.ts tests/dev-auto-login-672.test.ts` | **PASS 21/21**, exit 0 |
| `npx vitest run --config storage/artifacts/context674-review/vitest.review.config.ts` | **PASS 11/11**, exit 0 (baseline Context674: FAIL 10 / PASS 1) |
| Grep `dist/` cho `createDevAutoLoginHandler`, `devAutoLoginPlugin`, `sec-fetch-site`, `QNU_DEV_ACCESS_KEY=`, `DEV_AUTO_LOGIN_ENV_KEY`, `AI.Admin`, `act_dev_admin` | **0 tệp khớp** mỗi mẫu |

Bộ test chính tăng 156 → 190: giữ đủ 156 ca cũ, thêm 3 ca OCR draft, 6 ca auth race,
19 ca hợp đồng RAG và 6 ca UI RAG. Không nới lỏng assertion nào; ca duy nhất phải
sửa fixture là `tests/compilation-ui-671.test.tsx` (thêm hai prop bắt buộc mới vào
lần render, giữ nguyên toàn bộ assertion) và `storage/artifacts/context674-review/ocr-draft.test.tsx`
(thêm `useBlocker` vào mock router, giữ nguyên assertion).

### Không đạt / chưa chạy

| Hạng mục | Trạng thái | Điều kiện cần |
|---|---|---|
| Gọi API/SSO/model thật (đăng nhập dev thật, upload→OCR→biên soạn→duyệt→index→chat) | **NOT RUN** | backendV1 chạy ở cổng 8002 + QNU SSO + ModelOps provider thật; phiên này không có listener nào trên 8000/8002/5173 và không được phép khởi động dịch vụ |
| Kiểm tra desktop/mobile thật, bàn phím, light/dark trên các màn hình đã sửa | **NOT RUN** | trình duyệt thật + backend; chỉ kiểm bằng jsdom/DOM, không kết luận tương đương |
| Kiểm chứng cầu nối vắng mặt ở `preview`/production bằng runtime | **PASS một phần** | đã xác nhận bằng grep `dist/` sau build thật; `vite preview` không chạy vì cần server |
| Provider catalog lọc theo capability + quyền workspace cho rerank/verification | **PASS (tĩnh)** | đã lọc `rerank`/`embedding`/`chat` từ `useCatalogQuery(workspaceId)`; chưa đối chiếu với quyền provider thật trên backend vì backend chưa công bố cổng quyền riêng cho RAG |

## 4. Vì sao các ca này chứng minh được lỗi cũ

Probe Context674 chạy trên provider/store/component thật với HTTP và query mô
phỏng; baseline 10 FAIL / 1 PASS được tái lập trước khi sửa. Sau khi sửa, đúng bộ
probe đó (không đổi assertion) PASS 11/11, nên thay đổi hành vi là do mã nguồn chứ
không do nới lỏng kiểm tra. Các ca quan trọng đã được chuyển vào bộ chính để không
phụ thuộc thư mục artifact bị ignore.

## 5. Giới hạn còn lại

1. **Chưa có cổng quyền riêng cho từng provider RAG**: danh sách provider đã lọc theo
   capability (`rerank`, `embedding`, `chat`) từ catalog ModelOps của workspace, nhưng
   backend chưa công bố quyền riêng ở mức provider RAG nên FE chưa có gì thêm để kiểm.
   Nếu backend thêm, phải đọc lại quyền đó thay vì suy từ catalog.
2. **Chưa có smoke thật**: toàn bộ luồng RAG (đăng ký metadata → duyệt có hash →
   index → tìm kiếm → chat có kiểm chứng) mới được kiểm ở mức hợp đồng request và
   DOM, chưa chạy trên dữ liệu thật.
3. **`metadata_filter` cấp hội thoại** chỉ gửi được khi người dùng đặt trong
   composer; chưa có UI xem lại phạm vi đã ghim của hội thoại ngoài dòng mô tả trên
   từng lượt.
4. **Bảng lớn**: trình soạn metadata yêu cầu người dùng biết chỉ số mục/đoạn/hàng;
   chưa có bộ chọn trực quan từ nội dung bản biên soạn.
5. **Kiểm tra giao diện thật** (desktop/mobile, bàn phím, light/dark) chưa chạy.
6. Cảnh báo chunk > 500 kB của Vite vẫn còn; không xử lý trong phạm vi này.

## 6. Tệp thay đổi

Mới: `src/features/rag/{types,schemas,verification-panel,rag-policy-summary,metadata-filter-fields}.ts(x)`,
`src/features/knowledge/{index-types,index-requests,index-queries,index-panel,ocr-draft-store,retrieval-metadata-editor,retrieval-metadata-view}.ts(x)`,
`src/lib/idempotency-key.ts`,
`tests/{ocr-draft-674,auth-auto-login-race-674,rag-ui-674}.test.tsx`,
`tests/v1-rag-contracts-674.test.ts`.

Sửa: `src/app/auth/v1/{provider.tsx,dev-auto-login.ts,index.ts}`, `src/routes/signin-oidc.tsx`,
`src/app/api/v1/{endpoints.ts,index.ts}`,
`src/features/conversations/{types,requests,schemas,chat-view,chat-message-item}.ts(x)`,
`src/features/knowledge/{publication-types,publication-schemas,publication-requests,register-document-dialog,review-gate-dialog,compiled-version-detail-page,compiled-document-detail-page,collection-detail-page,ocr-tab-container,ocr-text-review-panel}.ts(x)`,
`src/features/assistants/{types,requests,schemas,assistant-form-dialog,assistant-detail-page,assistants-panel}.ts(x)`,
`src/routes/workspaces.$workspaceId.collections.$collectionId.index.tsx`,
`tests/compilation-ui-671.test.tsx`, `README.md`.

Không đổi: `src/app/api/backend-fetch.ts`, màn hình mẫu KTX, `get_actor` backend,
`vite.config.ts`, `.env*`, migration, cấu hình runtime.

## 7. Bằng chứng độc lập

`frontendV1` chưa được Git theo dõi nên không có diff nền. Bằng chứng thay vào đó là
hash SHA-256: `verification.json` ghi 47 tệp đã tạo/sửa, còn
`snapshot_sha256.json` ghim toàn bộ **495 tệp** nguồn của `frontendV1`
(`src`, `tests`, `dev`, `config`, tài liệu; loại `node_modules`/`dist`/`storage`)
để phiên sau đối chiếu được chính xác tệp nào đổi.
