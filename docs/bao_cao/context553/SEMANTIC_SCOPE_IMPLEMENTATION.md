# Context553 — triển khai phạm vi ngữ nghĩa

## Thay đổi và lý do

- `semantic_annotations.NoteScope`: thêm trường nội bộ tùy chọn `assertion_version=1` và `related_evidence`. Snapshot cũ mặc định dùng liên kết source unit cũ. Không thay wire schema selector v1/v2.
- `semantic_assertions`: dựng SourceUnit dẫn xuất từ đúng khoảng code point của EvidenceBinding; giữ source ID/revision/hash, vị trí canonical, locator và đích table/row/column. Nội dung là slice nguồn, không qua LLM viết lại. Mỗi assertion có định danh riêng; hai span cùng nguồn/cùng target được phép, bản trùng bị chặn. Reference kèm theo có cùng scope và binding riêng.
- `semantic_binding`/`semantic_evidence`: cung cấp thêm span trọn khoản đánh số; từ chối gắn toàn bộ list nhiều khoản như một điều kiện toàn bảng. Selector v2 chọn span con thì dùng assertion dẫn xuất. V1 đã lưu giữ hành vi cũ; v1/v2 giữ schema/hash wire. Thông báo model yêu cầu chọn riêng các điều kiện.
- `semantic_annotations.stage_semantic_annotations`: tự tạo scope issue cho assertion mới, giữ toàn văn để đối chiếu phủ định. Hai issue gốc cho p050/p051 được tái sử dụng vì cùng nguyên đơn vị và cùng đích; không yêu cầu xác nhận lặp lại. Không tự ghi quyết định.
- `retrieval_models`/`retrieval_units`: SourceUnit có metadata `semantic_scope`; giá trị rỗng không đổi seal v1. Span assertion được kiểm với source unit và canonical. Không suy temporal verified từ một mệnh đề con.
- `source_links` được tái sử dụng, không sửa thuật toán đóng phụ thuộc. `_refresh`, `structure_chunks` và `semantic_store.semantic_fingerprint` giữ phạm vi assertion trong facts/chunks/seal. Context cho một field chỉ đóng các phụ thuộc chung và cột đúng đích.
- `_apply_cells` nhận bằng chứng từ assertion dẫn xuất chỉ khi toàn EvidenceBinding trùng chính xác span được scope tới ô đó; mệnh đề khác trong cùng source unit không đủ. Raw, ô trống, số 0 và các kiểm tra giới hạn vẫn giữ nguyên.
- `ContextBuilder`: thêm view cho human review, có giới hạn unit/bytes; mở subtree của heading gồm cả mục con. `expand` cũng mở đầy đủ subtree rồi kiểm ngân sách packet hiện có. Heading không có body được báo thiếu.
- `semantic_context_review`: phân tích reference là advisory, gắn đúng issue ID và assertion IDs, có full-source bindings. Hành động mới `related_context_reviewed` cần người dùng xác nhận riêng, full reference evidence đúng và exact proposal hash/target; không cho đổi reference đã phân loại liên quan thành `not_applicable_to_target`. Phân loại chưa đủ chứng cứ chặn áp dụng. Heading riêng không cho kết luận. Phân tích đã có được giữ khi model im lặng; reprocessing deferred đi qua proof và issue scope mới, không tự hoàn tất.
- `semantic_modelops`: đường followup có kiểm chứng hỗ trợ cả missing-context và deferred-reference. Không thay provider, model, timeout, key hay ngân sách runtime.
- Frontend: hiển thị reference đầy đủ, đúng nhãn hành động, phân biệt source unit và trích đoạn. Span Unicode dùng code points thay vì UTF-16. Key của card gồm evidence ID, hỗ trợ nhiều assertion cùng source/target. Vẫn dùng màn hình và primitives cũ.
- `prepare_semantic_review_checkpoint.py`: đọc sealed checkpoint, kiểm file/envelope/input/source hashes, load pair qua LocalStorageDriver, dùng ContextBuilder; tạo thư mục checkpoint mới, không ghi source DB, approve, apply, index hoặc gọi model.

## Revised proposal cụ thể

12 assertion, do agent đối soát và trình duyệt, không giả nhận là lượt model mới:

1. l006: đơn vị/quy định chung Bảng1.
2. l006: dữ liệu 2027 dự kiến, c10–c12 giữ ba đại lượng khác nhau.
3. l006: thiết bị nhóm A, giao sáu dòng r001–r006 với c10–c12 năm 2027; giữ điều kiện/ngoại lệ đầy đủ II.1 và mệnh đề không sửa chỉ tiêu.
4. l006: điều kiện riêng AM-0007/r003, loại AM-0070/r004.
5. l006: ngoại lệ thực tập riêng nhóm B/r007–r012, bổ sung II.2, khoản 3 Điều15, dẫn nhập và giới hạn tách biệt của phụ lục.
6–8. p049: ba mốc theo đúng nhóm cột 2025, 2026, 2027.
9. p049: tỷ lệ từ số lượng cùng năm/làm tròn, chung bảng.
10. p050: chỉ r003, giữ toàn bộ loại trừ r004.
11. p051: chỉ c11 “Ước tính”; c10/c12 và c05/c08 không nhận điều kiện này. Quan hệ chung nhóm năm được assertion 2/8 bảo toàn độc lập.
12. footnote_2: mã chuỗi ở c02/r001,r002,r003, giữ 0 đầu.

Sáu deferred reference đều được đối chiếu nội dung và phân loại advisory là liên quan, theo từng assertion. Tất cả tám ID gốc được giữ. Tổng còn 18 issue chờ human decision: tám gốc và mười scope issue bổ sung; p050/p051 tái sử dụng issue cũ. Không có quyết định mang actor thật hoặc test trong checkpoint.

## Cách chạy lại

Các test ở `backend/tests/test_semantic_scope_assertions.py` dùng tài liệu tổng hợp và actor TEST. Chạy cùng nhóm regression semantic/lifecycle/binding trên DB test và Storage tạm theo bảng kiểm chứng repo. Script `audit_context_patch.py` chỉ đọc cấu hình DB; `context_patch_validation.py` tạo DB có ownership nonce, vô hiệu MinIO/Qdrant/Redis và migration/seed trong tiến trình test. Không chạy trực tiếp suite trên database ứng dụng.

Để tạo lại bản đối soát offline, dùng script prepare với `--original`, `--plan` và một `--output` mới chưa tồn tại. Kế hoạch và corpus giữ ở Storage riêng; không đóng gói vào Git. Nạp nguồn/actor/review của ứng dụng thật là bước riêng, chưa thực hiện.
