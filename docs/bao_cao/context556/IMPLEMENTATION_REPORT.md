# Context556 — Triển khai

Chỉ thêm hai file; không đổi mã runtime ứng dụng, schema DB, ModelOps, parser standard hay importer.

1. `backend/scripts/reconcile_semantic_checkpoint.py`: công cụ offline chuẩn bị proposal mới khi và chỉ khi mọi source/target map được. `ExactSourceMap` chứng minh DOCX hash, manifest/document parity, exact full body, locator và ancestry/role duy nhất; bảng chứng minh toàn raw/state grid và locator, cột đích chứng minh đúng thứ tự/header metadata. Không fuzzy, embedding, từ điển hoặc chấp nhận ID trùng làm bằng chứng.
2. `backend/tests/test_canonical_semantic_reconciliation.py`: 13 ca mới về đổi ID/binding/hash, thiếu/đổi/trùng evidence/role/locator, cùng chữ khác vị trí, đổi header cột đích, sai DOCX/proposal hash/manifest/raw cell, và pending import/persistence qua DB/Storage test.

`reconcile_proposal` dựng mới source identity, input hash, evidence IDs, assertion/issue IDs và proposal hash; chỉ gọi stage helper trên bản sao trong bộ nhớ, không ghi DB. Khi một assertion/reference thiếu, trả inventory chi tiết với `proposal=null`, không xuất import-package. Trường hợp đầy đủ trả `PREPARED_NOT_STAGED` và importer có xác thực hiện hữu vẫn phải kiểm tra exact pair/hash/revision/actor/conflict.

CLI kiểm checksum mọi file checkpoint đã seal, exact byte hash cặp canonical và DOCX, source identity và pair parity giống contract loader hiện hữu. Pair parity cho phép thứ tự khóa YAML, nhưng không coi bytes khác hash là cùng artifact. Output mới, không ghi đè thư mục có sẵn, không cho output nằm trong checkpoint đầu vào. Negative probe exit1 và không sinh file đã được kiểm tra.

Lượt đầu dùng điều kiện toàn header quá chặt khiến12 mục blocked; sau đối chiếu đã tách chứng minh physical table/raw grid và exact role của từng cột đích. Header3 cột đầu khác do label ô gộp không được giả là bằng nhau. Nếu assertion thực sự nhắm cột có role khác, công cụ vẫn chặn; regression riêng đã chứng minh. Kết quả cuối11mapped/1blocked, không nới guard ứng dụng.

Historical/native probes nằm trong Storage evidence riêng; không ghi raw DOCX/MD/corpus vào gói báo cáo. Hai tiến trình native riêng giữ cùng runtime dependencies, cùng cấu hình preview-off, hai Storage tạm riêng; không khẳng định determinism toàn bộ PDF preview/deployment.

Authenticated TEST integration tái dùng `import_semantic_checkpoint`, actor TEST và endpoint authorization tests hiện hữu. Đóng session, mở session mới, rebuild và pending được giữ nguyên, không effective/active approval. Đây không phải người dùng đăng nhập thật hoặc E2E production.

Supplementary probe với đầy đủ source offline chứng minh nhánh thành công chuyển đủ12assertion/18issue/6reference assessment: labels/roles giữ nguyên, evidence identity và proposal hash mới, không effective/stage. Probe đầu sai giả định rằng input_hash phải đổi khi chỉ đổi revision identity; contract hiện hữu chỉ hash content/manifest/tables nên có thể giữ nguyên. Đã sửa probe theo contract, không sửa app; lượt đầu FAIL và lượt cuối PASS được giữ riêng. Không dùng kết quả này thay bằng chứng canonical thiếu A12.

Mã hiện tại đã sửa builder giữ footnote, nên không sửa parser hoặc revision cũ. Muốn phục hồi nội dung thật cần tạo revision nháp mới theo luồng chuẩn, kiểm evidence rồi mới tạo proposal hash mới. Chưa thực hiện vì prompt yêu cầu xác nhận riêng cho hành động này.
