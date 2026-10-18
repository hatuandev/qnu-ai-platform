# Phiên 538 — Nguyên nhân thiếu nội dung khi chuẩn hóa DOCX

Kết luận: lỗi được tái hiện ở parser và adapter chuyển cấu trúc, trước bước trả lời RAG. Không có bằng chứng file Word bị hỏng. Ba footnote có thật trong OOXML/PDF nhưng đã mất ở cây Docling; các chú thích còn chữ nhưng chưa thành liên kết; state chỉ phân loại biểu diễn; định vị trang dựa trên chuỗi lặp và con trỏ chung. Validator chuẩn chỉ kiểm cấu trúc của đầu vào đã bị thiếu, nên vẫn có thể PASS.

## Phạm vi và phương pháp

- User yêu cầu tìm hiểu và phân tích nguyên nhân, chưa giao sửa. Giữ nguyên mọi thay đổi mã đang diễn ra ngoài lượt này; không sửa app, reparse, nạp lại hay cập nhật DB.
- Đọc Git/memory và nguồn thực tế. Tài liệu và artifact dùng đúng hash phiên537 `58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274`, source revision `ks_rev_84c4950c9ce2`.
- Probe offline `.antigravity-bridge/validation/analyze_docx538.py`: đọc DOCX, chạy riêng `DoclingOfficeParser._parse_sync`, đọc PDF preview18trang đã lưu, tái dựng alignment bằng cùng hàm layout và builder. Không gọi OCR/provider, DB, StorageDriver, index hoặc publication.
- Backend cài thực tế **docling-slim2.128.0**. Không suy kết luận về phiên bản upstream khác. Kết quả ở `backend/storage/docx-trial537/root-cause538.json`, ignored.
- Probe thành công exit0; stats tái dựng **bằng đúng** stats artifact537, gồm matched234/ambiguous91/out_of_order37/absent1/spanning3/unavailable1. Không dùng full suite để thay việc truy nguyên này.

## 1. Footnote mất ngay tại Docling

Chuỗi kiểm chứng của cả3 note: `word/footnotes.xml` có nội dung và document.xml có anchor → PDF render còn nội dung tại trang3/6/13 → Docling iterate_items không có → Docling Markdown không có → QNU blocks không có.

Backend cài đặt `backend/.venv/Lib/site-packages/docling/backend/msword_backend.py:662`–684 convert bằng `_walk_linear(self.docx_obj.element.body)`, thêm header/footer và comments. Đường này không materialize3footnote trong package vào cây item; phần paragraph/run lấy text, không resolve anchor footnote sang part riêng. Đây là bằng chứng của bản cài và file đang thử, không phải suy từ việc JSON thiếu.

Adapter `backend/app/modules/knowledge/parsers/docling_office_parser.py:127` lấy `convert()` và `export_to_markdown()`; không bổ sung notes từ part OOXML. Builder `docling_structure.py:499` chỉ duyệt iterate_items, nên không thể khôi phục đối tượng chưa có trong cây. Nhánh note ở dòng652 chỉ có tác dụng nếu upstream đã gán label caption/footnote; probe không có label đó.

Hướng khắc phục: adapter đọc note part/relationship bằng ID nguồn, giữ nội dung và anchor gốc, cấp locator cho note và reference từ block chứa anchor. Kiểm cả note lặp nhiều reference và thiếu target; không nối note theo nội dung giống chữ hay số hiển thị. Không sửa trực tiếp site-packages, không gọi OCR/LLM để đoán lại phần OOXML đọc được.

## 2. Chú thích còn chữ nhưng chưa có association

Probe xác minh các đoạn TB1/D-AM-0007/C-2027/G-A/G-B và hai note giống chữ đều có trong Docling, label **text**. Trong cây có text169, section_header36, list_item53, table10, picture1, code1; không có caption/footnote label.

`docling_structure.py:652` giữ chúng thành text. Toàn builder không có bước thiết lập context_refs; model mặc định context_refs=[] và kết quả299block đều rỗng. Quan hệ parent_id chỉ theo section, không chứng minh ghi chú áp dụng cho mọi hàng/cột trong section. `source_links.build_context_graph` của nhánh chuẩn chỉ đóng các refs đã có, không tự đoán association, nên downstream không có scope note để đóng gói.

