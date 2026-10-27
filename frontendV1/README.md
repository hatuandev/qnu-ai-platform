# Frontend V1 · Bản mẫu đầy đủ QNU-KTX

Sao chép FE từ `D:/DuAnPhanMem/QLKTX/qnu-ktx/src/Web/ClientApp` theo lựa chọn
người dùng: **giữ toàn bộ màn hình và nghiệp vụ KTX làm mẫu, thay nghiệp vụ sau**.
Giữ đủ 78 tệp route, navigation, layout, component và các trang nguồn.
Không chuyển menu thành QNU AI trong đợt này.

## Chạy

Yêu cầu Node.js 22.12 trở lên; đã kiểm tra với Node 24.15.0.

```powershell
cd D:\DuAnPhanMem\qnu-ai-platform\frontendV1
npm ci --ignore-scripts --no-audit --no-fund
npm run dev
```

Mở <http://127.0.0.1:3001/design-system>, <http://127.0.0.1:3001/users>
hoặc <http://127.0.0.1:3001/dashboard>. Cổng 3001 cố định, khác FE cũ.
Có thể tạo `.env.local` từ `.env.example` để đổi `FRONTEND_PORT`.
Không cần .NET Aspire, SSO hay backend KTX để xem mẫu.

## Tự đăng nhập khi phát triển local

Mặc định **TẮT**. Khi bật, Vite dev server tự lấy token qua cầu nối nội bộ để
không phải nhập access key mỗi lần tải lại trang. Access key **không bao giờ đi
vào trình duyệt**: nó chỉ được đọc trong tiến trình Node của dev server.

Bật bằng cách tạo `frontendV1/.env.local` (đã bị `.gitignore`):

```dotenv
QNU_DEV_AUTO_LOGIN=true
QNU_DEV_ACCESS_KEY=<đúng bằng DEV_ACCESS_PASSWORD của backendV1>
```

Không dùng tiền tố `VITE_` cho hai biến này: mọi biến `VITE_*` bị nhúng thẳng
vào bundle. `.env.example` chỉ nhắc tên biến trong chú thích; không đặt giá trị
thật vào đó, vào tài liệu hay vào log.

Điều kiện phía `backendV1` (không thay đổi trong mã này):

- `DEV_AUTH_ENABLED=true`, `ENVIRONMENT` khác `production`;
- `DEV_ACCESS_PASSWORD` trùng `QNU_DEV_ACCESS_KEY`;
- `SECRET_KEY` tối thiểu 32 byte để ký được token;
- backend chạy ở `http://127.0.0.1:8002` (hoặc `QNU_API_PROXY_TARGET` trỏ tới
  một địa chỉ loopback).

Cách hoạt động:

1. Trình duyệt `POST /__qnu_dev/auto-login` trên chính dev server.
2. Middleware đọc `QNU_DEV_ACCESS_KEY`, gọi `POST /platform/v1alpha1/auth/login`
   hiện có của backendV1 rồi chỉ trả về `access_token`.
3. Token được giữ trong bộ nhớ như khi đăng nhập thủ công; `GET /auth/me` vẫn
   phải xác minh actor trước khi mở trang được bảo vệ.

Ranh giới an toàn:

- Plugin chỉ được đăng ký khi `command === "serve"` và `mode !== "production"`,
  nên `vite build`/`vite preview` không có endpoint này.
- Cầu nối từ chối request không phải `POST`, `Host`/`Origin` không phải loopback
  hoặc khác origin, và từ chối gọi tới địa chỉ backend không loopback.
- Đăng xuất sẽ đặt cờ chặn trong `sessionStorage` (chỉ là boolean, không chứa
  credential) để không tự đăng nhập lại; nút **Tự đăng nhập bằng cấu hình local**
  hoặc **Thử lại** bật lại rõ ràng.
- Thiếu cấu hình, sai access key hoặc backend chưa chạy đều hiện màn hình lỗi
  giải thích đúng nguyên nhân kèm nút thử lại và lối đăng nhập thủ công/SSO.

Kiểm tra tự động: `tests/dev-auto-login-672.test.ts` (middleware),
`tests/dev-auto-login-ui-672.test.tsx` (luồng UI) và
`tests/dev-auto-login-bundle-672.test.ts` (credential không lọt vào `dist/`).

## Phạm vi tích hợp và chế độ mẫu

