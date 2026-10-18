# Phiên 534 — Review lại sau bản sửa bốn lỗi chuẩn DOCX/PDF

Ngày: 2026-10-18. Chỉ review, không sửa ứng dụng. HEAD quan sát khi đọc mã: `1b5ab27a` (`test: add comprehensive regression tests for QNU PDF and DOCX standards`); các file ứng dụng được review không có diff chưa commit tại đầu lượt. Không tạo commit hoặc thao tác Git ghi trong lượt này.

**Decision: CHANGES REQUESTED — còn hai finding P1.** Bốn ca của review532 vẫn qua regression hiện có, nhưng hai ca độc lập dưới đây còn vi phạm bảo toàn vai trò hàng và trạng thái ô của chuẩn.

## F1 — P1: DOCX tin nhãn header mặc định của Docling và mất vai trò dòng dữ liệu đầu

Vị trí ứng dụng: `backend/app/modules/knowledge/parsers/docling_structure.py:207–218,328,372`.

`_table_header_rows` coi `cell.column_header=True` là đủ để loại hàng khỏi data rows. Kiểm trực tiếp backend Docling đang cài (`backend/.venv/Lib/site-packages/docling/backend/msword_backend.py:3087,3100`) cho thấy nó gán **`column_header=row_idx == 0`**, không đối chiếu `w:tblHeader` cho các cell thông thường. Do đó đây là đề xuất theo vị trí của engine, không phải bằng chứng nguồn xác nhận vai trò header.

Probe tạo DOCX thật bằng python-docx, không `w:tblHeader`, gồm đúng hai dòng dữ liệu:

```text
Alpha | North
2     | South
```

Parse qua Docling và builder thật, kết quả:

- source_declares_header: false;
- representation: gfm;
- columns header_path: Alpha và North;
- source_data.header_rows: 1;
- derived_indexes data-row count: **1**, cần giữ **2** dòng khi chưa có bằng chứng vai trò;
- quality_flags: `[]`, validator `ok=true`.

Raw cells còn trong JSON, nhưng Alpha/North bị chuyển thành tên cột và không còn là record dữ liệu trong projection/đếm. Đây là cùng loại sai vai trò đã được chặn ở native PDF, còn đường DOCX. Cần phân biệt engine proposal với header-role evidence từ nguồn; thiếu căn cứ thì giữ mọi hàng, metadata đề xuất và cờ unresolved. Header thật có căn cứ phải có positive tests riêng; không vá bằng từ vựng tên cột hay hình thái nội dung của một fixture.

## F2 — P1: Nhánh GFM làm mất trạng thái ô mơ hồ, tạo fact và vượt chặn unresolved cells

Vị trí: `backend/app/modules/knowledge/normalization/qnu_projection.py:109,158–159,167–176`; liên quan `docling_structure.py:367–384` và guard duyệt tại `source_ingestion_service.py:784–789`.

Probe DOCX thật có **header khai báo rõ bằng `w:tblHeader`**, không dùng fixture F1 để suy luận header:

```text
Mã ngành | Tên ngành | Chỉ tiêu
7480101  | Alpha     | –
7480102  | Beta      | 0
```

Bảng nhỏ, không merge nên builder chọn GFM. `unresolved_cell_count` chỉ đếm `attributes.fields` của records; nhánh GFM không tạo trạng thái ô tương đương. Fact chỉ được bổ sung `field_state` khi `block.type == table_row`; fact GFM thiếu state rồi bộ lọc mặc định thiếu thành present.

Kết quả thực tế:

- representation: gfm; validation ok;
- unresolved_cell_count: **0**, issues `[]`;
- fact Chỉ tiêu/Alpha có value **`–`**, field_state null;
- fact Chỉ tiêu/Beta có value `0`, field_state null;
- gọi `_apply_review_decision` trên **binding/revision giả trong RAM** với actor/comment hợp lệ trả revision.status **ready**.

Không có DB/storage write, không test qua HTTP hay tuyên bố vượt kiểm quyền. Repro chứng minh guard ô chưa rõ không nhận ra marker của GFM dù mục 7/11.2 yêu cầu giữ ambiguous đến khi có chú giải/hiệu đính. Hành vi phải nhất quán giữa records và GFM: sinh state/provenance cho ô nội bộ hoặc chọn records khi cần; đếm/chặn đúng ô ambiguous và không mặc định fact thiếu state thành present. Giữ 0 là present và ô trống là blank, không cấm nhầm các giá trị hợp lệ.

## Kiểm chứng

- Cwd `backend`: `.venv/Scripts/python.exe -m pytest -q tests/test_qnu_standard_regressions.py tests/test_qnu_docx_markdown.py tests/test_qnu_pdf_markdown.py tests/test_qnu_serving.py tests/test_qnu_standard_integration.py tests/test_pdf_review_regressions.py tests/test_studio_revision_safety.py tests/test_document_revisions_lifecycle.py --basetemp=storage/review534-focused --junitxml=storage/review534-focused.xml` → **164 passed, 23 subtests passed**, exit 0, 15.28s. Log `backend/storage/review534-focused.log`.
- Cwd `backend`: `.venv/Scripts/ruff.exe check app/modules/knowledge/parsers/docling_structure.py app/modules/knowledge/normalization/qnu_markdown.py app/modules/knowledge/normalization/qnu_projection.py tests/test_qnu_standard_regressions.py tests/test_qnu_docx_markdown.py` → PASS, exit 0.
- Cwd root: `backend/.venv/Scripts/python.exe .antigravity-bridge/validation/review534-probes.py`, PYTHONPATH=backend → exit 0; đây là script thu quan sát, **không phải conformance PASS**. Hai hành vi sai ở trên tái hiện trong RAM bằng DOCX thật/Docling/builder/projection và hàm nghiệp vụ duyệt với đối tượng giả.
- Đọc trực tiếp mã backend Docling đang cài xác minh nguồn của nhãn column_header. Không gọi model/API hay cần suy đoán tài liệu thư viện bên ngoài.
- Full backend **NOT RUN lại** vì không sửa mã. Kết quả phiên533 là lịch sử: **FAIL13/2100pass/17skip/23subtest**, không chuyển thành current PASS.

Giới hạn: chưa visual QA/Word render mới/live OCR/retrieval/chat; không lặp đọc DB/corpus thật. Năm PDF cũ vẫn cần reparse/đối soát riêng theo bàn giao trước. Không sửa ứng dụng, không commit/push/stage/reset/reparse/approve/index/publish/restart/deploy/config/model changes. Chỉ thêm báo cáo và cập nhật memory/index.
