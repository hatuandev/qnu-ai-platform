# Context572 — DOCX mới và vector staging

**Đã tạo revision mới `ks_rev_d5135c27d130`, READY_WITH_LIMITATIONS; index staging `idx_rev_91267ceb54ff` ready. Chưa xuất bản.** Kho không bị dọn toàn bộ; bản đang phục vụ và dữ liệu collection khác được giữ.

| Kiểm tra thực tế | Kết quả |
| --- | --- |
| Nguồn DOCX | Cùng SHA256 `58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274`, 102423 bytes |
| Bóc tách | 233 khối, 36 mục, 10 bảng, 53 source list items, 3 raw footnotes |
| Bảo toàn | 517 fields giữ nguyên raw/state; IDs, loại, parent và section path giữ |
| Standard MD/JSON | Validation và hash/pair/source verification đạt; tải API HTTP200 khớp bytes lưu |
| Bản dễ đọc | 62083 bytes; Markdown AST nhận 10 bảng, 3 footnote/3 refs, list depth3, code thật vẫn là code |
| Quality Gate | 0 blocker; 1 cảnh báo trang preview của native footnote; 44 cell limitations |
| Nạp vector | API202 → worker thật completed; 262 chunks, 415 facts, 262 points; parity PASS |
| Chặn publication | Mọi point mới `is_retrievable=false`, status staging; index ready, không active |
| Bản đang phục vụ | 262 points cũ/payload nguyên; active index cũ, snapshot và epoch65 giữ |

Reader AST có 55 listItem tổng cộng, gồm phần nội dung khác; 53 là số item có mapping nguồn trong các block list, không đánh đồng hai đại lượng. Chuỗi raw, 0, mã có số0 đầu, unknown, bảng không header và ô gộp không được tự diễn giải. Xác nhận Hình1 đã có được tái sử dụng vì cả file và ảnh khớp hash, không tạo phê duyệt ngữ nghĩa mới.

## Lỗi tích hợp phát hiện bằng luồng thật

Revision3 `ks_rev_58f4db9f0b8d` bị chặn vì `table_header_unresolved.status=literal_only` nằm ngoài trạng thái hợp lệ của standard. Offline Context571 chưa chạy bước `preserve_native_layout` trong kiểm chứng roundtrip nên bỏ sót ranh giới này; không gọi kiểm chứng offline cũ là full ingestion E2E.

Đã thêm regression lưu/đọc artifact thật bằng Storage test: FAIL đúng lỗi trước sửa. Sửa tối thiểu `docx_layout_fidelity.py` dùng trạng thái cờ `confirmed` sau khi khớp đầy đủ lưới, spans, số hàng và hash OOXML. Đây là xác nhận tính toàn vẹn của literal, không phải xác nhận vai trò header: `column_roles=unknown`, field ambiguous/normalized null, interpretation literal_only và 0 facts ở bảng fixture không header vẫn được kiểm tra. Không đổi validator, chính sách Quality Gate, ModelOps hoặc semantic approval.

Revision4 `ks_rev_8c2a5731e277` của lần sửa chưa đủ giữ flag unresolved đã hợp lệ về cú pháp nhưng vẫn bị block ở projection; regression được mở rộng để kiểm cả ranh giới này. Revision5 hiện tại qua cả hai. Hai revision bị chặn và job receipts được giữ để đối soát; không ghi đè bản lỗi hoặc bản xuất bản. Một full run khởi đầu trong lúc phát hiện nhánh projection đã dừng và ghi INTERRUPTED; kết quả nghiệm thu lấy lượt full-complete cuối, không dùng lượt bị ngắt.

## Facts thay đổi thế nào

368 → 415 là thay đổi dẫn xuất của projection hiện tại, không phải số ô bóc tách. Thêm 60 cells vào facts (59 giá trị chữ, 1 số0 có chứng cứ); 13 cells không còn materialize thành facts (10 trường mã/tên từng gắn vào group identity; 3 trường của một dòng ngưỡng/khoảng). Cả 13 vẫn ở canonical Markdown/JSON, không bị xóa. 340 facts chung đổi trường định danh theo projection hiện tại; giá trị ở mọi cell chung không đổi. Không coi tăng số facts là tự chứng minh chất lượng.

Toàn bộ facts mới trỏ về cell state present với raw khớp sau trim whitespace đầu/cuối; có đúng 1 khác biệt trailing-space trong trường văn bản dài, raw JSON gốc còn nguyên. Các ô numeric gold của bộ frozen vẫn có đúng giá trị và năm. Không có unknown cell thành fact, không áp unapproved semantics. Các thất bại đầu của probe so sánh gồm giả định sai toàn bộ factset phải giống chỉ mục cũ, whitespace và kiểu string/int của năm; log được giữ, sau đó kiểm theo raw cell provenance và gold. Không sửa dữ liệu hoặc assertion ứng dụng để che lệch.

## Truy vấn thử staging

Admin candidate API thật, có quyền và kiểm hash/source/index: 6/6 HTTP200, citations trả ra đúng staging revision; đúng nội dung 4/6: N01, N02, P07, P13. P06 thiếu điều kiện; P08 từ chối quá mức. Chỉ preview, không chuyển nguồn phục vụ. Phép thử bổ sung D01 trả đúng khoảng và đơn vị của dòng ngưỡng đã không còn facts riêng, từ canonical evidence.

Preview dùng API quản trị/candidate và defaults khác ranh giới assistant chat; không quy khác biệt P08 chỉ cho parser. Không chạy lại toàn bộ64 trên revision staging, không gộp 4/6 hoặc D01 vào điểm86,67%. Usage preview6 là 19 Luna success/0 fallback; D01 ghi audit riêng. Vẫn còn lỗi RAG nên chưa tuyên bố hoàn tất chất lượng hoặc sẵn sàng production.

## Xem kết quả

[Mở revision mới](http://localhost:3000/knowledge/col_admissions/sources/bnd_fa71a57c9cf1?revision=ks_rev_d5135c27d130&tab=content), chọn Xem Markdown để đối chiếu Bản dễ đọc / Gói chuẩn / Bản phục vụ RAG. Chỉ mục đã ở staging; không cần nhấn nạp lại. Xuất bản vẫn là hành động riêng chưa thực hiện.
