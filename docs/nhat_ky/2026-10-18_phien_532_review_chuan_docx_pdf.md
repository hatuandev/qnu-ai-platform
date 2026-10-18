# Phiên 532 — Review DOCX/PDF theo QNU RAG Markdown Standard v1.0

Ngày: 2026-10-18. Phạm vi: đối chiếu `docs/quy_trinh/13_chuan_markdown_rag_v1.md` với builder DOCX/PDF, renderer/validator, MD/JSON pair và serving projection hiện tại. Chỉ review; không sửa mã ứng dụng, không reparse hoặc duyệt/xuất bản dữ liệu.

**Kết luận: CHANGES REQUESTED — chưa tuân thủ đầy đủ.** Khung trao đổi đã có, nhưng bốn finding dưới đây tái hiện được dù bộ test hiện có đều đạt.

## Những phần đã có bằng chứng đạt

- Renderer chung sinh schema `qnu-rag-markdown/1.0`, frontmatter, ID/revision do server cấp và cặp marker `rag:block`; literal marker/code fence được xử lý riêng.
- Có records/GFM, raw/state/normalized, column paths, merged origins; test hiện có giữ mã số 0 đầu, số 0, ô trống, header nhiều tầng, năm, source locator và revision identity.
- Pair loader kiểm checksum MD/JSON, danh tính binding/revision, source hash tham chiếu, parity ngữ nghĩa; PDF kiểm raw sidecar. Gói metadata không tự phê duyệt.
- PDF builder hiện tại đã giữ các hàng chưa đủ căn cứ header, native/OCR alternatives và source identity của symbol legend. Bảng nối trang chỉ là candidate cần đối soát.
- Đọc DB bằng transaction READ ONLY và storage read-only: cặp MD/JSON của sáu revision mới nhất thuộc `col_admissions` đều qua `verify_revision_pair`. Đây là toàn vẹn/parity, không phải chứng nhận nội dung nguồn đã đúng.

## F1 — P1: DOCX gán sai trang và vẫn báo aligned

`backend/app/modules/knowledge/parsers/docling_structure.py:363–366,409` chỉ map header/anchor cho bảng GFM; `qnu_projection.py:110` dùng location của cả bảng cho từng dòng. Fixture DOCX thật tạo bằng python-docx, parse bằng Docling: header + Alpha ở trang projection 1, Beta ở trang 2. Kết quả table chỉ có page 1, Beta serving unit cũng page 1; `page_mapping.status=aligned`, validator ok, không warning.

Đường đoạn văn còn dùng `map_text_to_page` (`docling_structure.py:58–80,699–706`) chỉ xét tối đa 12 token và điểm bắt đầu. Đoạn 20 token có 12 token đầu ở trang 1, phần còn lại ở trang 2 vẫn nhận duy nhất page 1 và aligned.

Lệch mục 4 và hợp đồng mapping tại mục 11: một khối trải trang phải giữ mọi vị trí; không thể chứng minh toàn khối bằng phần mở đầu. Cần map toàn đơn vị, map row GFM riêng hoặc chọn records; chưa chắc thì unknown/cờ thay vì gán trang header cho mọi dòng. Các page_ranges trong probe là projection đã biết để cô lập lỗi mapping, không phải phép render Word thật.

## F2 — P1: Bảng DOCX một cột bị biến toàn bộ dữ liệu thành note

`docling_structure.py:445–453` coi một hàng chỉ có một cell object và `col_span == num_cols` là note. Với bảng một cột thì mọi hàng bình thường đều thỏa điều kiện này.

Probe DOCX thật: header Item, hai dòng dữ liệu; một ô dài hơn 120 ký tự khiến chọn records. Kết quả types là `[table, note, note]`, **không có table_row**, trong khi validator vẫn ok. Nội dung còn dạng note nhưng mất vai trò hàng/field và không còn tham gia tập record của bảng.

Lệch mục 5–6: merge geometry không tự chứng minh vai trò chú thích. Cần giữ hàng/ô và role chưa xác định khi không có căn cứ; đặc biệt không phân loại một cột thành hàng gộp.

## F3 — P1: Projection tự áp mọi note con cho mọi dòng

`backend/app/modules/knowledge/normalization/qnu_projection.py:138–141` bổ sung tất cả note có cùng parent table vào refs của từng table_row, dù `context_refs` của nguồn rỗng.

Probe DOCX có hàng A, một hàng gộp ghi “Only applies to group A.”, rồi hàng B. Builder tạo note n001; row B không có explicit context. Projection vẫn tạo `qnu:n001` trong refs của row B. Cả builder validation và manifest validation đều đạt.

