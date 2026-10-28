# Context702 — ModelOps tạo nhà cung cấp trước, thêm khóa và model sau

## Yêu cầu và phạm vi

Người dùng muốn luồng giống 9router: tạo OpenAI/ChatGPT, Gemini hoặc server AI QNU như một nhà cung cấp; sau đó vào chi tiết thêm API key, kiểm tra kết nối và thêm các model của nhà cung cấp. Triển khai cả backendV1 và frontendV1. Giữ thay đổi Context701 đã có trong index/memory; không chỉnh `.env`, credential hoặc DB đang phục vụ, không tự restart/migrate/push.

Áp dụng các skill QNU clean-code, backend, frontend và ModelOps; kiểm chứng theo bảng chung. Workspace V1 giữ biên giới quyền; không áp ngoại lệ này sang `backend/`.

## Nguyên nhân và phương pháp

Registry cũ gắn endpoint + một model trong mỗi bản ghi provider; UI buộc nhập model từ bước tạo. Tách nhà cung cấp cha và model con trong registry hiện có, bảo toàn ID model để không phá defaults, grants, binding trợ lý, usage và index đã ghim. Các container không được thực thi/cấp quyền như model.

Migration `0005_provider_connections` thêm `is_connection`, `parent_id`, `ProviderKey.model_ids`; gom model cũ theo endpoint, chuyển quyền sở hữu khóa/audit/lease về container nhưng giữ ID/ciphertext và phạm vi model cũ. Khóa mới tạo tại nhà cung cấp dùng chung; khóa cũ theo model không tự mở rộng. Khi chỉ có khóa cũ có phạm vi, thêm model mới trả lỗi hướng dẫn tạo khóa dùng chung.

Runtime, catalog, fallback, diagnostics và key pool tra cứu khóa theo owner + phạm vi; khóa cha trước con và credential. Tắt cha chặn model con. Xoay khóa giữ phạm vi; lease dùng fencing chung theo key để worker cũ không giải phóng lượt mới của model khác. Endpoint đã có model không được đổi riêng hoặc repoint âm thầm.

FE có thẻ/bảng và tìm kiếm nhà cung cấp, tạo kết nối không cần model/key, tự mở chi tiết. Chi tiết gồm kết nối, khóa, discovery và model đã thêm; model có trang riêng `/modelops/models/{id}` với capacity/probe/resilience. Deep link model cũ tiếp tục hoạt động. Form dùng TanStack Form và ResponsiveDialog hiện có. Key/model mutations làm mới cache liên quan; kết quả discovery cũ được đánh dấu cần thử lại theo cấu hình server.

