# Phiên640 — Luồng xử lý PDF/DOCX backendV1

Người dùng giao triển khai luồng xử lý tài liệu PDF/DOCX cho backendV1, dựa trên backend
cũ **có chọn lọc**, và yêu cầu kết quả kiểm chứng được chứ không chỉ kế hoạch. Đã đọc
`PROJECT_CONTEXT.md`, `architecture.md`, `module-boundaries.md`, `knowledge-collections.md`,
ownership/migration, báo cáo 639, quy trình 18, cùng Git/diff và source thật trước khi sửa.

Kết quả: upload PDF/DOCX → revision bất biến → yêu cầu xử lý trong cùng transaction →
dispatch sau commit → worker claim có lease → render trang → OCR từng trang qua ModelOps
runtime → raw + canonical JSON + Markdown + manifest content-addressed → 8 route đọc lại
có `ETag`. Trạng thái xử lý ở bảng riêng; nguồn vẫn `stored`.

Migration `0006_ocr_processing` thêm 3 bảng, composite FK theo workspace, partial unique
index một lượt hoạt động/revision, `downgrade()` từ chối; unique key `uq_kb_revision_scope`
thêm bằng 0006 chứ không sửa 0005 đã áp. Không migrate DB phục vụ.

Port chọn lọc: layout Nemotron (viết lại thuần, thêm `unsupported` thay vì đoán), adapter
payload/lỗi (viết lại có mapping phân biệt), bỏ `nemotron_runtime`, bỏ phần Word→text cũ,
không port `compilation_catalog`. Không import app legacy; 475 file `backend/app` giữ hash.

Hai lỗi thật gặp trong lúc kiểm chứng và đã sửa: `config_from_run` đọc `max_pages` sai
nhánh JSONB, và phát hiện trang trắng theo **tỷ lệ** mực khiến trang chỉ có dòng tiêu đề bị
bỏ OCR — nay đo bằng số pixel tối tuyệt đối trên toàn dòng mẫu.

Kiểm chứng: 14 ca OCR integration từ 11 FAIL → 0 FAIL; full integration 86PASS/1FAIL
(regression downgrade639 của 641) → sửa đúng bản chất → **full v1 249PASS/0FAIL/0SKIP**,
83,39s, exit0, DBtest `qnu_v1_test_73051dbf42c4467a` đã drop, sentinel legacy giữ.
95 ca mới (81 unit + 14 integration); baseline 154 → 249. Ruff PASS; OpenAPI 39 path/54
operation (+8). **Live Nemotron NOT RUN** — không có endpoint/credential thật; provider
loopback trong test là mock, không dùng để tuyên bố chất lượng OCR.

Không sửa code legacy, không migrate DB chính, không restart/deploy. Chưa có Compiler,
chunk, embedding, index, publication, RAG, frontend.

[Báo cáo/lệnh/giới hạn](../bao_cao/context640/REVIEW.md).
[Thiết kế luồng](../../backendV1/docs/ocr-processing.md).
