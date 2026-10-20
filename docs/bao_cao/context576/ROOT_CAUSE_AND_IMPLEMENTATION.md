# Context576 — Nguyên nhân và thay đổi

N18 và B03 đều bị yêu cầu chứng minh nhiều hơn điều câu hỏi thực sự cần xác lập. N18 hỏi nội dung một ô ghi điều kiện, nhưng row audit đòi chứng cứ của toàn Phụ lục để đánh giá hồ sơ. B03 hỏi tình huống giả định thiếu một điều kiện bắt buộc, nhưng verifier lại đòi xác nhận hồ sơ giả định thực sự thuộc diện đủ điều kiện. Ngoài ra, đoạn quy định dùng tên nhóm còn mã ngoại lệ nằm ở bảng tóm tắt; các quote phạm vi có trong context chưa được gắn trực tiếp vào claim để hai audit đọc cùng bằng chứng.

## Ranh giới được làm rõ

1. Thuật lại nguồn: trả đúng giá trị/điều kiện và tham chiếu mà ô ghi. Không tự viết nội dung phần được dẫn, không xác nhận hồ sơ đã đạt.
2. Giải thích quy tắc hoặc giả định: giữ phạm vi, các tiền đề và loại trừ. Thiếu một điều kiện cần không thành đủ điều kiện; một con đường đủ hoặc một lựa chọn thay thế không bị biến thành điều kiện cần phổ quát. Giả định từ người hỏi không được lưu hay trình bày thành fact của nguồn.
3. Xác nhận trường hợp thực tế: vẫn cần đầy đủ điều kiện áp dụng và chứng cứ thực tế. Mã trùng, câu trích hay một bảng tóm tắt không đủ để phê duyệt.

`answer_obligations.py` dùng chung hướng dẫn này cho các lượt đọc/đề xuất/kiểm chứng hiện có; không thêm bước gọi model. Các verdict âm về phạm vi, conflict, evidence hoặc completeness vẫn chặn.

`source_claim_context.py` gắn thêm tối đa trong giới hạn bốn reference cho claim: hàng nguyên văn mang đúng mã được hỏi và heading tổ tiên theo parent/unit. Chỉ dùng blocks đã được cấp vào lượt đọc, cùng binding/index/source/hash đầy đủ. Mã khớp toàn bộ; mã trùng, unit thiếu/trùng, vòng parent, hash thiếu, nguồn khác hoặc quote vượt contract không được đoán. Bằng chứng thêm chỉ là attribution, không tự kết luận áp dụng. Primary quote và nội dung công khai giữ nguyên.

## Phòng ngừa lỗi cùng lớp phát hiện trong benchmark

Lượt 64 câu đầu phát hiện một điều kiện đã hiện nguyên văn vẫn bị đánh dấu thiếu vì model bỏ `retained_by`. Server bổ sung `source_condition_claims` từ đúng clause, claim công khai và span nguồn đã gắn; không dựa vào câu chữ do model đề xuất. Server tự tính lại khi resolve, không tin map do client/model gửi. Chỉ sửa thiếu liên kết khi chính văn bản và nguồn khớp; ID lạ, sai identity/span/hash, đoạn chưa xuất hiện hoặc block ID trùng vẫn chặn. Kiểm năm/role riêng không được bỏ qua.

Regression mới cũng phát hiện `audit.complete=false` chưa được dùng trong quyết định cuối của verifier khi các atomic check đều true. Bản chốt bổ sung guard này, nên map literal không thể ghi đè một audit phủ định. Đây là siết kiểm chứng, không hạ Quality Gate.

## Vị trí tài liệu khác phạm vi của hàng

Sau batch v12, B03 có một lượt gọi thật vẫn FAIL: repair thêm hàng E-A nhưng verifier dùng vị trí mục II.2 về nhóm B để loại hàng ghi rõ nhóm A. Nested hint `section_role` chưa loại được sự mơ hồ của trường `section` ở các projection khác.

Bản chốt chuyển nguyên văn section của hàng bảng có đủ tọa độ/header/cell sang `document_position: {section, role: location_only}` trong cả block, passage, passage gọn và reference catalog gửi model. Chỉ đổi cấu trúc truyền metadata, không xóa văn bản vị trí hay thay nội dung nguồn. Ngữ cảnh hàng và quy định nguồn vẫn xác định phạm vi, không tự gán từ vị trí bảng. Non-table hoặc hàng không đủ cấu trúc giữ contract section cũ. Raw EvidenceBlock/reference/citation trên server vẫn giữ section nguyên văn; không sửa Markdown/JSON, parser hay dữ liệu đã xuất bản.

Bốn test projection tái hiện FAIL trước sửa. Một assertion transport của test575 được cập nhật theo contract mới và thêm assertion raw provenance không đổi; không sửa nhãn/giá trị/phạm vi kỳ vọng để chấm xanh. Các negative scope/year/hash và guard audit phủ định vẫn chạy.

Cache version đáp án đổi từ v10 sang v13 để phân biệt hành vi mới; không flush cache hoặc đổi cấu hình đang chạy. Không parser, frontend, schema DB, model, nguồn hoặc index nào được sửa trong Context576. Các diff có từ trước được giữ nguyên.


## File ứng dụng thuộc Context576

- `backend/app/modules/rag/answer_obligations.py`
- `backend/app/modules/rag/evidence_audit.py`
- `backend/app/modules/rag/evidence_claims.py`
- `backend/app/modules/rag/evidence_context.py`
- `backend/app/modules/rag/evidence_indexed_audit.py`
- `backend/app/modules/rag/evidence_model.py`
- `backend/app/modules/rag/evidence_passages.py`
- `backend/app/modules/rag/evidence_verification.py`
- `backend/app/modules/rag/row_answer.py`
- `backend/app/modules/rag/service.py`
- `backend/app/modules/rag/source_claim_context.py`
- `backend/app/modules/rag/source_row_context.py`
- `backend/app/modules/rag/source_scope_audit.py`
