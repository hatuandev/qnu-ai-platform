# QNU AI Platform — Backend v1

Backend viết lại có chọn lọc, chạy ở cổng 8002. `backend/` giữ nguyên. Workspace là biên giới quyền của đơn vị theo ngoại lệ trong AGENTS.md; DB/Redis/storage có thể dùng chung hạ tầng nhưng quyền và ownership phải rõ ràng.

## Đã triển khai

- [Review trước duyệt](docs/publication-review-gate.md): con người xác nhận báo cáo
  đúng phiên bản và giải trình từng finding; model không tự duyệt/xuất bản.
- [Dọn dẫn xuất](docs/storage-cleanup.md): preview/xác nhận, giữ nguồn/raw và tệp
  còn tham chiếu; xóa có điều kiện trên Local/S3.
- [Recovery v1](docs/recovery.md): bundle mã hóa và restore vào đích mới, gồm dữ
  liệu v1, tệp và Qdrant. [Readiness](docs/readiness.md) báo dependency/worker/config
  thật và tách rõ kiểm tra inference/chất lượng.

- [Vận hành](docs/operations.md): theo dõi job/usage, preview phục hồi, backup bằng chứng có checksum và retention thủ công.
- [Hybrid và đánh giá](docs/hybrid-evaluation.md): PostgreSQL FTS + dense/RRF, rerank qua ModelOps, so sánh cùng snapshot/candidate. Dense vẫn là mặc định; chưa nghiệm thu cải thiện chất lượng.

- Workspace: tạo, liệt kê có phân trang, chi tiết, cập nhật/tạm dừng; thêm/đổi vai trò/thu hồi/khôi phục thành viên; audit.
- Xác thực: đăng nhập dev có mật khẩu và signing key cấu hình, không tự tạo admin từ request thiếu token. Token dev bị từ chối khi gate tắt hoặc production. SSO xác minh RS256/JWKS, issuer, audience, expiry; lỗi SSO trả lỗi hạ tầng. Chưa thử SSO QNU thật.
- ModelOps quản trị: provider/model/capability; thêm, xoay và thu hồi credential trong DB có mã hóa; đọc dạng che và audit.
- Platform admin cấp allowlist; admin workspace chỉ chọn default chat/embedding/rerank/OCR trong danh sách đã cấp. Catalog và public API phân giải model theo đúng workspace, không hợp quyền của các workspace khác.
- Quota theo tháng UTC và usage ledger nội bộ: reservation khóa đồng thời, request idempotent, usage/cost chưa biết giữ NULL. Chưa cấu hình quota của tháng thì không cho reserve; cấu hình limit=NULL mới là unlimited tường minh.
- Kho tri thức: collection theo workspace, upload tệp trực tiếp vào collection, nguồn logic + phiên bản file bất biến, tải lại đúng bytes gốc. Dedupe nội dung trong collection, idempotency theo `(workspace, actor, key)`, checksum kiểm lại khi tải. Nguồn dừng ở `stored`; trạng thái xử lý nằm ở bảng riêng.
- Xử lý PDF/DOCX: yêu cầu xử lý gắn với revision bất biến, job ARQ bền vững có lease và reconcile, render trang bằng PyMuPDF (DOCX qua fixed-layout), OCR từng trang bằng Nemotron lấy provider/model/credential từ ModelOps DB, lưu raw + canonical JSON + Markdown + manifest content-addressed, đọc lại qua 8 route có `ETag`. Run hoàn thành chỉ xác nhận xử lý kỹ thuật, không phê duyệt nội dung.

## Chạy ứng dụng

[Trợ lý và hội thoại](docs/assistants-conversations.md): cấu hình assistant gắn một
collection/model, lịch sử PostgreSQL theo owner, gửi lượt idempotent và câu hỏi nối
tiếp qua ModelOps. Dùng baseline hiện hành; chưa chia sẻ/public/streaming hoặc tool write.

[Hỏi đáp có trích dẫn](docs/rag-answers.md): search → evidence → model chat qua
ModelOps → kiểm citation/nguồn hiện hành → câu trả lời. API đồng bộ, chưa lưu hội thoại.

