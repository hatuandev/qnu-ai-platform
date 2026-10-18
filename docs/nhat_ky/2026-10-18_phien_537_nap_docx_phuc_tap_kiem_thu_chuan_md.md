# Phiên 537 — Nạp DOCX phức tạp để kiểm thử chuẩn Markdown

Đã nạp đúng tệp người dùng chỉ định vào `col_admissions` qua Kho tài liệu và luồng import hiện có. Kết quả **thành công về lưu trữ và cú pháp chuẩn; chưa đạt đầy đủ độ trung thực nội dung**. Source revision dừng ở `review_required`, binding pending, không có index mới. Không duyệt hoặc xuất bản tài liệu mô phỏng vào RAG đang phục vụ.

## Phạm vi được phép và dữ liệu thực tế

- User yêu cầu nạp file đã chuyển vào `docs/tai_lieu/tuyen_sinh/tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).docx` để thử chuẩn hóa DOCX → MD theo chuẩn v1.0.
- SHA256 `58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274`, 102423 bytes. Repository trước nạp không có tài liệu cùng hash.
- Dùng actor thật do dependency server local trả về, xác minh authenticated và permission upload; không tự chế reviewer hoặc token.
- Đặt tên hiển thị có nhãn KIỂM THỬ MÔ PHỎNG. Không đổi nội dung nguồn, cấu hình, model/provider hoặc dữ liệu đang phục vụ.
- Mã RAG có thay đổi đồng thời từ ngoài lượt này; giữ nguyên. Hash mã tại inspect lưu trong `backend/storage/docx-trial537/before.json`; kết quả chỉ áp dụng cho lần nạp cụ thể, không khẳng định mọi process đang chạy đã nạp cùng mã.

## Identity và luồng xử lý

| Đối tượng | ID |
| --- | --- |
| Collection | col_admissions |
| Repository document | rep_doc_0dc36d3f92e6 |
| Repository revision | rev_27f61b496a0d |
| Import batch | imp_batch_1b46bc0381de |
| Import item | imp_item_a499ebe2fa5e |
| Knowledge binding | bnd_21c09bbc6ca0 |
| Source revision | ks_rev_84c4950c9ce2 |
| Job hoàn tất | job_cec126eb57d0 |

Luồng: `document_intake_service.intake_document` lưu bytes qua StorageDriver, idempotency theo hash → `create_import_batch` cho đúng một document, `dispatch=False` operator → worker task chuẩn dùng mã hiện tại → render Office qua Gotenberg, Docling và OCR adapter đang cấu hình → build/validate MD–JSON → projection → review_required. Không gọi các hàm duyệt, build staging index hoặc promote publication.

Lượt đầu `job_99bb0d87cd4d` thất bại `OCR_SERVICE_UNAVAILABLE` vì sandbox không nối được endpoint OCR đã cấu hình. Probe mặc định ConnectError; probe ngoài sandbox HTTP200. Đã retry cùng batch/item qua service, không tạo repository document/batch trùng, giữ job lỗi trong lịch sử. Lượt retry ngoài sandbox hoàn tất exit0. Không đổi endpoint hay dùng provider khác để vượt lỗi.

## Kết quả đối soát

- Cặp MD/JSON được đọc lại qua `verify_revision_pair`: **PASS**, identity/hash nguồn/snapshot khớp. Validator `ok=true`, 299 blocks, 0 errors/warnings của validator. Cờ chất lượng trong khối là cơ chế khác, không bị coi là không có chỉ vì validator không cảnh báo cú pháp.
- Render PDF thực tế **18 trang**. `source.page_count=null` vì không áp số trang vật lý cho DOCX; document_meta giữ render_page_count18, mapping partial và render hash riêng.
- 299 blocks: text162, section36, list15, table10, table_row74, figure1, code1.
- **10/10 bảng**, 4 records và6 GFM; đối chiếu số dòng thân bảng với grid raw/Word: **103/103 dòng**, lần lượt13/49/6/6/6/8/3/3/7/2. Bảng2 giữ45/45 mã NV-01…NV-45, không thiếu/trùng;49 dòng gồm45 nhiệm vụ và4 dòng nhóm/điều kiện.
- Header bảng1 giữ3 tầng và12 cột; bảng3 giữ6 dòng một cột, gồm0 và00027. Bảng4 giữ6 dòng, Alpha/North và2/South vẫn là dữ liệu, không bị nuốt thành header; dòng gộp có field_origins.
- Code giữ một khối fence Python14 dòng; công thức Q còn nguyên văn. Chưa chứng nhận mọi công thức đều được nhận dạng type formula.
- 392 draft facts trong artifact, **0 facts mới được materialize vào serving**.3 ô bất định còn giữ ambiguous; không sửa số hoặc diễn giải thay nguồn.

