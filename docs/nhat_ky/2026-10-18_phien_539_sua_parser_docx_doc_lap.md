# Phiên 539 — Triển khai parser DOCX độc lập

User cho phép sửa parser độc lập trong lúc batch RAG đang được triển khai ở file khác. Batch này không sửa projection, retrieval models/units, source_context, source_ingestion_service, unit_annotation hoặc app/modules/rag. Sửa xong mã rồi mới bổ sung/chạy test theo ngoại lệ thứ tự user yêu cầu. Không nạp lại, duyệt hoặc xuất bản tài liệu thử.

## Thay đổi

- `parsers/docx_evidence.py` mới đọc footnote/endnote parts và anchor theo ID OOXML, giữ locator/style paragraph và table/row/grid-column của anchor. ID riêng theo part, không gộp bằng text. Đích thiếu/trùng giữ nội dung+cờ. Body-row anchor buộc records để giữ identity hàng; header note giữ metadata phạm vi nguồn. Prose note chưa có anchor không được đoán scope/state.
- `parsers/base.py` thêm evidence nội bộ; `docling_office_parser.py` đọc original bytes, không sửa raw DoclingDocument. Complex note structures giữ text/locator và cờ đối soát.
- Ảnh embedded đối chiếu pixel identity duy nhất với tài nguyên nguồn, giữ bytes gốc, không tải external relationships. `source_extraction.py` chuyển bytes nội bộ; `qnu_docx_artifacts.py` đóng gói archive có hash qua StorageDriver trước MD/JSON. JSON chỉ có manifest/member/hash/path, không Base64. Dùng raw_evidence lifecycle hiện có để kiểm checksum/reuse/edit/cleanup đúng phạm vi, không sửa lifecycle đang vibe.
- `docling_structure.py` sinh note blocks và refs theo anchor duy nhất, map note theo native preview khi duy nhất; chưa chắc thì locator/null/cờ. Header gộp dọc không lặp cùng origin. Rich-cell text đã materialize trong bảng không xuất lặp thành prose; không bỏ hình hoặc nội dung chưa có trong cells.
- Mapping text/heading/list/code kiểm trọn dòng, không bỏ qua chữ số giữa tokens; tránh lấy prefix mục lục hoặc từ trong paragraph khác làm match. Giữ guard đa match/span/gap, không gán trang đầu. Repeated paragraph nhiều trang vẫn unresolved khi thiếu căn cứ phân biệt.
- Inventory gate notes/resources trước lưu: rơi note hoặc thiếu bytes/hash sai/storage lỗi không trả ready. Gate này chưa chứng nhận semantic coverage toàn tài liệu.
- Fingerprint mã mới `layout-v17-docx-source` nằm trong cột32 ký tự; chỉ áp lần xử lý tương lai, không thay config hoặc tự reparse.

## Kiểm chứng thực chạy

Cwd `D:\DuAnPhanMem\qnu-ai-platform\backend`, Python/Ruff từ backend\.venv.

Lượt focused đầu: **3failed/94passed/23subtests**, exit1. Một fixture mới thiếu sha256; hai regression do matcher chưa chấp nhận dấu chấm cuối câu. Đã sửa fixture và matcher, giữ assertions cũ. Sau sửa: **97passed/23subtests**, exit0,13.41s. Bổ sung inventory gate và2test xuyên extract_source; focused cuối:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_docx_source_evidence.py tests/test_qnu_docx_markdown.py tests/test_qnu_standard_regressions.py tests/test_qnu_header_and_cell_states.py tests/test_docling_office_parser.py tests/test_qnu_pdf_markdown.py tests/test_qnu_serving.py tests/test_qnu_standard_integration.py --basetemp=storage/parser539-final-focus --junitxml=storage/parser539-final-focus.xml --tb=short
```

**PASS168tests+23subtests**, exit0,15.55s. Có11test mới: real OOXML footnote/endnote/table scopes/shared/missing/ambiguous anchors, styles, merged-header identity, TOC/body, rich cells, hashed image archive/cleanup ownership/tamper/reuse/storage failure, dropped note inventory và extract_source wiring. Test PostgreSQL tích hợp hiện có dùng fixture outer rollback, không ghi giữ nguồn nghiệp vụ.

Scoped Ruff7files **PASS**, exit0; chỉ format hai file mới. Probe `.antigravity-bridge/validation/check_parser539_offline.py` **PASS**, exit0: DOCX thật, preview18trang đã lưu, parser/builder và storage fake trong RAM; load_document xác minh pair/hash. QA mới chỉ xuất cục bộ `backend/storage/parser539-offline/`, không cập nhật source trong DB.

Full suite chạy một lần sau batch mã ổn định:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=storage/parser539-full --junitxml=storage/parser539-full.xml
```

**FAIL:13failed/2137passed/17skipped/23subtests**, exit1,238.50s. Log `backend/storage/parser539-full.log`. Đối chiếu tự động exact test IDs với baseline533:13/13 trùng, new_failures=[], missing_baseline=[], exit0; `backend/storage/parser539-baseline-compare.json`. Không có failure ID mới nhưng full backend vẫn FAIL. Full working tree có mã RAG được sửa đồng thời bên ngoài, không dùng tổng số test để tự nghiệm thu riêng batch đó.

## So sánh file phức tạp

| Hành vi | Trước537 | Parser mới offline539 |
| --- | --- | --- |
| Nội dung footnote | 0/3 | 3/3 |
| Anchor liên kết nguồn | 0 | 3/3, không thiếu/trùng target |
| Trang note | Không có | 3,6,13 |
| Ảnh gốc trong gói chuẩn | Chưa đóng gói | Bytes nguyên gốc, manifest/hash kiểm bằng StorageDriver fake |
| Bảng/dòng thân bảng | 10/103 | 10/103 |
| Header gộp dọc | Nhóm/Nhóm/Nhóm… | Một cấp theo cùng origin; năm/metric/unit khác vẫn giữ |
| page_unresolved trên blocks | 130 | 9 |
| Mapping units | 91ambiguous/37out_of_order | 4ambiguous/0out_of_order;8absent/1unavailable còn unknown |
| Span qua trang | Có | Giữ3span7–8/10–11/15–16 |

Blocks299→233 do bỏ rich-cell text đã materialize lặp và thêm3notes; không phải mất66đoạn độc lập. Giữ103dòng; regression riêng giữ đủ hai paragraph của rich cell. Source inventory:3notes/3anchors/3linked,1image anchor/1resource. Hình vẫn có figure_content_unverified, không tự phiên âm hay xác nhận nội dung.

## Giới hạn

Chưa suy scope cho prose notes TB1/D-AM-0007/C-2027…; chưa phân loại semantic “Chưa công bố”/“Không áp dụng”. Giữ source style/raw cho bước tích hợp RAG/annotation sau, không vá từ điển/gán note gần nhất.9khối chưa rõ trang vẫn null/locator/cờ. Không khẳng định mọi DOCX đã map đúng.

Source537 `ks_rev_84c4950c9ce2` trong kho giữ bản cũ review_required; QA offline không có quyền duyệt/xuất bản. Không live OCR/render mới/model/chat benchmark/reparse/index/publish/restart/deploy/config/commit/push/stage/reset/dọn tracked. Mã RAG đồng thời bên ngoài giữ nguyên; checks chứng minh phạm vi parser và working tree tại lúc chạy, không tự nghiệm thu batch RAG.
