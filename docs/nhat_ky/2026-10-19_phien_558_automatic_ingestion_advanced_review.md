# Phiên558 — Automatic Document Ingestion và Advanced Review

Ngày 2026-10-19. Người dùng điều chỉnh Context558: ưu tiên upload DOCX/PDF → QNU Markdown/Structured JSON → kiểm tra chất lượng → nạp vector; Semantic Review là chức năng nâng cao. Giữ Context552–557, các thay đổi chưa commit và cơ chế bảo vệ. Không commit/push/deploy, không duyệt hoặc nạp nguồn thật.

## Audit và phương pháp

Đã đọc PROJECT_CONTEXT, Git/diff, chỉ dẫn repo và skills clean-code/backend/frontend/admin, ingestion/RAG theo phạm vi. Trước sửa luồng automatic, ghi audit/thiết kế trong [INGESTION_DIRECTION](../bao_cao/context558/INGESTION_DIRECTION.md), viết regression mới và chạy red (exit2/module chưa tồn tại). Legacy baseline70PASS trước triển khai. Luồng cũ ép warning/review cho bản chuẩn, đồng thời gộp pending semantic và QC nguồn thành một cờ chặn; UI có xác nhận lặp.

Chính sách automatic-content-v1 chỉ áp dụng upload/reparse mới. Certificate máy khóa source/revision/hash/pair/bảng/graph/facts/QC; core thay đổi thì chặn. AUTO_READY và READY_WITH_LIMITATIONS có thể chunk/index staging; NEEDS_ATTENTION vẫn chặn. Literal chưa diễn giải giữ raw/ambiguous, blank khác0, không sinh fact chắc chắn. Pending semantic proposal không thay dữ liệu có hiệu lực. Không certificate retroactive hoặc sửa nguồn thật.

Smart Approval được giữ ở Advanced Review, có actor/quyền/row lock, policy version, hash/revision/source verification, bulk audit, snapshot v3 và idempotency/concurrency; v1/v2 compatible. Fixture allowlist chỉ đúng provenance/payload đã đối soát, không từ điển parser hoặc tên file. Không giả18 quyết định thủ công. Publication vẫn riêng theo quyền/collection/revision/parity/CAS; embedding staging không đổi active_index/epoch.

## Mã thay đổi

- Backend: automatic_ingestion.py; qnu_serving và source_ingestion_service dùng nhánh automatic; source_artifact, model/schema readonly DTO; queue/chunk/derived_bundle kiểm tra source lần nữa.
- Backend nâng cao: smart_approval.py, smart_approval_service.py, policy fixture, router/schema, semantic_store và semantic_context_review.
- Frontend: source-detail-page; ingestion-readiness-panel, smart-approval-panel, semantic-review-preview; API/types và lời dẫn source-actions/clean-content. Main UI có trạng thái, Xem Markdown, Nạp vector; kỹ thuật/chứng cứ trong phần nâng cao.
- Tests mới: test_automatic_ingestion.py, test_smart_approval.py, test_smart_approval_api.py; frontend behavior/preview tests.

## Kiểm chứng thực tế

Kiểm tra cấu hình local trước chạy. Nguồn thật chỉ READ ONLY; PostgreSQL test sở hữu riêng, Storage local riêng, MinIO/Qdrant/Redis localhost:1, không migrate/seed production. Native DOCX/PDF và DB/Storage thật; adapter index/parity bên ngoài giả lập ở ranh giới test. Không coi đây là provider E2E.

| Kiểm tra | Kết quả |
|---|---|
| Focused backend 13 module | 265PASS +23subtest, exit0 |
| Automatic evidence cuối | 12PASS, exit0; full cuối bao phủ lại |
| Full cuối | **FAIL**: 2466PASS/18FAIL/17SKIP +23subtest, exit1 |
| So sánh Context557 lịch sử theo ID/cause | Không đổi ID chung/không mất ID/không lỗi mới;37ID mớiPASS;18failure message khớp |
| Frontend preview/behavior + vector/cache/clean | 28+13PASS, exit0 |
| Biome9 LF / Ruff17 / build TypeScript | PASS, exit0 |
| Fixture probes | 18issue/6ref/A03/A10/A11/A12 và3ô XMLPASS; không apply nguồn thật |
| UI live chỉ đọc | PASS trạng thái/Markdown/vectordisabled/Advanced; không action ghi |
| Final integrity | Mọi cột đúng revision/binding khớp trước phiên, sourcehash và pair hợp lệ |
| Real model/embedding/Qdrant E2E/humanSSO | NOT RUN |

Full chưa xanh vì18 lỗi nền (seed tables/data, endpoint test tắt, quyền/API, legacy schema/claim, tool fixtures), giữ nguyên từng ID và nguyên nhân so557. Hai full run trước steering bị dừng; không tínhPASS. Bảng ID và lệnh thật xem [VALIDATION_REPORT](../bao_cao/context558/VALIDATION_REPORT.md) và [REGRESSION_IDS](../bao_cao/context558/REGRESSION_IDS.md).

## Nguồn thật và cleanup

Context557 thực tế changes_requested/review_required; các cảnh báo nội dung độc lập còn, không tự biến ready sau khi xác minh18issue. Đối chiếu toàn bộ cột revision/binding với before snapshot và Storage chỉ đọc: không đổi nguồn/hash/proposal/active pointers. Context552–557 giữ nguyên, không gọi lại22packet hay sửa config/model, không index/publish/reparse nguồn thật.

DB test đã xóa bằng ownership nonce. Lệnh PowerShell xóa đệ quy đúng runtime bị bộ kiểm duyệt tự động chặn theo chính sách trước thực thi; **Storage còn2.226file/32.290.795byte**, không tắt bảo vệ/không thử shell khác. Giữ inventory/evidence riêng, không đụng các runtime cũ. Chưa hoàn tất cleanup Storage.

## Bàn giao

- [Nguyên nhân](../bao_cao/context558/ROOT_CAUSE_REPORT.md)
- [Thiết kế](../bao_cao/context558/SMART_APPROVAL_DESIGN.md)
- [Triển khai](../bao_cao/context558/IMPLEMENTATION_REPORT.md)
- [Kiểm chứng](../bao_cao/context558/VALIDATION_REPORT.md)
- [Hướng dẫn người dùng](../bao_cao/context558/USER_GUIDE.md)
- [Quy trình](../quy_trinh/smart_approval.md)

Không tự chuyển tài liệu cũ sang ready; cần thao tác revision mới hợp lệ khi người dùng chọn. Không commit/push/deploy. Hạn chế còn:18lỗi nền, provider E2E chưa chạy và Storage cleanup bị policy chặn.
