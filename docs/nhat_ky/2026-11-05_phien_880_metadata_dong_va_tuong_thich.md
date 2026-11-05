# Phiên 880 — Metadata động và tương thích dữ liệu cũ

Hoàn thiện bước 5–6 theo yêu cầu: UI chọn/chỉnh metadata từ đề xuất có nguồn, bộ lọc thuộc tính JSON theo danh mục thật, giữ luồng phát hành tự cập nhật chỉ mục của bước 1–2 và bổ sung kiểm chứng tương thích. Giữ các thay đổi từ những phiên trước trong checkout; không reset dữ liệu ứng dụng, restart, reindex, publish hoặc push.

## Thay đổi

- Đăng ký tài liệu đưa danh sách đề xuất và nguyên văn nguồn lên trước. Người dùng chọn từng đề xuất, chỉnh giá trị và trích đoạn trong cùng dẫn chứng, hoặc mở phần bổ sung thủ công. Server giữ target/citation gốc và kiểm lại giá trị với đúng nguồn đã ghim. Thay đổi có idempotency, hash và audit; đề xuất chưa chọn không tự áp dụng.
- Bộ lọc nhận attributes có kiểu văn bản/số/logic. Không ghép các trường của những annotation khác nhau. Mã văn bản 0012 không bằng số 12, true không bằng 1. Số 12 và 12.0 tương đương theo số JSON.
- API search-facets chỉ đọc, kiểm workspace/collection, publication hiện hành và manifest. Chỉ trả thuộc tính đã xác nhận, không dùng đề xuất hoặc tài liệu đã thu hồi. UI giới hạn hiển thị 50 trường × 50 giá trị, báo truncated và giữ lựa chọn cũ.
- Form trợ lý, hội thoại và tìm thử dùng chung bộ lọc động. Trợ lý mới dùng catalog scope và context_window=1; cấu hình trợ lý/hội thoại đã lưu giữ nguyên. Gộp scope cố định, lượt trước và lượt hiện tại theo từng thuộc tính; không làm rơi các khóa khác.
- Catalog resolver v2 dùng nhãn/giá trị thật, yêu cầu làm rõ khi kiểu/giá trị mơ hồ, chặn câu hỏi mâu thuẫn với phạm vi cố định. Lọc trước TopK cho dense và hybrid. Không tự nới scope khi không có kết quả, không đoán năm cho tài liệu cũ chưa có metadata.
- Giữ serialization filter cũ và request hash khi không gửi chỉnh sửa metadata. Không đổi nội dung nguồn hoặc backfill. Đường Quản trị chỉ mục nằm trong menu nâng cao dành cho người có quyền; người dùng thông thường chờ sẵn sàng sau phát hành.

## Phạm vi file

Backend: knowledge/metadata.py; index/query_scope.py, router.py, search.py; publication/schemas.py, service.py; compilation/supplement.py; conversations/service.py; assistants/schemas.py.

Frontend: metadata-proposal-item.tsx, register-document-dialog.tsx, retrieval-metadata-editor.tsx; rag/types.ts, schemas.ts, metadata-filter-fields.tsx, metadata-facet-fields.tsx; index requests/types/queries và các trang trợ lý, chat, answers/index, menu kho tri thức.

## Kiểm chứng thực chạy

Các lệnh backend từ root, dùng DB qnu_v1_test_* tạo/xóa bởi harness, QNU_TEST_WINDOWS_SELECTOR_LOOP=true và --frozen --extra dev. Provider trong test dùng loopback giả; PostgreSQL/Qdrant là hạ tầng thử. FE từ frontendV1. Không retry model để làm xanh kết quả.