- **Đã tích hợp thực tế QNU AI & SSO**:
  - Xác thực qua **QNU Single Sign-On (OpenIddict)** với chuẩn Authorization Code Flow + PKCE S256 (`qnu-ai-platform`, scope `openid profile email roles offline_access ai.api`, audience `ai.api`).
  - Callback tại `/signin-oidc` xác minh transaction, PKCE code verifier và đổi token trực tiếp qua OIDC manager.
  - Sau callback, access token được nạp vào bộ nhớ phiên (`session-token.ts`), gọi `GET /platform/v1alpha1/auth/me` để backend xác minh chữ ký RSA qua JWKS, audience và ánh xạ actor/quyền trước khi mở trang được bảo vệ.
  - Token không bao giờ lưu vào `localStorage` hay `sessionStorage`; transaction state chỉ giữ tạm thời trong `sessionStorage` (`qnu_ai_oidc_txn_`) và dọn sạch sau callback.
  - Các trang Workspaces (`/workspaces`, `/workspaces/$workspaceId`), Kho tri thức (`/workspaces/$workspaceId/collections`, `/workspaces/$workspaceId/collections/$collectionId`, `/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId`) và ModelOps (`/modelops`, `/modelops/$providerId`) kết nối với `backendV1` qua proxy `/platform/v1alpha1` (cổng 8002) với session isolation, scoped TanStack query cache, và loại bỏ hoàn toàn secret khỏi `MutationCache`.
  - **Kho tri thức giai đoạn đầu**:
    - Danh sách, tạo mới, sửa metadata và chi tiết bộ sưu tập (`KBCollection`).
    - Tải lên nguồn tài liệu mới (`KBSource`) bằng `multipart/form-data` qua `v1Client.upload` giữ nguyên bytes, hỗ trợ tiêu đề tùy chọn và header `Idempotency-Key` bảo vệ retry.
    - Lịch sử phiên bản (`KBRevision`) bất biến; tải lên phiên bản mới (chỉ tệp, từ chối title).
    - Tải tệp gốc binary bằng `v1Client.requestBlob` với Bearer token và phân giải filename RFC 5987 an toàn; xem trước PDF inline qua Blob Object URL được dọn dẹp khi unmount; chỉ dẫn tải xuống rõ ràng cho DOCX.
  - **Quản lý Trợ lý AI (Assistants)**:
    - Danh sách trợ lý AI trong workspace (`/workspaces/$workspaceId/assistants`) phân trang mảng trung thực theo `limit` và `offset` (không giả `total` hay page wrapper), hỗ trợ lọc client-side trên phạm vi đã tải.
    - Tạo mới trợ lý qua Dialog gắn với một bộ sưu tập kho tri thức và model chat được cấp phép (lọc capability `chat` từ ModelOps catalog của workspace).
    - Hỗ trợ lựa chọn "Theo mặc định workspace" (`chat_provider_id = null`) để backend tự động giải quyết model chat theo cấu hình ModelOps.
    - Trang chi tiết độc lập (`/workspaces/$workspaceId/assistants/$assistantId`) phân chia rõ ràng các khối: Thông tin chung, Kho tri thức gắn kết (bất biến), Cấu hình Model Chat, Persona/chỉ dẫn hệ thống, Tham số phản hồi & RAG (`top_k`, `history_turns`, `max_output_tokens`), và Checklist điều kiện hoạt động trung thực.
    - Sửa cấu hình và bật/tắt hoạt động (`is_active`) gửi đầy đủ payload và kiểm tra xung đột phiên bản qua `expected_revision`.
    - Phân quyền chặt chẽ theo backend contract: chỉ workspace `admin` hoặc platform admin mới có quyền tạo/sửa/bật/tắt trợ lý; thành viên và editor có quyền xem cấu hình.
  - **Trò chuyện với Trợ lý AI (Conversations & Chat)**:
    - Danh sách cuộc trò chuyện của chính người dùng đăng nhập trong workspace (`/workspaces/$workspaceId/conversations`) phân trang mảng theo `limit` và `offset`, hỗ trợ tìm kiếm và lọc trạng thái Đang mở / Đã lưu trữ.
    - Tạo cuộc trò chuyện mới từ một trợ lý AI đang hoạt động (có thể tạo từ danh sách hội thoại hoặc bấm nút *Trò chuyện* trên trang chi tiết trợ lý).
    - Trang chat độc lập hỗ trợ deep link (`/workspaces/$workspaceId/conversations/$conversationId`), responsive trên cả mobile và desktop, hỗ trợ đổi tên, lưu trữ và mở lại cuộc trò chuyện (khi lưu trữ thì khóa nhập chỉ đọc).
    - Gửi câu hỏi đồng bộ với backend thật (không có streaming SSE giả): số thứ tự `expected_turn_no` lấy nghiêm ngặt từ `conversation.last_turn_no`, gửi kèm header `Idempotency-Key` chuẩn UUID v4, chống double submit, giữ nguyên key và toàn bộ body khi retry cùng thao tác.
    - Trạng thái lượt hỏi minh bạch: hiển thị spinner trung thực khi `running` (polling có giới hạn và tự dọn dẹp khi đổi phiên/unmount, không làm hiệu ứng gõ chữ giả), `completed`, `failed` (hiển thị mã lỗi và nút thử lại với cùng key), `uncertain` (cảnh báo quá hạn lease).
    - Dẫn nguồn và trích đoạn bằng chứng: hiển thị các mệnh đề `statements` kèm nút dẫn nguồn bấm mở `CitationSheet` hiển thị trích đoạn bằng chứng, mã tài liệu/phiên bản, tọa độ trang/bảng biểu, độ khớp (score), và chỉ dẫn trung thực "Không có thông tin" khi metadata thiếu.
    - Bảo vệ an toàn dữ liệu: khi `source_status === "unavailable"` hoặc `result === null`, loại bỏ kết quả cũ và hiển thị cảnh báo nguồn không còn khả dụng; phân biệt rạch ròi kết quả nghiệp vụ `insufficient_evidence` (với lý do `no_eligible_content`, `no_match`, `model_abstained`) với lỗi hạ tầng hay lỗi provider.
    - Quyền truy cập: mọi thành viên hợp lệ trong workspace đều có thể tạo hội thoại và gửi câu hỏi với trợ lý đang hoạt động (không giới hạn quyền chat chỉ cho admin).
  - **Cấu hình RAG, chỉ mục/tìm kiếm và kiểm chứng (Context673/675)**:
    - `rag_policy` là một phần của hợp đồng trợ lý: `retrieval_mode` (dense/hybrid/hybrid_rerank), `candidate_k`, `rrf_k`, provider rerank, `metadata_filter`, cửa sổ/ngân sách ngữ cảnh, và kiểm chứng (`off`/`observe`/`enforce`, provider, ngân sách token).
    - Form sửa trợ lý có mục gập **Truy xuất & kiểm chứng nâng cao (RAG)** với nhãn tiếng Việt; không phải nhập JSON. Mặc định giữ đúng tương thích backend (dense, cửa sổ 0, kiểm chứng tắt) — không tự nâng lên hybrid và không tự bật judge.
    - `toRagPolicy` bỏ provider rerank ngoài `hybrid_rerank` và bỏ provider kiểm chứng khi chế độ `off`, để không gửi id không dùng được. Trang chi tiết trợ lý hiển thị `RagPolicySummary` kèm ghi chú đổi cấu hình chỉ áp dụng cho hội thoại mới.
    - Tab **Chỉ mục & Tìm kiếm** trong trang bộ sưu tập: tạo index generation bằng endpoint thật với `Idempotency-Key` (`created: false` hiển thị là replay), bảng lượt chạy có trạng thái/mã lỗi thật, cảnh báo khi không có generation đang hoạt động, và form **Tìm kiếm thử** (query, mode, `top_k`, `candidate_k`, `rrf_k`, provider rerank, metadata filter) với trạng thái rỗng/lỗi trung thực; điểm số được ghi rõ không phải xác suất.
    - Chat gửi `metadata_filter` tường minh qua mục gập **Phạm vi metadata** (chỉ áp dụng cho lượt kế tiếp). Khi trợ lý đã ghim phạm vi, ô nào lệch sẽ được cảnh báo trước và backend trả `conversation_scope_conflict` được mở lại đúng panel để sửa; không bao giờ lấy câu trả lời cũ làm căn cứ.
    - Đăng ký tài liệu/phiên bản cho phép khai báo `retrieval_metadata` (target `document`/`paragraph:s:p`/`table:citation:row:r[:column:c]`, giá trị năm/ngành/đợt/hiệu lực, và trích đoạn nguồn chứng minh). Trình soạn thảo phản chiếu luật backend (không suy đoán từ tên tệp, `document` chỉ nhận năm ban hành và khoảng hiệu lực, mỗi giá trị phải xuất hiện trong câu trích).
    - Trang phiên bản hiển thị metadata kèm căn cứ và `retrieval_metadata_sha256` do backend tính. Cổng duyệt yêu cầu xác nhận riêng cho metadata rồi gửi lại đúng hash đó trong `review_ack`; người duyệt không nhập hay sao chép hash. Lỗi `publication_metadata_review_required` buộc xem lại.
    - Kết quả kiểm chứng được hiển thị qua `trace.verification`: `supported` được mô tả là kiểm tra tự động, không phải bảo đảm tuyệt đối; `unsupported`/`uncertain` hiện cảnh báo `role="alert"` kèm lý do và trích đoạn để đối chiếu; chế độ `enforce` bị chặn hiển thị đúng nguyên nhân kiểm chứng, không phải lỗi kết nối. Token của bước sinh và của judge tách riêng; thiếu usage là "không rõ", không phải 0.
    - Lượt hỏi bị hủy (`cancelled`/`operation_cancelled`) là trạng thái kết thúc: giải thích do dừng trợ lý hoặc lưu trữ hội thoại, không có thân câu trả lời rỗng, không gợi ý gửi lại như yêu cầu mới với cùng khóa idempotency.
    - Bản nháp hậu OCR được giữ trong store theo phiên (`sessionId`/workspace/collection/source/revision/lượt OCR) nên chuyển sang tab đối chiếu ảnh rồi quay lại vẫn còn; đổi lượt OCR hoặc rời trang khi còn nháp sẽ hỏi xác nhận, và nháp không bao giờ bị mang sang nguồn khác. Xung đột phiên bản không tự đổi căn cứ của nháp — người dùng chọn áp dụng lên bản mới.
  - **Xử lý OCR & Rà soát văn bản hậu OCR (OCR Processing & Post-OCR Text Review)**:
    - Chọn revision và quản lý danh sách lượt xử lý (`/processing-runs`), phân trang chuẩn `Page` (`meta: { page, page_size, total }`).
    - Yêu cầu xử lý OCR mới với catalog provider capability `ocr` (hoặc mặc định workspace với `provider_id = null`), cờ `force: false` (tái sử dụng lượt hoàn tất tương đương mã 200) hoặc `force: true` (tạo generation mới mã 201 với cảnh báo token).
    - Trạng thái từng trang (`pending`, `in_flight`, `completed`, `blank`, `failed`, `uncertain`), số đếm trang `pages_done / pages_total` (chờ xác định khi null, không sinh phần trăm giả), attempt count, usage tokens (không đổi null thành 0).
    - Nút *Gửi xử lý lại (Dispatch)* cho các lượt `dispatch_pending`.
    - Đối chiếu ảnh trang PNG render với nội dung văn bản/bảng biểu song song trên Desktop (zoom/pan, bbox) và tab dọc trên Mobile; disclaimer layout cho DOCX; xem raw response JSON gốc khi cần.
    - Tái dựng bảng theo hàng canonical, `row_span`, `col_span`, `header`, bảo toàn ô rỗng và dấu gạch.
    - Rà soát văn bản hậu OCR (`text-review`): duyệt các phiên bản đã lưu (v0 OCR gốc, v1, v2...), sửa nội dung từng đoạn/ô vào draft cục bộ (không sửa evidence_id hay cấu trúc bảng), modal đối chiếu trước/sau, lưu sửa đổi với `Idempotency-Key`, `expected_version`, `expected_sha256` và mảng changes `before`/`after`.
    - Giữ nguyên draft khi gặp xung đột phiên bản `409 ocr_text_version_conflict`, cho phép người dùng nạp lại hoặc đối chiếu mà không bị mất bản nháp.
    - Kiểm tra chính tả bằng AI (Chat ModelOps capability `chat`, 1-100 đoạn đã chọn): tính toán span theo Unicode code point (tương thích Python, xử lý ký tự ngoài BMP), áp dụng gợi ý theo thứ tự offset giảm dần chống chồng lấn, chỉ cập nhật draft cục bộ, không tự động áp dụng toàn bộ.
    - Tải xuống và xem kỹ thuật các artifact: Canonical Document JSON theo đúng phiên bản, Derivative Markdown theo đúng phiên bản, Processing Manifest kiểm tra hash/toàn vẹn, và Evidence Snapshot ghim nguồn phục vụ Compiler.
  - Hỗ trợ luồng đăng xuất: xóa sạch token bộ nhớ, hủy query pending, dọn mutation cache và kích hoạt SSO end-session redirect.