Preset Gemini dùng [OpenAI compatibility chính thức của Google](https://ai.google.dev/gemini-api/docs/openai/). Adapter nối đúng `/v1beta/openai/models`, `/chat/completions`, `/embeddings` thay vì chèn thêm `/v1`. Không thêm native OAuth/web login hoặc chứng nhận model thật đã chạy.

## File chính

- `backendV1/alembic/versions/0005_provider_connections.py`; `qnu/platform/schema.py`.
- `backendV1/qnu/domains/modelops/connections/{router,schemas,service}.py`; `keys/scope.py`.
- ModelOps models/schemas, providers, keys, catalog, public_api, diagnostics và resilience; ba URL builder adapter; đăng ký router.
- `frontendV1/src/features/modelops/connections/*`; providers-page/detail/form, queries, diagnostics, keys/types, navigation và routes.
- Các test provider-first, migration parity/chain và recovery có dữ liệu sau chuyển provider.
- [Quy trình42](../quy_trinh/42_modelops_nha_cung_cap_va_model.md), hướng dẫn chạy V1 và tài liệu migration/ModelOps.

## Kiểm chứng thực chạy

Mọi lệnh test BE dùng harness DB loopback dùng một lần, môi trường con tối thiểu, Redis test DB15 với key riêng và chặn mạng ngoài. Không sao chép corpus hoặc credential người dùng. Cwd gốc repo, trừ FE ở `frontendV1`; lệnh Ruff dùng `uv --project backendV1`.

| Kiểm tra | Kết quả |
| --- | --- |
| Tái hiện trước triển khai API create-connection | 1 FAIL, 404 đúng nguyên nhân |
| Pool/diagnostics sau tích hợp owner | 40 PASS; trước sửa JSON-null/SQL-NULL có31FAIL, đã sửa `none_as_null=True` |
| Provider-first API/DB, disabled, grants, scope, URL Gemini, lease fencing | 10 PASS cuối batch, DB `qnu_v1_test_e48eb7488122455e` dọn |
| Migration chain/offline/parity/preservation cùng provider tests giai đoạn trước | 12 PASS, DB `qnu_v1_test_5579d31e235741fd` dọn |
| Negative diagnostics khi cha tắt | Trước sửa1FAIL vì200/thực hiện HTTP, sau sửa nằm trong10PASS |
| Negative thêm model mới với chỉ khóa legacy có phạm vi | Trước sửa1FAIL vì201, sau sửa nằm trong10PASS |
| Recovery Proactor | 4 PASS ban đầu (`qnu_v1_test_e228d1dd5e94463a`); bổ sung chuyển model cũ sang cha trước backup, chạy lại ca khôi phục toàn bộ1PASS (`qnu_v1_test_6181682ad5d04369`); DB đích/test được dọn |
| FE final `npm test -- --maxWorkers=2` | 411 PASS /44file, exit0; artifact `storage/artifacts/context702-provider-connections/final-fe-tests.log` |
| FE đầu với4worker | 410PASS/1FAIL timeout ca `evaluation caps the editable question list at twenty`; riêng30PASS và hai lượt full2worker đều411PASS. Không sửa assertion hoặc tăng timeout |
| `npm run build` cuối batch | PASS TypeScript + Vite; còn cảnh báo bundle lớn có sẵn |
| Scoped Ruff / Biome | PASS27file BE /17file FE, exit0 |
| Tài liệu / encoding / diff | UTF-8 không BOM kiểm56file;16link mới PASS, `git diff --check` PASS. Quét toàn các index lịch sử vẫn FAIL241link cũ, đối chiếu HEAD cũng241, delta0; không sửa ngoài phạm vi |
| Full BE Selector, tách recovery theo Proactor của Windows | **765 PASS /0FAIL/0SKIP**, exit0; 1834.23s, receipt `qnu_v1_test_41f2f5d5f2c44f9f` xác nhận DB đã dọn và sentinel giữ nguyên |

Full BE lần đầu bị gián đoạn khi phiên công cụ bị ngắt, không coi là PASS. Đã kiểm không còn kết nối và sentinel cũ trước dọn đúng hai DB thử `qnu_v1_test_c2a77496d6c34b94`, `qnu_v1_test_8cf0001dd6b146ee`; có `interrupted-cleanup.json`. Sau sửa hết batch, chạy lại full để lấy kết quả cuối.

## Giao diện và vận hành

Preview dùng API8014/FE3004 và dữ liệu giả trong DB riêng, không dùng API8002/FE3001 của người dùng. HTTP upstream của preview là MockTransport. Đã quan sát tạo nhà cung cấp → tự mở detail0model/0key; chọn preset QNU; thẻ/bảng → mở nhà cung cấp; discovery → thêm OCR từ danh sách → mở model; thêm model Rerank từ form mobile có toast thành công. Không gọi model thật.

Đã kiểm desktop mặc định1265×712 và mobile override390×844 (client width375 sau scrollbar): không tràn ngang trang; bảng khóa cuộn ngang trong khối. Form thêm model dùng drawer mobile, nút lưu/hủy nhìn được. Light/dark trên mobile đã kiểm; có ảnh trong `storage/artifacts/context702-provider-connections/`. Cuối lượt API browser phụ không còn truy cập được (`browser.user is unavailable`) nên thao tác xác nhận cuối/reset viewport/đóng tab không được xác nhận; không suy các thao tác đó đã hoàn tất. Có ảnh trước lúc API browser không còn truy cập được và toast/đường dẫn thành công.

DB preview `qnu_v1_test_3b7ae94216f94472` đã dọn, sentinel giữ nguyên; tiến trình riêng đã dừng, temporary test đã xóa sau đối chiếu đúng bytes. Không restart phiên người dùng. Cần người vận hành dừng phiên V1 cũ, giữ backup, chạy `./make.ps1 v1-migrate`, rồi `./make.ps1 v1-dev` để dùng schema/API mới.

## Giới hạn

- Chưa áp migration vào DB đang phục vụ; chưa chạy live inference với khóa thật trên OpenAI/Gemini/server QNU trong batch này.
- Server không có `/models` có thể thêm ID thủ công; chạy thử từng capability và khai báo capacity có căn cứ trước cấp workspace.
- Chuyển dữ liệu online giữ phạm vi khóa cũ; tạo khóa dùng chung là thao tác quản trị tường minh tại UI. Không mở rộng quyền workspace khi thêm nhà cung cấp/model.
