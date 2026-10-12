# Phiên #364 — Sửa OCR lỗi trang scan trắng

## Mục tiêu và phạm vi

Triển khai hướng phân biệt blank scan và OCR mất nội dung đã được người dùng đồng ý ở #363. Giữ nguyên pagination/Studio, không sửa Kho tài liệu, qnu-sso, ModelOps/khóa, RAG/DAG hoặc quy trình publish. Không reset/migration/restart/retry nguồn người dùng.

## Thay đổi và thuật toán

- `backend/app/modules/knowledge/services/blank_pages.py`: helper kiểm tra raster của trang gốc khi OCR rỗng. Render grayscale tối đa 144 DPI/cạnh 2400; không kết luận blank nếu phải giảm dưới 72 DPI hoặc còn native text. Ước lượng nền percentile 95 và Gaussian local background, phát hiện foreground tương phản, connected components 8-neighbor. Nền >=245; tối đa 128 pixel và density <=0,00006, component <=16 pixel/cạnh <=5; chỉ cho phép đốm sub-glyph thưa. Các ngưỡng là heuristic bảo thủ được kiểm tra bằng fixture/scan thật, không phải bảo đảm mọi chữ cực mờ hoặc scan nhiễu được phân loại hoàn hảo.
- `source_extraction.py`: sau validation success/page count, OCR rỗng chỉ được chấp nhận nếu raster có blank evidence. Trang có nội dung/không chắc vẫn `EMPTY_OCR_PAGE`; lưu text/blocks/tables rỗng, dimensions từ trang gốc, content_status blank/evidence. Không bỏ/dịch trang. Tài liệu hoàn toàn không text bị `EMPTY_EXTRACTED_TEXT` trước page markers. Adapter có thể từ chối tài liệu toàn rỗng bằng `OCR_CONTENT_EMPTY` sớm hơn; cả hai đều không tạo tri thức giả. Artifact version layout-v4 cho cả import/reparse.
- `source_pages.py`: giữ content_status/blank_detection trong manifest JSONB. Trang rỗng đi qua canonical page/chunker với đúng số trang và không sinh chunks; facts không có nội dung để trích xuất. Không đổi schema/migration/FE.
- Tests: mở rộng `test_source_layout_extraction.py` và thêm `test_blank_pages.py`; scan trắng giữa tài liệu, standard/layout_analysis, text/faint/figure rỗng vẫn fail, toàn trắng không usable; chữ mờ nhỏ, đường mảnh, nhiễu nhiều, nền tối, lớp chữ vô hình, oversized page. Tests lỗi provider/thiếu trang và native/DOCX/Studio trước đó vẫn đạt.
- Đồng bộ Quy trình 02, nhật ký/index, PROJECT_CONTEXT, snapshot và WORK_LOG.

## Kiểm chứng

- Regression trước sửa: sau chỉnh fixture DTO đúng schema, 3 fail/4 pass; hai ca blank scan fail đúng EMPTY_OCR_PAGE, ca toàn trắng chưa có mã lỗi nội dung rỗng.
- **51 focused tests đạt**: blank pages, source layout, page provenance, source ingestion và Studio revision safety. Ruff toàn backend và phạm vi thay đổi đều đạt; toàn backend có warning quyền đọc thư mục artifacts test cũ.
- **Live Paddle thật qua Tailscale, không mock**: PDF QĐ 2705 người dùng, standard pipeline qua ModelOps DB, 48 trang, 680 blocks, 70.962 ký tự Markdown, 71 ClauseBased chunks, engine paddleocr_vl, khoảng 19,92s. Trang 48 blank: background255, foreground94, component lớn nhất16; không có chunk trang48. Không kiểm định thủ công độ chính xác của tất cả nội dung 47 trang.
- Live probe chạy extraction/normalize/chunk trong bộ nhớ, không tạo/retry KnowledgeSourceRevision/batch hoặc nạp Qdrant/publish; OCR service ghi audit call như bình thường. Chưa browser/worker E2E của thao tác retry trên nguồn người dùng.
- Full suite đầu qua uv: 870 passed/13 failed/2 skipped/9 setup errors quyền Temp Windows. Lượt uv tiếp theo bị cache ngoài workspace denied; dùng đúng Python venv với basetemp mới thuộc backend/storage: **887 passed/13 failed/2 skipped**, không setup errors. 13 lỗi nền trùng nhóm đã ghi ở #360, không phải regression OCR; không tuyên bố full suite đạt.
- Không chạy Vite build vì không thay đổi FE. Kiểm tra UTF-8 và whitespace trên tệp thay đổi.

### 13 lỗi nền còn lại

`test_consulting_dispatcher` (2 export), `test_publishing_v2_cutover_and_gc` (gc_api_endpoint, canary_policy_get_and_update_api), `test_publishing_v2_decommissioning_and_system_gc` (direct_upload_blocked, direct_upload_allowed, system_gc_audit), `test_publishing_v2_e2e_canary` (api_routes_canary_and_rollback), `test_rag_data_truth_and_lifecycle` (reconciliation_detects_discrepancies), `test_tools` (fact_layer_lookup_tool_found), `test_trust_boundary_and_hitl` (auth_session_cookie_actor_claims), `test_universal_tools` (fact_layer_lookup_tool, dispatch_admissions_with_dynamic_facts). Nguyên nhân hiện thấy: thiếu facts/artifacts seed, API legacy nhận403, reconciliation contract và role AI.Admin/admin; giữ ngoài phạm vi sửa OCR.

## Bàn giao và bài học

Backend/worker cần nhận code mới trước khi bấm Thử lại mục lỗi hoặc Bóc tách lại. Không cần reset DB, migration hoặc tải lại tệp Repository. Không tự ghi đè revision đã xuất bản. Phân loại blank dựa trên ảnh gốc, không text-empty hay số trang; không sử dụng danh sách từ vựng vá lỗi. Nếu scan có nhiễu vượt ngưỡng, vẫn lỗi/cần kiểm tra thay vì bỏ nội dung im lặng.