Cần phân biệt đây là **thiếu annotation trong quá trình tạo chuẩn**, khác lỗi reviewed_fact làm rơi dependency đã tồn tại ở review536. Sửa downstream không tự tạo được các dependency mà DOCX builder chưa sinh.

Hướng khắc phục: giữ Word style, caption/reference/bookmark/anchor và vị trí nguồn cần thiết để xác lập vai trò/đích. Cho phép proposal có căn cứ và review cho phạm vi chưa xác minh. Note toàn bảng, riêng dòng, riêng năm/cột và nhóm phải tách. Không coi paragraph bắt đầu bằng một từ khóa viết tay, hay paragraph gần nhất, là bằng chứng đủ để gán scope.

## 3. State đang dựa vào ký hiệu, chưa hiểu phạm vi nguồn

Probe gọi đúng `qnu_markdown.cell_state` ở dòng42:

| Raw | Kết quả thực tế |
| --- | --- |
| 0 | present |
| Chuỗi rỗng | blank |
| Chưa công bố | present |
| Không áp dụng | present |
| – | ambiguous |
| / | ambiguous |

Hàm chỉ nhận một chuỗi, không nhận header, chú giải hoặc basis quote. Ngoài blank và tập marker hiện có, mọi chuỗi khác thành present. Records gọi hàm ở `docling_structure.py:393`–398; GFM gọi lại tại projection vì Markdown bảng không tự mang field state chi tiết. Vì vậy cùng lỗi có thể xuất hiện ở cả hai representation.

CT-03/CT-04 là nhãn trạng thái của giá trị theo chính bảng5, nhưng chỉ được giữ như text có nội dung. CT-05 có chú giải song vì mục2 chưa dựng quan hệ nên chưa dùng được để phân loại; CT-06 chưa có định nghĩa thì ambiguous là đúng. Raw không mất và0không bị đổi; lỗi nằm ở diễn giải state có kiểu. Không suy rằng mọi ô văn bản “Không áp dụng” ở bất kỳ cột mô tả nào đều phải là state not_applicable.

Hướng khắc phục: giữ classification proposal cùng quote/phạm vi cho đúng field, cơ chế review và state riêng; thiếu căn cứ không đoán. Không mở rộng từ điển để làm mỗi câu fixture thành state. Test cần đi từ DOCX gốc; test hiện có `test_explicit_record_state_is_not_overwritten_by_gfm_marker_defaults` tự tạo sẵn not_applicable/context_refs chỉ chứng minh downstream bảo toàn, không chứng minh parser suy được chúng từ Word.

## 4. Định vị trang bị ảnh hưởng bởi text lặp và khác thứ tự biểu diễn

`source_extraction.align_office_markdown:209` dùng SequenceMatcher của tokens Docling và PDF layout để chia các khoảng trang; kiểm tỷ lệ khớp90% theo tokens Docling. `docling_structure.map_unit_to_page:74` sau đó tìm toàn bộ text unit trong projection, kiểm một chữ ký trang duy nhất trên toàn document và chỉ chấp nhận match phía sau cursor chung.

Tái hiện đúng91ambiguous và37out_of_order, không dùng OCR:
- “HỘI ĐỒNG QUẢN LÝ ĐÀO TẠO” có3match ở trang1/8/12; “KẾ HOẠCH” có23match; mục lục và heading lặp giữa trang2và thân bài. Hàm từ chối nếu match trải nhiều chữ ký trang, dù source occurrence có thể phân biệt được bằng anchor.
- Một số mục lục có duy nhất match ở trang2 nhưng đã trước cursor, nên bị out_of_order.
- Header ô/bảng trong cây Docling và projection span-aware có thứ tự/biểu diễn khác. Mẫu header quay lại vị trí trước cursor ở trang6; một hàng header raw không có chuỗi liên tục tương ứng sau flatten nên absent. Không phải mất mọi ô của hàng đó.
- Unavailable1 là nội dung caption rỗng của picture.
- Ba đơn vị spanning được map đúng nhiều trang: đoạn đối soát7–8, row NV-30 trang10–11 và đoạn xếp loại15–16. Cơ chế giữ span nhiều trang đã hoạt động; không nên thay bằng gán trang đầu.

