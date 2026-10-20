# Context564 — Nguyên nhân và bản sửa dependency closure

Ngày 2026-10-20. Triển khai prompt Context564 cùng 5 bổ sung đã được người dùng duyệt. Trạng thái nghiệm thu toàn bộ phụ thuộc LIVE_RAG_E2E_REPORT, không suy từ unit tests.

## Hai khoảng hở được tái hiện

**Reviewed Fact thiếu canonical source row.** `_fact_groups` gọi `exact` nhưng bỏ kết quả, đồng thời bỏ qua source unit trong vòng duyệt refs. Sau pack, kiểm lại closure không tìm được dòng nguồn. Bộ red ban đầu: 5 FAIL / 14 PASS, exit 1. Bản sửa tái dùng đúng đối tượng `source_row` đã kiểm, đưa nó vào hàng đợi đầu tiên và duyệt cả dependency riêng của dòng đó. `seen` xử lý vòng tham chiếu; identity/hash/revision và unique canonical unit vẫn do `exact` kiểm.

**Thành viên/ancestor bổ sung mất dependency riêng.** Kiểm thử live tiếp tục gặp cùng mã 409 ở một đường khác. Probe không LLM trên 113 prose seeds tái hiện 5 gói có thể thiếu footnote của thành viên được thêm qua nhóm danh sách. Corpus đầy đủ đạt closure, nên không phải kết luận nguồn bị mất footnote. Hai regression tách footnote sang section riêng và ancestor có note đều FAIL trước sửa.

Canonical refs nay được duyệt có hướng và bắc cầu trong `_canonical_context`. `pack_context` hoàn tất required refs của mọi thành viên/ancestor/continuation đã thêm, trước khi tính chi phí và nhận nhóm. Không kéo các sibling không được yêu cầu chỉ vì một note tình cờ nằm trong danh sách khác: dùng map required refs riêng với map enumeration hints. Một regression tái hiện việc mở rộng note quá rộng đã FAIL trong quá trình triển khai và PASS ở bản cuối.

## Kết quả trên nguồn đang xuất bản

- Published canonical corpus: 272 blocks. Sáu fact blocks là tập được chọn cho probe cụ thể, không phải tổng số fact groups của tài liệu; exhaustive selection hiện có 67 groups.
- Sau bản cuối, 113/113 prose seed packs qua closure/projection, không còn 5 gói hở đã tái hiện.
- Cả 6 fact groups của probe giữ đúng canonical row, pack 5 blocks/group với K=5 / 36000 ký tự. Không đổi cấu hình.
- Live batch cuối không còn `EVIDENCE_CONTEXT_MISSING`, gồm cả năm không có dữ liệu; nhưng ca chỉ tiêu vẫn không trả được số liệu, vì nhánh lựa chọn fact độc lập. Xem báo cáo E2E.

## Bất biến được giữ

Không synthetic row, không đổi text/hash/revision, không chấp nhận reference khác identity. Missing/duplicate/cross-revision/hash và metadata hỏng vẫn bị chặn. Dependency có hướng, chia sẻ block được dedup theo IDs đã xác thực; không mở rộng mọi row dùng cùng một note. Budget vẫn tính toàn nhóm, gồm serialization model block và source context theo cách tính hiện có. Nhóm không vừa bị loại cả nhóm với reason có sẵn.

K và ngân sách không đổi. Ngoại lệ `allow_first_whole_group` đã tồn tại cho prose recovery vẫn giữ nguyên: có thể nhận nguyên nhóm đầu lớn hơn K nếu caller đã cho phép, nhưng giới hạn ký tự vẫn áp dụng. Không dùng ngoại lệ này để bật cấu hình mới cho fact test.

## Phân biệt model context

Mã 409 này do backend kiểm chứng nguồn phát sinh, khác `MODEL_CONTEXT_EXCEEDED`. Không tăng Qwen 32K/64K, không thay model/provider/prompts để sửa. Một lượt thử giữa chừng có lỗi Qwen request và fallback Luna theo cấu hình sẵn có; ghi riêng, không coi đó là nguyên nhân của dependency bug hoặc bằng chứng phải tăng context.

## Giới hạn của bản sửa

Packing đã được sửa và kiểm trên snapshot thật. Nghiệm thu Reviewed Fact qua chat chưa đạt: runtime hiện dùng fact/table route rồi prose fallback; không tự bật evidence policy hoặc sửa entity/metric mapping để ép pass. Không kết luận mọi mã 409 khác đã được loại bỏ.

Bằng chứng private: `backend/storage/context564/tests`, `published-verified-audit.json`, `prose-pack-audit.json`, các batch live và TCP receipts. Không đưa corpus/token/key vào Git.