- PASS, exit 0: 43 ca backend metadata, xác nhận đề xuất, scope/catalog và phát hành/index tự động qua run_isolated_tests.py. Receipt qnu_v1_test_478607007a2b451f: DB thử đã xóa, legacy sentinel giữ nguyên.
- PASS, exit 0: 101 ca mở rộng qua run_isolated_tests.py, gồm unit/integration dynamic_metadata_880, conversations_649, native_extraction_710, native_source_870, docx_fragments_872, table_context_769 và migration_baseline_661. Receipt qnu_v1_test_8c241a4daaf446c2: DB thử đã xóa, legacy sentinel giữ nguyên.
- PASS, exit 0: 59 ca Vitest trong dynamic-metadata-880, regression-677-index-scope, v1-rag-contracts-674, v1-assistants, rag-ui-674 và search-availability-878.
- PASS, exit 0: Biome 17 file triển khai và test mới; thêm check riêng regression-677-index-scope. npm run build gồm TypeScript đạt; còn cảnh báo Vite về import cấu hình native và chunk lớn.
- PASS, exit 0: Ruff trên các file backend sửa trong đợt này, git diff --check.
- FAIL, exit 1: toàn frontend trước bổ sung mock facet: 785 PASS / 11 FAIL. Chín ca regression-677 lỗi fixture thiếu useMetadataFacetsQuery đã bổ sung; lượt 59 ca sau đó đạt. Hai ca còn lại không sửa trong đợt này: v1-publication.test.ts::createDecisionPreview, draft, review-gate and history transport properly (assert /draft$ cũ, thực tế có ?group_by_source=true); ocr-review-ux-806.test.tsx::batches a selected page of 32 units and excludes the other page (timeout 5 giây). Chưa chạy lại toàn bộ frontend; không tuyên bố gate toàn FE đạt.
- FAIL, exit 1: bộ backend toàn diện chạy tests -q --tb=short -x dừng sau 78 PASS / 1 FAIL tại tests/integration/test_chat_shared_admission_751.py::test_real_redis_enforces_shared_limit_and_releases_own_leases. CACHE_NAMESPACE nhận qnu:v1:cache: trong khi test yêu cầu qnu:test:. Cùng ID/nguyên nhân đã ghi ở Context878. Những test còn lại chưa chạy; không tuyên bố full gate PASS. Receipt qnu_v1_test_3045c9d00457434c: DB thử đã xóa, legacy sentinel giữ nguyên, 430,67 giây.
- NOT RUN: benchmark model thật trên 53 câu, OCR upstream thật và kiểm tra hình ảnh giao diện bằng trình duyệt. Test loopback/fixture không chứng minh chất lượng model/corpus thực tế.

Test đầu đã bắt được lỗi nhập nhằng chuỗi/số và thiếu tương thích serialization; sửa trước lượt 43/101 ca. Test tích hợp đối chiếu cùng snapshot dense/hybrid với scope trước TopK, không match thì không gọi embedding rộng hơn, từ chối quyền sai và kiểm hash metadata. Có kiểm chỉnh đề xuất sai nguồn/giá trị, replay/idempotency và hội thoại gộp thuộc tính mà không mất phạm vi cố định.


## Lệnh kiểm chứng có thể chạy lại

Từ root, đặt QNU_TEST_WINDOWS_SELECTOR_LOOP=true trước lệnh harness:

~~~powershell
$env:QNU_TEST_WINDOWS_SELECTOR_LOOP='true'
uv run --project backendV1 --frozen --extra dev python backendV1/scripts/run_isolated_tests.py tests/unit/test_dynamic_metadata_880.py tests/integration/test_dynamic_metadata_880.py tests/integration/test_conversations_649.py tests/unit/test_native_extraction_710.py tests/unit/test_native_source_870.py tests/unit/test_docx_fragments_872.py tests/unit/test_table_context_769.py tests/unit/test_migration_baseline_661.py -q --tb=short -x
~~~

Từ frontendV1:

~~~powershell
npm exec -- vitest run tests/regression-677-index-scope.test.tsx tests/dynamic-metadata-880.test.tsx tests/v1-rag-contracts-674.test.ts tests/v1-assistants.test.ts tests/rag-ui-674.test.tsx tests/search-availability-878.test.tsx --reporter=dot
npm run build
~~~

Các lượt bộ tổng đã chạy một lần, không đổi assertion/bỏ cổng quyền để đạt màu xanh: backend dùng cùng harness với tests -q --tb=short -x; frontend dùng npm exec -- vitest run --reporter=dot. Log FE ở tmp/frontend-suite-880.log, log build ở tmp/frontend-build-880.log. Log/receipt backend nằm trong backendV1/storage/context636 theo tên DB thử ghi trên. Đây là tệp cục bộ, không chứa key hoặc nội dung corpus thật.

## Vận hành

Bước này không thêm migration; bước 1–2 có 0014_publication_index_sync. Nếu DB app chưa cập nhật, dừng dev rồi chạy ./make.ps1 v1-migrate, ./make.ps1 dev. Không clear/reset. Sau đăng ký, duyệt và phát hành, chờ Sẵn sàng cho trợ lý AI; không phải mở trang Tìm kiếm & Chỉ mục để tạo thủ công. Tài liệu cũ không tự có metadata mới: chỉ xác nhận ở phiên bản mới khi có căn cứ.

Hướng dẫn: [Quy trình chỉ mục](../quy_trinh/24_index_va_tim_kiem_dense_backendv1.md).