- **Màn hình KTX giữ làm bản mẫu**: Giữ các màn hình hồ sơ, sinh viên, xếp phòng, hợp đồng, cư trú, phòng/tầng/tòa nhà, học vụ, mức phí, hóa đơn, công nợ, thanh toán, báo cáo, hỗ trợ, thông báo và không gian sinh viên.
- `src/app/api/backend-fetch.ts` tiếp tục chặn toàn bộ các lời gọi fetch của các màn hình KTX mẫu. Không có proxy sang backend KTX.
- Dữ liệu minh họa trên các trang KTX chỉ là mẫu UI; thao tác mẫu chỉ thay đổi trạng thái trong trình duyệt.
- Giữ React 19, TypeScript, Vite 8, Tailwind 4, TanStack và Radix/shadcn, semantic tokens Academic Teal, responsive layout và light/dark.
- Không sao chép `.env.local`, node_modules, dist, cache, cấu hình IDE hoặc lịch sử Git.
  Dependencies được cài mới theo lockfile nguồn, không nâng phiên bản; LICENSE và
  THIRD_PARTY_NOTICES được giữ lại. Repo nguồn không bị chỉnh sửa.

## Kiểm tra

```powershell
npm test
npm run lint
npm run build
```

`npm test` dùng Vitest, hỗ trợ alias Vite và TSX. Các kiểm tra API/auth hiện có
được giữ; kiểm tra tương tác dùng React Testing Library và jsdom với dữ liệu
tổng hợp, không gọi backend/model thật. Chạy một nhóm bằng
`npm test -- tests/compilation-ui-671.test.tsx`.