Lệch mục 4: quan hệ cha–con không chứng minh mọi điều kiện áp dụng cho mọi con. Đây là projection dùng chung DOCX/PDF và có thể mở rộng sai phạm vi điều kiện. Chỉ thêm phụ thuộc đã có bằng chứng scope/explicit refs; chưa rõ giữ candidate/cờ.

## F4 — P2: Validator chưa đủ để chứng nhận cấu trúc chuẩn

`backend/app/modules/knowledge/normalization/qnu_markdown.py:774–795,818–839` kiểm kiểu list/mapping nhưng chưa kiểm cấu trúc GFM hay yêu cầu thiếu vị trí phải có cờ.

Hai probe độc lập đều trả `ok=true`, errors/warnings rỗng:

1. `type=table`, `representation=gfm`, body là câu văn thường, không header/separator.
2. `type=text`, `source_locations=[]`, không quality flag.

Gọi `save_qnu_document` với GFM sai trên, mock hoàn toàn StorageDriver: trả **status ready, validation.ok true**, số lần ghi storage thật bằng 0. Projection có thể chặn tiếp GFM sai; finding này không khẳng định đã vượt được publication. Tuy nhiên artifact ready không còn bảo đảm gate cấu trúc như mục 5/10/11.1 quy định. Cần kiểm GFM, representation hỗ trợ, required metadata/source-location flags và trả finding có cấu trúc ngay tại validator.

## Tệp PDF đã lưu chưa được cập nhật theo code mới

| Revision mới nhất | Định dạng | Pair | Trạng thái DB | Số block / quality flags |
|---|---|---|---|---|
| ks_rev_0c1e98ac424b | DOCX | valid | ready, active source | 56 / 0 |
| ks_rev_1ba8a04f5ee4 | PDF | valid | review_required, chưa active | 83 / 27 |
| ks_rev_5ffe3662aee1 | PDF | valid | review_required, chưa active | 43 / 4 |
| ks_rev_4a8c28996473 | PDF | valid | review_required, chưa active | 89 / 10 |
| ks_rev_7b9dc0ce1a6a | PDF | valid | review_required, chưa active | 87 / 47 |
| ks_rev_8db62cd3f358 | PDF | valid | review_required, chưa active | 114 / 14 |

Đối chiếu raw checksum rồi dựng lại trong RAM: điểm sàn page 6/key42 và học phí page 2/key17, page 3/key43 đều có **0 table_row** trong model đã lưu, nhưng có **1 table_row** trong builder hiện tại. Không phải raw bị xóa: vai trò hàng đã bị xếp sai trong artifact cũ. Đây là giới hạn vận hành đã giữ từ phiên531; sửa code không tự thay revision cũ. Chưa reparse/approve/index/publish năm PDF này.

## Kiểm chứng và giới hạn

- Cwd `backend`: `.venv/Scripts/python.exe -m pytest -q tests/test_qnu_docx_markdown.py tests/test_qnu_pdf_markdown.py tests/test_pdf_review_regressions.py tests/test_qnu_serving.py tests/test_qnu_standard_integration.py --basetemp=storage/review532-focused --junitxml=storage/review532-focused.xml` → **122 passed, 23 subtests passed**, exit 0, 12.00 giây. Log `backend/storage/review532-focused.log`.
- Probes local `.antigravity-bridge/validation/review-standard-532-probes.py`: exit 0 là script thu quan sát thành công; **không phải PASS conformance**. Sáu quan sát lệch kỳ vọng được nhóm thành bốn finding ở trên. Fixture DOCX được tạo/parse trong RAM, không model/provider/network.
- `.antigravity-bridge/validation/review-standard-532-stored.py`: đọc DB/storage, verify sáu pair và rebuild raw trong RAM; exit 0. Không gọi luồng ghi reparse/approve/index.
- Mock `save_qnu_document` chứng minh F4 tại ranh giới artifact; không storage writes.
- Full backend và Ruff: **NOT RUN lại**, vì không đổi mã ứng dụng; full phiên531 vẫn là kết quả lịch sử **FAIL 13/2074pass/17skip/23subtest**, không chuyển thành current PASS.
- Chưa kiểm ảnh trực quan từng trang của sáu nguồn, live OCR, Word render mới, retrieval/chat hay chất lượng câu trả lời. Không tuyên bố nội dung OCR hoặc mọi nhánh chuẩn đã được nghiệm thu. Không commit/push/stage/reset/config/restart/dọn file.
