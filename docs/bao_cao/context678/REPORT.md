# Context678 — Frontend mục2–3–4: vòng đời, thay tài liệu, vận hành

Người dùng yêu cầu triển khai cả3nhóm trong một đợt. Đã hoàn tất mã FE, nối
API backendV1 hiện có. Không sửa BE, ModelOps/credential, auth, CSS/design-system,
dev bridge hoặc cấu hình đang phục vụ; không migrate/reindex corpus/deploy.

## Chức năng

| Nhóm | Kết quả |
|---|---|
| 2 — Vòng đời ngược | Menu theo quyền trên kho/nguồn/tài liệu/trợ lý/hội thoại; pause/resume, archive/delete/restore, hủy job/lượt hỏi, dọn index inactive. Lý do → preview tác động thật → xác nhận của người dùng → biên nhận. Thùng rác đọc server, có khôi phục và phân trang không bịa total. |
| 3 — Thay tài liệu | Upload staged mặc định giữ serving revision, có chế độ thường với cảnh báo; nguồn hiển thị latest/serving riêng. Sau OCR/Compiler/duyệt hiện hữu, chọn bản approved tại trang compiled document; preview/accept replace và theo dõi trạng thái đến khi backend chuyển publication/index. |
| 4 — Vận hành | Tab Vận hành có bộ lọc/phân trang/deep link job, summary/usage thật, chi tiết tiến độ/lỗi/lease, hủy/giao lại hợp lệ; readiness admin cho DB/queue/worker/vector/storage/ModelOps/quota, không tuyên bố đã inference. |

Biên nhận pending đã được xác nhận có thể tiếp tục sau tải lại bằng cùng ID,
hash và idempotency key. Dùng key ổn định từ preview ID, không tự phát lại model.
SSO/admin bypass vẫn theo mã cũ. Hội thoại của người khác không trở thành quyền
của admin; owner theo dõi biên nhận qua Thùng rác, không phải xin quyền Operations.
Worker tiếp tục kiểm membership thực, không sao chép quyền client/platform.

Các thao tác tắt/bật trợ lý và lưu trữ hội thoại trực tiếp trước đây được chuyển
sang preview lifecycle để thể hiện tác động/hủy tác vụ trước khi xác nhận. Các
form sửa cấu hình/persona/RAG vẫn theo API hiện hữu. Lỗi/quyền/hết hạn/stale
hiển thị trung thực; response muộn sau đổi scope/session bị loại bỏ.

## Phạm vi tệp

- New domains: `frontendV1/src/features/lifecycle/` và `features/operations/`;
  API paths/client contracts và hai route Workspace `operations`/`resources`.
- Nối vào các màn knowledge, assistants, conversations và workspace tabs.
- Source upload gửi đúng form field staged, giữ title/source provenance.
- 3tệp test mới,33test. `template-boundary.test.ts` chỉ thêm2domain QNU được
  người dùng cho phép vào allowlist; giữ các assertion chặn KTX/API fallback.
- `routeTree.gen.ts` do Vite/TanStack tự sinh khi build, không sửa tay.
- Snapshot779tệp trước thay đổi,16tệp cũ thay đổi và26tệp mới (gồm source/tests).
  Không mất211ID test cũ. Source/BE bảo vệ ngoài phạm vi giữ hash.

## Kiểm chứng thực chạy

CWD: `frontendV1`. Chi tiết [verification.json](verification.json), artifact
`storage/artifacts/context678-fe-lifecycle` (ignored).

| Kiểm tra | Kết quả cuối |
|---|---|
| Vitest trọng tâm8tệp | PASS56/0FAIL/0SKIP, exit0 |
| Full `npm --silent test` | PASS244/0FAIL/0SKIP, exit0; giữ211ID+33mới |
| `npm --silent run lint -- --reporter=json` | PASS520tệp,0error/0warning/0info, exit0 |
| `npm --silent run typecheck` | PASS exit0 |
| `npm --silent run build` (Vite + tsc) | PASS exit0, còn cảnh báo chunk>500kB |
| Probe độc lập674/676 sau tích hợp | PASS11 và PASS8,0FAIL/0SKIP, exit0 |
| Bundle/template guards sau build | PASS11/0FAIL/0SKIP, exit0 |
| Scope/hash và source UTF-8 không BOM/LF | PASS theo source-integrity.json |

Các test mới dùng API client/component thật với port tổng hợp: xác nhận con
người, hash/key/retry không đổi, stale/expired/403, pending receipt sau reload,
scope/logout, role/editor/owner, unknown metrics, readiness không inference,
upload staged/mode/key, approved-only và bản cũ được giữ đến server completed.

Lượt kiểm tra đầu có7ca FAIL do fixture jsdom thiếu matchMedia; bổ sung đúng API
trình duyệt vào fixture, không sửa assertion để che lỗi. Typecheck đầu phát
hiện2link thiếu pageSize và1import thừa khi tách receipt; đã sửa, các gate cuối
đều đạt. Full suite chỉ chạy một lần sau batch ổn định.

## Kiểm tra hình ảnh

Đã dùng trình duyệt Codex trên fixture loopback riêng, render component/CSS
thật với API/auth/role tổng hợp, không kết nối backend/model/corpus thật:

- [Vận hành desktop sáng](../../../storage/artifacts/context678-fe-lifecycle/ops-desktop-light.png).
- [Vận hành khung390px tối](../../../storage/artifacts/context678-fe-lifecycle/ops-mobile-dark.png).
- [Thùng rác390px tối](../../../storage/artifacts/context678-fe-lifecycle/trash-mobile-dark.png).
- [Dialog desktop tối](../../../storage/artifacts/context678-fe-lifecycle/action-desktop-dark.png).
- [Dialog390px sáng](../../../storage/artifacts/context678-fe-lifecycle/action-mobile-light.png).
- [Chọn bản thay thế desktop sáng](../../../storage/artifacts/context678-fe-lifecycle/replacement-desktop-light.png).

Các view quan sát giữ nội dung/controls trong khung, dialog mobile có footer
truy cập được. Đây là spot-check bố cục, không phải ma trận mọi kích thước/trạng
thái hay browser E2E auth/navigation thật. Cuộn iframe qua AX có lỗi công cụ;
không ghi PASS cho phần cuộn đó. Tab QA và helper Node riêng đã đóng/dừng;
không restart API/worker hoặc dev server của người dùng.

## Giới hạn

Chưa smoke FE→BE/SSO/AI thật, không đánh giá semantic/RAG quality. Quy trình
thay thế dùng các màn OCR/Compiler/duyệt hiện hữu, không tự chạy toàn pipeline
khi upload. Thay từng compiled document theo khả năng BE; shared-source có
thể bị chặn và hiển thị lỗi. Không thêm evaluation/backup UI ngoài nhóm2–4.

[Hướng dẫn sử dụng](../../quy_trinh/34_frontend_vong_doi_thay_the_va_van_hanh.md).
Tài liệu mới/source dùng UTF-8/LF; các đoạn CRLF có sẵn trong hai index lớn được
giữ, chỉ chèn mốc mới để tránh đổi định dạng ngoài phạm vi.