[Index và tìm kiếm dense](docs/dense-indexing.md): bản đang xuất bản → chunk giữ
nguồn/bảng → embedding ModelOps → Qdrant generation → API trả đoạn và citation.
Dùng baseline hiện hành; live BGE-M3/Redis/ARQ/Qdrant đã thử với dữ liệu mẫu riêng.

[Phiên bản và xuất bản](docs/compiled-publication.md): đăng ký output Compiler
thành tài liệu/phiên bản, duyệt, xuất bản/thay thế/thu hồi có preview và audit;
API đọc bản hiện hành kiểm lại nguồn/hash. Dùng baseline hiện hành.

[Compiler v1](docs/compiler-v1.md) đã nối runtime chat ModelOps: OCR đã hoàn tất
→ job biên soạn theo chủ đề → bản nháp JSON/Markdown có citation và bảng nguyên bản.
API có tạo job, danh sách, trạng thái, draft, Markdown và raw; dùng baseline hiện hành.

Từ `backendV1`, cài `uv sync --extra dev --frozen`. Tạo `.env` từ `.env.example`, đặt DATABASE_URL của môi trường được phép, SECRET_KEY ngẫu nhiên ít nhất 32 byte, PROVIDER_ENCRYPTION_KEY và cấu hình xác thực. Không lưu LLM API key vào `.env`; thêm qua API ModelOps.

Migration là thao tác chủ động: `uv run alembic upgrade head`, sau khi kiểm tra database và quyền sở hữu. Batch này chỉ áp migration trên DB test, chưa áp DB đang phục vụ. Chạy `uv run uvicorn qnu.main:app --host 127.0.0.1 --port 8002`; OpenAPI tại `/docs`.

Chuỗi gồm baseline **`0001_initial_schema`** đã gộp đầy đủ15revision phát triển cũ,
và **`0002_operational_readiness`** cho review acknowledgement/dọn dẫn xuất,
**`0003_rag_policy_metadata`** cho [RAG policy/metadata/context/kiểm chứng](docs/rag-policies.md).
Xem [migration và bản lưu lịch sử](docs/migrations.md); DB ở revision cũ cần chuyển
tiếp riêng, không tự `stamp head`. Các migration tiếp theo bắt đầu từ `0004_...`.

Dev login cần DEV_AUTH_ENABLED=true và DEV_ACCESS_PASSWORD. Production tắt dev gate và cấu hình SSO_ENABLED, SSO_AUTHORITY, SSO_AUDIENCE, SSO_JWKS_URL (endpoint HTTPS tin cậy của quản trị). Signing key và master encryption key là bí mật hạ tầng, không phải credential LLM. Không có cơ chế tự seed provider/key.

## Dữ liệu thử nghiệm Phòng Công tác sinh viên

Từ `backendV1`, dùng đúng cấu hình DB local đang chạy:

```powershell
# Nếu ứng dụng dùng .env ở gốc repo:
uv run --frozen --env-file ../.env python -X utf8 -m scripts.seed_student_affairs
# Nếu ứng dụng dùng backendV1/.env:
uv run --frozen python -X utf8 -m scripts.seed_student_affairs
```

Seed tạo workspace `cong-tac-sinh-vien`, một kho trống và ba membership:
`ctsv.admin` (quản trị workspace), `ctsv.editor` (biên tập), `ctsv.user` (thành viên).
Admin nền tảng `dev.admin` tiếp tục dùng dev gate hiện có. Chạy lại không tạo trùng,
không đổi vai trò/trạng thái hiện có, không đặt lại khóa và không cấp provider/model.
Chỉ chạy với dev gate được bật, PostgreSQL loopback; không dùng cho production.

Khóa ngẫu nhiên lưu riêng trong `backendV1/.local/ctsv-test-accounts.json`, bị Git bỏ qua;
registry xác thực chỉ lưu SHA-256 của khóa. Không chép khóa vào log hoặc tài liệu.
Trong frontendV1: đăng xuất → mở **Sử dụng Dev Access Key (kiểm thử cục bộ)** →
dán giá trị khóa tương ứng từ tệp local. Tên tài khoản được máy chủ xác định từ khóa;
quyền phòng ban vẫn lấy từ membership DB. Chọn **Tự đăng nhập bằng cấu hình local**
để trở lại admin nền tảng nếu cầu nối local đã được cấu hình.
Các tài khoản thử nghiệm không phải tài khoản SSO hay tài khoản nhân sự thực.

