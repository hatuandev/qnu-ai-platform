# Phiên #410 — Đề xuất xuất bản nguồn đã chọn

## Vấn đề người dùng

Người dùng xác nhận kiểm thử lại từ đầu hoạt động ổn, nhưng khi chỉ nạp vector 1–2 tài liệu thì không xuất bản riêng các tài liệu đó được.

## Chẩn đoán mã nguồn

- `VectorLoadControls` truyền toàn bộ bindings vào `canPublishSources`, nên FE yêu cầu mọi nguồn active cùng có vector ready trên generation được chọn.
- `publish_generation` kiểm tra index của mọi binding active và trả `GENERATION_NOT_READY_FOR_ACTIVATION` khi bất kỳ nguồn nào chưa có index.
- Đây là giới hạn publish theo toàn generation hiện tại; việc nạp vector vốn đã hỗ trợ đúng tập nguồn được chọn.
- Retrieval snapshot lọc active generation của collection, nên không thể chỉ bỏ gate hoặc kích hoạt generation khác cho vài nguồn rồi bỏ qua các nguồn cũ; chúng có thể biến mất khỏi snapshot phục vụ.

## Hướng đề xuất trước khi triển khai

- Bổ sung xuất bản tập nguồn được chọn, pin exact source/index revisions và validate review/fact parity chỉ trên targets.
- Khi kho chưa có generation active, cho phép xuất bản generation đầu tiên chỉ với targets sẵn sàng; các nguồn khác tiếp tục chưa xuất bản.
- Khi generation đã active, cho phép thêm/cập nhật một tập nguồn trong chính generation đó; giữ serving pointers của nguồn không được chọn.
- Publish targets atomically với collection epoch/source/index guards, tenant/workspace scoping và audit; failure không thay pointer đang phục vụ.
- Khi đổi model/generation đang phục vụ, giữ luồng chuyển toàn kho riêng biệt; không trộn embedding spaces và không âm thầm làm biến mất tài liệu đang serving.
- FE phân biệt rõ `Xuất bản đã chọn` và `Xuất bản toàn kho`, confirmation nêu phạm vi; candidate preview phải dùng đúng snapshot tương ứng.

## Trạng thái phiên

Chỉ đọc mã và xây dựng đề xuất; chưa sửa FE/BE, chưa gọi API publish, chưa thay dữ liệu hoặc chạy tests. Cần thống nhất với người dùng vì đây là mở rộng contract publication, không phải chỉ đổi điều kiện enable của một nút.
