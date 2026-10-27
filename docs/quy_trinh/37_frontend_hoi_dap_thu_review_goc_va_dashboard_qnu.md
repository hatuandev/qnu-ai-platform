# 37 — Hỏi đáp thử, tải review gốc và dashboard QNU

Phạm vi: `frontendV1/`, các mục F4–F6 sau [kiểm kê680](../bao_cao/context680/FE_BE_INVENTORY.md).
Các API backendV1 đã có sẵn; phiên này không thay hành vi server.

## Hỏi đáp trực tiếp theo kho

Mở workspace → kho tài liệu → **Hỏi đáp thử**. Trang có đường dẫn riêng
`/workspaces/:workspaceId/collections/:collectionId/answers`, có thể mở trực
tiếp và tải lại. Cần là thành viên có quyền đọc kho; server kiểm tra quyền
lại khi nhận yêu cầu.

1. Nhập câu hỏi; chọn model trả lời hoặc để **Theo mặc định workspace**.
2. Có thể chọn tài liệu bằng bộ chọn của quy trình36. Không chọn nghĩa là
   toàn bộ tài liệu đủ điều kiện trong kho. Không mở rộng phạm vi khi ít kết quả.
3. Nếu cần, mở cấu hình RAG để chọn dense/hybrid/rerank, số ứng viên, đoạn
   lân cận và chế độ kiểm chứng. Rerank dùng model có capability tương ứng;
   model kiểm chứng cần capability chat. Mặc định vẫn dense, không mở rộng
   ngữ cảnh, kiểm chứng tắt.
4. Có thể nhập riêng năm dữ liệu, năm ban hành, ngày hiệu lực, ngành và đợt.
   Năm chưa hợp lệ phải sửa trước khi gửi; không suy năm từ câu hỏi hay tên tệp.
5. Chọn **Gửi câu hỏi**, đọc từng ý và bấm nút **Nguồn E…** để đối chiếu.
   Màn nguồn kiểm tra lại quyết định xuất bản/phiên bản và cho mở phiên bản
   tài liệu. Nguồn thay đổi hoặc bị thu hồi không được hiển thị như còn hiện hành.

Đây là hỏi từng câu độc lập, không tạo hội thoại hoặc thay cấu hình trợ lý.
Mỗi lần gửi có thể phát sinh token. Không có retry tự động; lỗi kết nối,
provider hay quyền không biến thành “không có dữ liệu”. Rời trang không hủy
xử lý server; mất kết nối có thể xảy ra khi server vẫn đang xử lý. Cần hội
thoại nhiều lượt thì dùng chức năng trợ lý/hội thoại hiện có.

Biểu mẫu và kết quả chưa được lưu bền vững qua F5. Kết quả ghi rõ câu hỏi và
phạm vi đã gửi; token sinh câu trả lời tách khỏi token kiểm chứng. Kiểm chứng
tự động chỉ là một kết quả hỗ trợ rà soát, không bảo đảm câu trả lời đúng.

API: `POST /workspaces/{workspace_id}/collections/{collection_id}/answers`.
FE gửi policy dạng phẳng theo AnswerRequest của BE, không gửi `rag_policy`
lồng, không thêm idempotency key hay endpoint hội thoại giả.

## Tải phản hồi gốc của review Compiler

Trong trang một lượt Compiler, mở tab rà soát và chọn đúng lần review.
Khối **Tệp của lần rà soát** có:

- **Tải bản gốc**: phản hồi model nguyên trạng, không parse rồi ghi lại JSON.
  Có thể tải ở trạng thái completed, failed hoặc uncertain; nếu chưa lưu được
  raw, server trả lỗi và giao diện không tạo tệp lỗi thay thế.
- **Tải Markdown**: chỉ bật khi review completed, vẫn dùng API báo cáo hiện có.

Queued/running chưa cho tải như một báo cáo hoàn tất. Raw có thể không hợp
lệ và không được xem là báo cáo đã duyệt. Tệp chỉ tải sau click; đổi review,
workspace hoặc phiên đăng nhập khi đang tải sẽ bỏ kết quả muộn của lựa chọn cũ.
Không sửa raw, nguồn OCR hay trạng thái duyệt/xuất bản khi tải tệp.

## Dashboard QNU

**Tổng quan** ở nhóm QNU AI mở `/dashboard`, dùng phiên đăng nhập backendV1.
Dashboard KTX cũ vẫn giữ ở `/reference-dashboard` trong nhóm màn mẫu; ranh
giới API của các màn mẫu vẫn được chặn như trước.

Chọn workspace để xem; danh sách có phân trang20 mục. URL giữ workspace đã
chọn và trang bộ chọn. Không tự thay một workspace không truy cập được bằng
workspace đầu tiên. Workspace tạm dừng chỉ hiện trạng thái, không tải nội dung.

- Mọi thành viên đã xác nhận quyền đọc có thể xem tổng số kho, số thành viên,
  sáu kho đầu tiên và đường dẫn tới danh sách đầy đủ/trợ lý/hội thoại.
- Quản trị, biên tập và rà soát được xem tổng số tác vụ chờ/chạy, cần kiểm tra
  (failed/uncertain), hoàn tất và usage theo trạng thái. Bấm một nhóm tác vụ
  mở trung tâm vận hành với bộ lọc tương ứng.
- Chỉ quản trị workspace hoặc quản trị nền tảng tải khối readiness.

Tổng hợp là các bản ghi hiện có trong workspace, chưa phải biểu đồ24 giờ hay
đo tốc độ xử lý. Summary đọc lại mỗi5 giây khi màn đang mở; readiness đọc khi
mở và khi chọn kiểm tra lại. Chi phí/token chưa có số đo giữ “Chưa có số đo”.
Lỗi đọc số liệu được hiển thị như lỗi, không thay bằng bộ đếm0 hoặc dữ liệu mẫu.

## Kiểm chứng và giới hạn

[Báo cáo682](../bao_cao/context682/REPORT.md) ghi kết quả test và kiểm tra
giao diện dùng fixture tổng hợp. Chưa chạy suy luận model thật, SSO thật hay
đánh giá chất lượng RAG trong phiên này. Không thay auth bypass, provider,
credential, migration, dữ liệu phục vụ, index hoặc runtime config.

Các mục này không bổ sung lịch sử evaluation bền vững, streaming, feedback,
chia sẻ chatbot hoặc giao diện full restore khi BE chưa có contract tương ứng.