## Kiểm thử

[Review ngữ nghĩa sau Compiler](docs/compiler-review.md): API kiểm hai chiều
nguồn/bản nháp, báo cáo nguyên văn JSON/Markdown, model reviewer qua ModelOps.
Compiler mới mặc định tạo review tự động; API thủ công vẫn dùng riêng. Không tự duyệt.
Migration `0012_compiler_review`; kết quả lịch sử batch652 qua4nhóm **460PASS/0FAIL/0SKIP**.
Từ [workflow654](docs/compiler-workflow.md), cần thêm `0013_compiler_workflow` để ghim
text version, giao review bền vững và lưu bản sửa có preview thành run con.

[Rà soát và sửa văn bản hậu OCR](docs/ocr-text-review.md): API trả đoạn/ô đọc được,
gợi ý chính tả qua ModelOps và lưu phiên bản Markdown/JSON đồng bộ. Màn hình
chưa nối; Compiler chọn được bản sửa qua `text_versions`, bỏ trống/0 dùng gốc.
Các bảng và binding đã nằm trong `0001_initial_schema`.

[Kiểm chứng và theo dõi OCR](docs/ocr-acceptance.md): trace theo run/revision,
đọc raw nguyên bản qua API và báo cáo kỹ thuật tách riêng chất lượng OCR thật.

`uv run python scripts/run_isolated_tests.py` dùng credential DB cấu hình chỉ để tạo DB loopback tạm `qnu_v1_test_*`, áp migration rồi chạy toàn bộ test. Không sao chép row/key từ DB ứng dụng. Harness giữ sentinel legacy và tự dọn đúng DB do nó tạo. Log/XML/receipt trong `storage/context636/` được Git ignore. Có thể truyền đường dẫn test để chạy regression riêng.

Chạy pytest trực tiếp cho unit/contract được; integration/migration sẽ SKIP nếu chưa cấp TEST_DATABASE_URL hợp lệ. Không tính SKIP là PASS. Chỉ cấp TEST_DATABASE_URL vào DB sở hữu riêng theo namespace test; fixture xóa dữ liệu v1 trong DB đó giữa các ca.

## Ranh giới batch

[Vòng đời ngược tài liệu/chatbot](docs/resource-lifecycle.md): preview/xác nhận,
dừng/hủy, thùng rác/khôi phục, thay bản đã duyệt cùng index và dọn generation cũ.
Nguồn gốc/raw được giữ; các bảng vòng đời đã nằm trong `0001_initial_schema`.

Adapter OCR, chat và dense embedding OpenAI-compatible đã nối runtime ModelOps.
Compiler tạo bản nháp từ OCR đã ghim; publication và chỉ mục có lifecycle riêng.
Search dense trả đoạn/citation; API RAG answer trả lời một câu hỏi có nguồn.
Đã có hội thoại lưu bền vững với cửa sổ câu hỏi để làm rõ follow-up.
Chưa chia sẻ/public hoặc streaming. Hybrid/rerank có ở search/answer API;
cấu hình assistant hiện giữ dense. Giao diện các luồng tri thức/operations làm sau.
Đã nối [discovery/probe](docs/modelops-diagnostics.md), [nhóm khóa có cooldown, dự phòng trước tác vụ và registry](docs/modelops-resilience.md). Mặc định chưa bật pool/dự phòng; model đã ghim giữ nguyên. Streaming/Responses/tools chưa triển khai.
Đăng ký capability không đồng nghĩa model đã được kiểm định. Repository đã bỏ
theo nghiệp vụ mới.

Xem [API workspace/ModelOps](docs/workspaces-modelops.md), [API kho tri thức](docs/knowledge-collections.md), [luồng xử lý PDF/DOCX](docs/ocr-processing.md) và [báo cáo batch640](../docs/bao_cao/context640/REVIEW.md).