Sau Context675 bộ chính có 190 test/20 tệp. Các tệp hồi quy mới:
`tests/auth-auto-login-race-674.test.tsx` (F1), `tests/ocr-draft-674.test.tsx` (F2),
`tests/v1-rag-contracts-674.test.ts` (hợp đồng `metadata_filter`, `retrieval_metadata`,
`review_ack` hash, index/search idempotency, policy mặc định và biên lỗi đọc bản
xuất bản) và `tests/rag-ui-674.test.tsx` (lượt bị hủy, cảnh báo kiểm chứng, xác
nhận metadata trước khi duyệt).

Build sinh `src/routeTree.gen.ts` rồi kiểm tra TypeScript; không sửa file sinh này
bằng tay. Sau clone sạch, chạy build/dev trước `npm run typecheck` riêng.

`npm run lint` (Biome) đã đạt trên toàn bộ 489 tệp sau Context675 (0 error/0 warning);
báo cáo Context650/671 là lịch sử của giai đoạn còn nợ lint. `frontendV1/storage/artifacts`
là thư mục output đã bị Git ignore và bị loại khỏi phạm vi Biome; các báo cáo QA cũ
được chuyển vào đó để giữ bằng chứng, không xoá.

## Khi chuyển sang QNU AI

Navigation ở `src/navigation/config.ts`; routes chỉ điều phối, nghiệp vụ ở
`src/features`, primitives ở `src/components/ui`, helpers ở `src/components/admin`.
Token màu ở `src/styles/tokens.css`.

Thay từng module KTX bằng workspaces/ModelOps/kho tri thức/trợ lý sau khi chốt
contract với backendV1. Khi nối API thật, thay đồng bộ runtime/auth/backend-fetch,
claim mapping và permission KTX bằng quyền thực của QNU AI; bỏ role demo trước khi
phục vụ dữ liệu thật. Không dùng permission `ktx.*` hoặc role trong localStorage
để chứng minh quyền workspace. Không đặt secret vào biến `VITE_*`.

`docs/architecture.md` và `docs/NEXT_STAGE_PROMPT.md` là tài liệu tham khảo từ
source; các chỉ dẫn nghiệp vụ KTX bên trong không phải yêu cầu triển khai QNU AI.
