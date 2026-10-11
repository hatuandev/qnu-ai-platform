# Phiên #354 — Trải nghiệm Studio cũ, nạp vector bằng cơ chế ADR-012

## Mục tiêu và ranh giới

Người dùng chấp thuận giữ Studio hai cột: ảnh/khung scan bên trái, Markdown và thực thể bên phải; làm rõ bước nạp Markdown vào vector. Không quay lại backend legacy, không sửa qnu-sso, không reset/migration, không sửa/xuất bản hai nguồn thật trong col_admissions.

## Thay đổi

- Studio có Lưu Markdown, Duyệt nếu cần, Nạp vector; nội dung chưa lưu không được nạp/xuất bản. Canvas/Markdown/Thực thể/Vùng nhận diện tiếp tục dùng snapshot ADR-012.
- Bảng nguồn tách MD sẵn sàng khỏi vector đã nạp/xuất bản. Cho phép chọn từng nguồn hoặc nhiều nguồn. Toolbar kỹ thuật/chỉ mục/khôi phục chuyển vào Nâng cao; không nhập raw Provider ID hoặc model name.
- Dialog chọn model/provider từ ModelOps, tạo/reuse generation và xếp hàng đúng các nguồn được chọn. Xuất bản vẫn riêng, áp dụng toàn kho, chỉ bật khi mọi nguồn hiện hành đã có index hợp lệ.
- Header đếm nguồn thật, index đang phục vụ và chunks đang phục vụ thay vì số nhóm legacy. Thiếu dữ liệu hiển thị dấu —, không giả là kho trống.
- API POST/GET vector-load: khóa collection/nguồn, kiểm tra tenant/workspace, revision hiện hành và ready, dedupe job đang chờ; persist trước khi dispatch ARQ, Redis offline giữ pending để reconciler xử lý.
- Worker pin source_revision_id và generation_id, chỉ gọi chunk-set/vector generation mới. Markdown thay đổi trước khi worker chạy trả SOURCE_REVISION_CHANGED, không index nhầm. Hủy job reuse không đánh failed index active đang phục vụ.
- State query explicit JOIN binding_id (hai FK giữa binding/index khiến JOIN suy đoán bị ambiguous). Loại indices legacy không có generation; ưu tiên index đang active để không mất KPI khi tồn tại index lỗi mới hơn.
- ModelOps defaults GET chuyển tiếp auth headers cho phiên SSO; không thêm hoặc in khóa API.

## Tệp thay đổi trong phiên

Backend: knowledge/schemas.py, router.py, services/binding_service.py, vector_generation_service.py, vector_load_service.py; workers/tasks.py; tests/test_vector_load_workflow.py; scripts/verify_vector_load_354_live.py.

Frontend: types/knowledge.ts, services/knowledge-api.ts, modelops-api.ts; collection-header.tsx, tabs/collection-bindings-tab.tsx, ocr/document-studio-workspace.tsx; features/knowledge/components/use-vector-workflow.ts, vector-load-controls.tsx; utils/vector-workflow.ts và vector-workflow.test.ts.

## Kiểm thử

- Regression red → green: worker nhận revision khác trước khi chunk; SQL JOIN ambiguous tái hiện rồi explicit JOIN sửa.
- 25 backend focused tests đạt (vector load, generation/chunk sets, workers). Phủ scope, source chưa duyệt, revision đổi, lựa chọn trùng, pending retry, offline broker, new-vs-legacy task, cancel giữ active index, compile SQL PostgreSQL thật.
- 3 frontend tests đạt: MD-ready không đồng nghĩa vector-ready; đúng revision/generation; pending/error và publish đủ nguồn. Bun có cảnh báo EBADFD đọc tsconfig trong sandbox nhưng tests exit0; không coi đây là browser E2E.
- Ruff toàn backend đạt. Full suite: 843 passed, 13 failed, 2 skipped; cùng nhóm lỗi cũ Auth/RBAC, publishing legacy, facts live/consulting/export, reconciliation. Basetemp riêng loại 5 setup errors quyền temp ở lần chạy đầu; không tuyên bố full suite xanh.
- FE targeted Biome đạt, Vite + TypeScript build đạt.
- Browser thật: chọn 2 nguồn fixture, dialog đúng 2 nguồn/model generation, publish bị disable; lỗi thiếu key hiển thị trên đúng nguồn, nguồn còn lại vẫn Chưa nạp vector. Studio tài liệu thật hiển thị 48 trang/680 khối, scan trái và Markdown/Thực thể phải, nút Nạp vector.

## Kiểm thử live và giới hạn

Tạo kho fixture độc lập col_d26b26e378b6 và hai DOCX có nhãn FIXTURE. Repository intake → snapshot import → DOCX parse/normalize hoàn tất 2/2. ARQ nhận selected-source job, gọi generation vg_a97d67e2e0b6/model bge-m3 phân giải từ DB. Embedding **thất bại thật**: provider prov_rtx5090_vllm không có legacy key và không có hàng ProviderApiKey. Không dùng key cũ từ chat, không fake embedding, không bỏ qua credential validation. API state sau sửa trả HTTP200 với failed job/index và lỗi tương ứng. Chưa xác minh thành công Qdrant/parity/publish live; cần người dùng nhập khóa hiện hành trong ModelOps rồi chạy lại script fixture.

Không xuất bản col_admissions hoặc fixture; không thay đổi hai tài liệu thật. Kho fixture và hai tài liệu fixture được giữ để kiểm tra/retry, không tự xóa vĩnh viễn. Script retry nhận ID kho fixture và reuse nguồn đã có.

Worker được restart riêng khi DB có 0 running jobs; PID parent mới 28700, logs backend/storage/worker_logs. Frontend dev cổng3000 bị tắt trong lúc kiểm tra, đã mở lại bằng process nền Hidden, PID24248. Backend8001 không restart. Không chạy worker sandbox (Tailscale).

Ảnh kết quả: backend/storage/e2e_fixtures/354/studio-vector-workflow.png (runtime, không commit). Nhật ký không chứa secret.

## Bài học

MD-ready, vector-ready và serving là ba trạng thái độc lập. Unit mocks không thay thế compile SQL hay kiểm tra live worker; test thực tế tìm được JOIN ambiguous và cấu hình credential thiếu. Giữ publish là hành động có chủ ý, dùng parity/CAS và snapshot đang phục vụ hiện có.
