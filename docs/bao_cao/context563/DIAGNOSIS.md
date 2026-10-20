# Context563 — Vì sao EVIDENCE_CONTEXT_MISSING không phải tràn context Qwen

Ngày 2026-10-20. Phạm vi người dùng yêu cầu: tìm nguyên nhân, đối chiếu khả năng context 32K. Chỉ đọc cấu hình/usage/nguồn local và chạy probe Python trong bộ nhớ; không gọi lại LLM, không sửa mã ứng dụng hay thay cấu hình/nguồn.

## Kết luận được kiểm chứng

Lỗi này được backend chủ động phát sinh bằng HTTP 409 trong `rag/evidence_dependencies.py`, khi không tìm được đúng canonical unit trong tập bằng chứng hoặc định danh/hash/revision không khớp. Nó không phải lỗi provider báo vượt cửa sổ token. Nhánh ModelOps xử lý vượt context riêng bằng mã `MODEL_CONTEXT_EXCEEDED`.

Usage đã lưu của đúng hội thoại live Context562 có hai lượt Qwen3.5-9b, đều `success`, không fallback:

| Lượt | Input tokens | Output tokens | Tổng tokens |
|---|---:|---:|---:|
| 1 | 543 | 133 | 676 |
| 2 | 4786 | 52 | 4838 |

Không cộng token của hai request thành một cửa sổ. Không gọi model mới để kiểm tra ngưỡng 32K/64K. Các request này đã được provider chấp nhận, nên lỗi 409 không được giải thích bằng việc Qwen từ chối vì context đầy.

## Lỗi đóng gói tái hiện trực tiếp

1. Đọc đúng published snapshot hiện hành của `col_admissions`: 272 canonical blocks và 6 reviewed fact blocks; dependency closure của tập đầy đủ PASS.
2. Trong `_fact_groups`, dòng 102 gọi `exact(...)` kiểm tra canonical source row của fact, nhưng không giữ giá trị trả về.
3. Vòng lặp dependency bỏ qua chính `source_unit_id`; danh sách nhóm cuối chỉ có fact dẫn xuất và các header/note/condition, thiếu canonical source row đã kiểm tra.
4. `pack_context` dùng danh sách nhóm đó. Một fact được chọn tạo 4 blocks, 8057 ký tự theo cách tính ngân sách của packer; không có nhóm nào bị loại vì ngân sách. Dòng nguồn bị thiếu do cách dựng nhóm.
5. `source_grounded_claims` gọi `dependency_intros` → `dependency_groups` → `_fact_groups` → `exact` để kiểm tra lại tập đã đóng gói, rồi phát sinh đúng `EVIDENCE_CONTEXT_MISSING` tại dòng 90. Probe không gọi LLM cũng tái hiện lỗi.

Đây là dòng nguồn canonical và fact dẫn xuất mang hai vai trò/định danh khác nhau. Có một bản diễn giải số liệu không thay cho việc giữ liên kết với đúng dòng nguồn đã xuất bản.

## Thí nghiệm loại trừ thiếu ngân sách

| Probe | K / ngân sách ký tự | Số block / ký tự đã chọn | Kết quả |
|---|---|---|---|
| Cấu hình ứng dụng hiện tại | 5 / 36000 | 4 / 8057 | Thiếu source row, HTTP 409 |
| Ngân sách lớn trong bộ nhớ | 100 / 10000000 | 4 / 8057 | Vẫn thiếu cùng source row, HTTP 409 |
| Bổ sung đúng canonical source row trong bộ nhớ | Thêm đúng 1 block | Không thay bất kỳ hash/nội dung nào | Closure và claim projection PASS |

Probe ngân sách lớn chỉ truyền đối số cho hàm thuần; không thay cài đặt chạy và không gửi gói 10 triệu ký tự tới model. Phép bổ sung source row là mô phỏng chẩn đoán, chưa phải bản sửa đã áp dụng hoặc Knowledge E2E PASS.

`max_context_chars=36000` là giới hạn ký tự đóng gói của ứng dụng, khác với số token tối đa mà model nhận. Tăng cửa sổ model không tự khôi phục một block mà code chưa đưa vào gói.

## Giới hạn và hướng sửa

Usage thật và nguồn gốc mã lỗi chứng minh không có lỗi tràn context ở hai lượt đã kiểm. Probe mới có stack cụ thể và tái hiện độc lập lỗi mất source row. Lượt live cũ không lưu toàn bộ plan/tập lựa chọn/stack, nên chưa tuyên bố đây là nhánh duy nhất từng gây mã 409 đó; cùng mã còn bảo vệ trường hợp thiếu note, sai hash/revision hoặc canonical unit trùng.

Hướng sửa tối thiểu: đưa đúng canonical source row vào atomic dependency group của reviewed fact, cùng header/đơn vị/chú thích/điều kiện bắt buộc. Dựng closure và kiểm toàn vẹn tập đã đóng gói; cả nhóm phải vào hoặc bị loại theo ngân sách, không tắt guard. Thêm regression cho chuỗi pack → claim projection, missing/duplicate/cross-revision targets, ngân sách nhỏ và shared notes; sau đó mới kiểm Knowledge E2E trên snapshot cố định.

Không cần đổi Qwen sang 64K để chữa lỗi đóng gói này. Kết luận đó không khẳng định 32K đủ cho mọi tài liệu/câu hỏi có thể phát sinh sau này.

## Bằng chứng và tác động

Lệnh probe chạy bằng `backend/.venv/Scripts/python.exe`, cwd root repository, exit 0. DB transaction READ ONLY, DB/MinIO/Qdrant đã xác minh loopback. Bằng chứng metadata và stack: `backend/storage/context563/diagnosis.json`.

Không có app-code/config/DB/source/index/publication writes; không commit/push/restart/deploy. Không tạo database test hoặc Storage runtime cần dọn. Chỉ giữ file chẩn đoán private và báo cáo. Không chạy full suite vì không sửa ứng dụng.