## Các khoảng hở phát hiện trên tài liệu thật

1. **Mất3/3 footnote trong MD/JSON**. Đọc `word/footnotes.xml` có3 note thật và3 anchor. Cả3 toàn văn không có trong các body chuẩn, cũng không có block note. Bản PDF render vẫn giữ note trên trang3/6/13. Đây là thiếu nội dung thật, không phải nguồn không có chú thích.
2. **Chưa dựng quan hệ chú thích/điều kiện**: cả299 blocks đều context_refs rỗng; các ghi chú TB1/D-AM-0007/C-2027/G-A/G-B và2 chú thích giống chữ còn là text, chưa có association có kiểu cho bảng/hàng/cột. Không được coi việc giữ câu chữ gần bảng là đã giữ đúng phạm vi cho RAG.
3. **Mapping trang partial**:130 cờ page_unresolved; stats unit_states ambiguous91, out_of_order37, absent1, unavailable1, spanning3, matched234. Đây là thất bại định vị, không đồng nghĩa130 khối mất nội dung; giữ locator/page null là trung thực. Cần cải thiện mapping trước nghiệm thu citation.
4. **Phân loại state còn thiếu nghĩa**: bảng5 giữ0=present và ô trống=blank đúng, nhưng CT-03 “Chưa công bố” và CT-04 “Không áp dụng” vẫn state present, chưa thành not_stated/not_applicable theo chính nguồn. CT-05 “–” vẫn ambiguous dù có chú giải; CT-06 “/” ambiguous là phù hợp vì nguồn chưa định nghĩa. Không vá bằng từ điển mới để giải quyết fixture.
5. **Hình chưa có nội dung dẫn xuất đầy đủ**: giữ figure reference và missing_content, chưa đưa ảnh vào artifact chuẩn. Ngoài ra header nhãn gộp dọc đang lặp path “Nhóm/Nhóm/Nhóm”, “Mã CT/Mã CT/Mã CT”, cần xử lý theo identity ô gộp nếu chuẩn hóa tiếp.

Cờ thực tế: page_unresolved130, spanning_row_needs_review5, table_header_unresolved1, missing_content1; artifact có thêm ambiguous_cell3. Cờ header của bảng không header là abstain có chủ đích, không được tự gán Alpha/North thành nhãn để gỡ cờ. Các dòng nhóm/ô gộp giữ unclassified để đối soát, không tự xóa dữ liệu.

Đã xem ảnh render trang13–15: footnote3 hiện rõ ở trang13; Bảng7/8 và hai note riêng nằm trên trang14. Dòng nhắc Bảng8 ở trang15 không chứng minh bảng thật trải qua hai trang. Không tuyên bố đã kiểm hình ảnh toàn bộ18 trang.

## Bằng chứng và bảo toàn serving

Artifacts audit cục bộ trong `backend/storage/docx-trial537/` (ignored):
- `standard.qnu-rag-v1.md` và `standard.qnu-doc-v1.json`: bản xuất từ StorageDriver sau khi pair verification.
- `preview.pdf`, `pages-13-15.png`: QA nội bộ.
- `before.json`, `state.json`, `audit.json`, `fidelity-summary.json`: identity/count/hash/đối soát, không chứa secret hoặc raw OCR Base64.

Lệnh operator từ `backend` dùng `.venv/Scripts/python.exe ../.antigravity-bridge/validation/docx_trial537.py` với action inspect/intake/import/status/retry/audit. Inspect/intake/status/retry/audit cuối exit0; import đầu exit1 do OCR network. Source standard validator/pair PASS; semantic fidelity **CHANGES REQUESTED**. Không chạy full Pytest/Ruff/build vì không sửa mã ứng dụng; không coi các check đó là PASS.

Trước–sau: config hash collection bằng nhau; active map vẫn chỉ `bnd_063df26142cb → ks_rev_0c1e98ac424b / idx_rev_c482a9e11451`; chunks56, materialized facts0; cuối busy jobs0. Binding thử nghiệm pending, active_index_revision_id=null. Năm PDF cũ và DOCX đang phục vụ không bị đổi.

Chỉ thêm script operator trong bridge ignored và nhật ký/memory có phạm vi; không sửa app, không commit/push/stage/reset/restart/deploy/reindex/approve/publish. Bước sau là sửa parser/provenance chung cho các khoảng hở trên, rồi reparse đúng bản thử khi được giao; chưa có quyền kết luận APPROVED từ việc nạp thành công.