130cờ page_unresolved không phải130đoạn mất chữ. Chúng gồm các block/list/table phụ thuộc những unit không định vị được. Giữ null+locator hiện tại là cách abstain trung thực, nhưng chưa đủ để nghiệm thu citation.

Hướng khắc phục: mapping theo source occurrence/order/identity, phân biệt TOC và body, header origin/merge và object container; ánh xạ nhiều đoạn/gap khi cần. Không chọn match đầu tiên, hạ threshold hoặc bỏ guard để giảm số cờ. Đối chiếu được cả độ phủ và đúng vị trí, không chỉ tỷ lệ token toàn document.

## 5. Vì sao MD/JSON PASS mà vẫn thiếu

`qnu_docx_artifacts._render_and_save:53` nhận QnuStructuredDocument đã dựng, render Markdown rồi gọi `validate_qnu_markdown:572`. Validator kiểm frontmatter, loại khối, ID, references/fields, vị trí/cờ và cú pháp. Nó không nhận DOCX bytes hoặc inventory nguồn để biết có3notes chưa được đưa vào model.

MD và JSON có thể cùng thiếu3notes và vẫn đối soát giống nhau. Hash xác nhận đúng bytes/identity, không xác nhận nội dung đầy đủ. Alignment90% cũng dùng mẫu số là tokens của Docling nên phần nguồn đã bị Docling bỏ không tự trở thành một token thiếu trong phép kiểm đó.

Cần inventory/fidelity gate độc lập: anchor/note parts, bảng/ô/merge/header, hình và coverage nguồn → extracted units. Đối tượng thiếu chưa được chuyển đổi phải có cờ vị trí/phạm vi, không im lặng. Giữ tách biệt artifact ready, nội dung đã đối soát và quyền duyệt/xuất bản.

## 6. Hai phát hiện phụ đã rõ nguyên nhân

- **Hình:** probe thấy picture có `image` thật nhưng caption_count0. Builder dòng581 chỉ giữ self_ref/caption và luôn đánh missing_content; không xuất embedded image. Đây là thiếu bước đóng gói resource ở adapter, không chứng minh hình nguồn không đọc được.
- **Header lặp:** `_header_paths:213` lấy text của grid[row][col] cho từng tầng. Ô gộp dọc được tham chiếu lại ở các hàng, nên tạo “Nhóm/Nhóm/Nhóm”. Cần xử lý identity/origin ô gộp để không lặp mức, không loại text trùng bừa vì hai header khác tầng có thể hợp lệ cùng tên.

## Kiểm chứng, giới hạn và ưu tiên

Lệnh thành công từ `backend`: `.venv/Scripts/python.exe ../.antigravity-bridge/validation/analyze_docx538.py`, exit0. Lần đầu probe chạy đến bước đọc version rồi dừng vì chỉ có metadata docling-slim, không có distribution docling; đã sửa helper để đọc đúng package và chạy lại, không đổi môi trường hoặc cài dependency. Kết quả phiên537 chỉ dùng để so stats; kết quả causal ở538 là chạy lại parser/mapping thật trong RAM.

Không chạy full Pytest/Ruff/build hoặc inference do chỉ phân tích, không sửa app. Không cập nhật trạng thái nguồn, không reparse/nạp lại, không model/provider calls, không commit/push/stage/reset/restart/deploy. Mã đang thay đổi đồng thời bên ngoài được giữ nguyên. Không tuyên bố các sửa RAG đồng thời đã nghiệm thu.

Thứ tự đề xuất khi được giao sửa: bảo toàn OOXML notes/resources và source inventory → dựng context association có căn cứ → field states theo scope đã xác minh → mapping theo occurrence/structure → fidelity gate và regression từ DOCX thật cho cả luồng. Giữ đủ103dòng/45NV đã đạt, không sửa nguồn để né trường hợp khó. Bản thử tiếp tục review_required; chưa có quyền APPROVED.
