# Phiên 510 — Bản sạch, Studio và kiểm tra toàn vẹn

## Yêu cầu và phạm vi

Triển khai bước 1–3 đã đề xuất: chuẩn hóa giữ cấu trúc, nâng Studio đối chiếu và
kiểm tra trước duyệt. Dùng ingestion/clean-code/backend/frontend/admin-design
skills. Code theo batch, test trọng tâm ở cuối. Không thay nguồn/vector/config
đang xuất bản, không reparse thực, reset, migration, restart/deploy hoặc Git push.

## Nguyên nhân và thay đổi

- Cleaner nguồn trước có thể xóa dòng số, cắt ô thừa và đoán nối hàng. Thêm
  `normalization/clean_content.py`, nối vào `source_pages.py`; không sửa cleaner
  dùng ở các luồng legacy khác. Giữ số, null/replacement, ảnh, code, math, nesting,
  bảng và chú thích; chỉ reflow văn xuôi thận trọng/NFC/khoảng trắng. Không gán năm
  từ tên tệp. Bump EXTRACTION_VERSION để lần xử lý mới không reuse cleaner cũ.
- Manifest mới lưu text extraction và hash normalization; merge bản sửa giữ nguyên
  raw text và blocks/bbox nguồn, layout alignment stale. Nhãn trang không được tự
  tạo/đổi thứ tự/bỏ mất. Nguồn unknown không giả page 1.
- Studio API trước trả raw_text bằng canonical hiện tại. Nay raw độc lập hoặc ghi
  rõ không có ở legacy; không ảnh/bbox giả cho nguồn chưa xác minh pagination.
- Thêm preview chỉ đọc, đúng collection/binding/revision, quyền server, hash check,
  CPU worker boundary; không gọi model và không ghi DB. Kiểm tra numbers/negation/
  wording (gồm đơn vị/điều kiện có thể bị đổi), phần bảng/formula/footnote bị giảm,
  width/header/empty column/nhiều năm, encoding/missing footnote/fence, repeated
  margin và reading-order trùng. Cảnh báo toàn văn không bị gán trang/dòng cuối.
- Lưu content trước có thể auto ready/chuyển active source. Nay tạo revision chờ
  duyệt, actor từ session, reason/time/base revision/hash/output hash; không chuyển
  active source khi save. Duyệt bản hiệu đính mới cần actor và ghi chú đối chiếu.
  Existing guards index/fact/publication vẫn áp dụng; không tự publish.
- UI thêm nút Đối chiếu trong Studio, preview trước áp dụng, raw text khi có,
  diff cùng số dòng, click cảnh báo vào trang/dòng nếu xác minh được, reason và
  provenance người sửa. Source detail cũng gửi reason/hash. API client trước làm
  rơi structured-review flags: đã chuyển đủ tới Studio. Export giữ page markers
  thật thay vì separator vô danh. Markdown preview không ép mọi dòng thành hard break.

## File/phạm vi

Backend: module normalization mới; source_pages/source_extraction/source_artifact/
source_ingestion_service, schemas/router. Frontend: clean-content-review, utility
clean-content, Studio workspace/inspector, source detail, studio actions/mapper,
knowledge API và knowledge/studio types. Không tạo DB table hoặc framework mới.

Test mới `backend/tests/test_clean_content_510.py`, utility frontend; cập nhật
fixtures source-page-provenance/source-ingestion/source-pause theo contract mới,
giữ nguyên khẳng định nguồn bất biến và ngừng dùng. Không sửa 11 lỗi nền.

## Kiểm chứng thực chạy

Cwd backend: Python `.venv/Scripts/python.exe` (Python 3.12 theo pyproject).

- Ruff scoped exit0: 11 file backend sửa, sạch cuối batch.
- Focus đầu: 75 pass/4 fail do fixture manifest/audit contract thay đổi; cập nhật
  fixtures, không nới guard. Lần kế 93 pass/1 fail source-pause thiếu actor/reason;
  cập nhật fixture. Bản scope ổn: **94 pass**, 54.33s, exit0,
  `storage/clean510-final-focus.xml`.
- Full chạy **một lần**: `pytest -v --basetemp=storage/clean510-full
  --junitxml=storage/clean510-full.xml`, log `storage/clean510-full.txt`.
  **1906 pass / 11 fail / 17 skip**, 240.77s, exit1, tổng suite FAIL. Exact 11 IDs
  khớp `storage/focus507-full.xml` qua XML Compare-Object, 0 ID lỗi mới.
- Khi rà cuối, bổ sung guard giữ code thụt lề và warning wording/year, rồi sửa
  locator cảnh báo toàn văn thành unknown thay vì page cuối/line1. Regression
  cuối `test_clean_content_510.py + test_source_page_provenance.py`: **35 pass**,
  5.80s, exit0; `storage/clean510-handoff.xml`. Full nêu trên không chứa hai case
  parametrized thêm cuối; không tuyên bố đã full-run lại sau guard cuối.
- Cwd frontend: Node strip-types utility/studio-actions **8 pass**, exit0.
  Biome 10 file có formatter PASS; knowledge-api lint PASS với formatter tắt vì
  đoạn glossary cũ chưa format (đã hoàn tác formatting ngoài batch do Biome tạo).
  Production build + TypeScript exit0 sau sửa nullable locator, log
  `storage/clean510-frontend-final.txt`. Rà cuối giữ indentation khi tách trang ở
  backend và apply preview ở frontend; scope test/build xác nhận riêng, không
  chạy full backend lần thứ hai.
  Bàn giao: `storage/clean510-delivery.xml` **35 pass**, 6.08s; build cuối
  `storage/clean510-frontend-delivery.txt` và typecheck sau microcopy pagination
  được xác nhận riêng. Biome dùng `--line-ending=lf` theo AGENTS, không đổi cấu hình
  formatter CRLF của project; byte-check source/docs có phạm vi.
- Các command trong sandbox từng lỗi startup/no output; chỉ tiến trình Vite tự
  chạy được hủy, chạy lại scoped có quyền. Không restart backend/worker/stack.
- UI thật: tab local tới collection chuyển về sign-in; không đăng nhập hoặc
  thay dữ liệu, đã đóng tab. UI layout/tương tác thật desktop/mobile/dark
  **NOT RUN**, không coi build/helper tests là UI PASS.

Exact baseline IDs:

```text
tests.test_consulting_dispatcher::test_dispatch_admissions_with_export
tests.test_consulting_dispatcher::test_dispatch_regulations_with_export
tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint
tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api
tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled
tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled
tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit
tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback
tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies
tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims
tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts
```

## Giới hạn và bàn giao

Các phép kiểm là heuristic, không chứng nhận semantic/OCR correct; text sửa chỉ
phục vụ sau quy trình duyệt/vector/publication hiện có. Chưa có bộ fixture bao
phủ mọi kiểu PDF/layout/công thức. Không OCR/live inference hoặc benchmark RAG;
không kết luận tỷ lệ cải thiện chất lượng. Chuẩn hóa không khắc phục lỗi đã có
ngay trong tài liệu nguồn. Nguồn legacy thiếu text gốc vẫn cần ảnh/binary gốc,
không backfill suy đoán. Client cũ cần gửi lý do, nếu thiếu nhận 422.

Bước sau: người dùng đăng nhập để nghiệm thu Studio trên 3 tài liệu đại diện;
chỉ khi yêu cầu mới reparse/chọn revision/duyệt/nạp vector/publish. Các bước
chunking và version rollback sâu không được mở rộng thêm trong batch này.

[Quy trình sử dụng](../quy_trinh/11_ban_sach_va_duyet_noi_dung.md).
