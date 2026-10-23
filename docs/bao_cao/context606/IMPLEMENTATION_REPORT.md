# Context606 — Rõ nghĩa trạng thái nguồn và kiểm chứng compiler bằng Qwen

Ngày 23/10/2026. Tiếp tục theo thứ tự: kiểm chiều quan hệ, đối soát ba coverage dispute, regression và thử compiler ba DOCX trong môi trường riêng. Bổ sung mới của người dùng: tránh dùng một tên `unknown` cho hai ý nghĩa khác nhau. Giữ nguyên model Qwen, dữ liệu nguồn và publication; không gọi Luna.

## Đổi tên ở ranh giới model

| Ý nghĩa | Hợp đồng gửi/nhận model | Dữ liệu bền vững hiện có |
|---|---|---|
| Nguồn không xác định giá trị được hỏi | `value_state=source_unspecified`, `value=null` | `value_state=unknown`, `value=null` |
| Nhận định chưa đủ bằng chứng để kiểm chứng | `verdict=unresolved` | `verdict=unresolved` |
| Giá trị có trong nguồn | `value_state=present`, giá trị không rỗng | Giữ nguyên |
| Nguồn có mâu thuẫn | `value_state=conflict`, `value=null` | Giữ nguyên |

Tên mới chỉ dùng cho assertion.value_state ở transport của topic compiler. Server mã hóa trước inference và giải mã trước khi kiểm hợp đồng/persist. Không migrate DB, không đổi bundle/hash cũ, không đổi API bền vững, không thay tất cả `unknown` trong ứng dụng. `temporal.role=unknown` tiếp tục là vai trò năm chưa rõ, không phải trạng thái giá trị hoặc verdict.

Chỉ chuyển trường value_state có cấu trúc. Trích nguyên văn, tên trường, giá trị chuỗi và temporal roles không bị thay bằng thao tác tìm/thay văn bản. Dynamic schema của PacketDraft chỉ cho `present/source_unspecified/conflict`; không nhận `unknown/unresolved` làm trạng thái giá trị trên wire. Bộ kiểm scalar hiện có vẫn chặn null cho present và giá trị chắc chắn cho trạng thái chưa xác định/mâu thuẫn.

Có thể kiểm chứng rằng nguồn cố ý để trống ngày đầy đủ; khi đó assertion về giới hạn nguồn có thể được supported, trong khi giá trị ngày vẫn null. Nếu bản thân nhận định về sự thiếu vắng hoặc phạm vi chưa có bằng chứng thì vẫn unresolved. Không suy từ một đoạn không được cấp rằng cả tài liệu không có thông tin.

## Các sửa đổi phục vụ lượt kiểm chứng606

- `compilation_coverage.py`: hướng dẫn phân biệt relevance với khả năng cung cấp scalar đầy đủ; giữ chế độ/đợt/nhóm và association theo bằng chứng. Thuật toán hai phân loại đồng thuận không đổi.
- `compilation_engine.py`: hướng dẫn giới hạn nguồn cho extraction/review/selection/synthesis, local entity và state/value nhất quán. Review không được tạo item cho assertion không tồn tại; proof cần nhưng bị bỏ sót phải vào missed_evidence_ids. Chia packet theo số primary tối đa4 để chừa dung lượng JSON đầu ra; không bỏ proof/context để vừa budget.
- `compilation_runtime_schemas.py`: kiểm local graph ngay khi nhận PacketDraft; sai entity IDs/duplicate IDs/orphan bị từ chối trước semantic review. Thêm policy max_primary_per_packet, không tăng call/time budget.
- `compilation_schemas.py`: giữ predicate scalar cũ, thêm mã lỗi rõ để một lượt sửa định dạng có căn cứ; không đổi legacy stored enum.
- `compilation_transport.py`: wire alias và dynamic enum; khôi phục ID và trạng thái trước hợp đồng nội bộ.
- `compilation_modelops.py`: cache hash gồm phase instructions, transport guide/version và policy để không tái dùng kết quả trước thay đổi.

Sáu file app thay đổi so snapshot đầu606. Không sửa parser, router, public serving, source/index/publication hay cấu hình model. Các test lifecycle được cập nhật để đếm coverage đúng một lần theo proof và số packet thực, thay giả định cố định3packet; vẫn kiểm idempotency, revocation và reuse không gọi lại inference.

## Giới hạn

Đổi tên giúp hợp đồng rõ hơn; không bảo đảm model luôn tuân thủ schema hoặc kiểm thời gian đúng. Lượt thử thật cuối vẫn có rejection, giữ nguyên thất bại và cổng chất lượng. Không tự chuyển verdict sai thành supported hoặc tự tạo kết quả kiểm tra để làm xanh.

Compiler vẫn là review_only/unpublished, chưa nối chatbot. Chưa chứng minh full compiler hoặc benchmark64 thành công với Qwen. Kết quả Luna lịch sử và giả thuyết Token Saver không được đổi nhãn; Qwen lần này đi provider cấu hình hiện có, không qua tuyến Luna.
