# Frontend: sao lưu, dọn tệp và đánh giá RAG

Phạm vi: `frontendV1` nối các API `backendV1` hiện hữu. Workspace tiếp tục là
biên quyền membership/role của v1; quyền và điều kiện cuối cùng do server kiểm.
Giao diện không tạo API phục hồi toàn hệ thống hoặc lịch sử đánh giá chưa có ở BE.

## 1. Sao lưu bằng chứng

Vào **Workspace → Vận hành → Sao lưu** (quản trị viên).

1. Nhập số ngày giữ, hoặc để trống để giữ lâu dài; chọn **Tạo bản sao lưu**.
2. Mở bản sao lưu để xem trạng thái, thời hạn, dung lượng và hash. Chưa đo được
   dung lượng sẽ hiển thị chưa có số đo, không thay bằng 0.
3. Khi hoàn tất, có thể **Kiểm tra toàn vẹn** hoặc **Tải ZIP**. Lỗi xác minh/tải
   được giữ là lỗi; không dùng trạng thái hoàn tất để giả định nội dung còn nguyên.
4. Bản đủ hạn theo API retention mới có **Xóa hết hạn**: nhập lý do → xem trước
   → xác nhận phạm vi → gửi yêu cầu. Đã gửi cho worker chưa có nghĩa là đã xóa.
5. Biên nhận nằm trong URL. Nếu thao tác đã được chấp nhận nhưng chưa giao xong,
   có thể tiếp tục cùng thao tác; hash và khóa chống tạo trùng giữ nguyên.

Danh sách phân trang từ server. API retention trả tối đa 100 ID đủ hạn ở mỗi
lần đọc; làm mới sau khi xử lý các bản đó. Tệp gốc/raw không bị xóa theo thời hạn
của bản backup. Gói này là sao lưu bằng chứng, không phải bản phục hồi toàn bộ
DB, cấu hình bí mật và hệ thống tìm kiếm. Phục hồi toàn hệ thống vẫn theo công cụ
CLI và [quy trình BE](32_duyet_don_du_lieu_va_phuc_hoi_backendv1.md).

Mất mạng khi tạo backup: giao diện giữ nguyên số ngày và khóa của yêu cầu để
thử lại; kiểm tra danh sách trước khi tạo ý định mới. Không tự gửi lại khi tải
lại trang. Nếu đã nhận ID backup thì có thể mở lại chi tiết qua URL.

## 2. Dọn tệp dẫn xuất không còn sử dụng

Vào **Workspace → Vận hành → Dọn tệp** (quản trị viên).

1. Chọn xem trước, nhập lý do và tuổi tối thiểu từ 24 đến 8760 giờ.
2. Đọc số tệp, dung lượng, ngày sửa và mã ẩn danh của từng tệp.
3. Xác nhận đã đọc phạm vi rồi chọn **Xác nhận xóa**. Danh sách rỗng hoặc bản
   xem trước hết hạn không được gửi xác nhận mới.
4. Khi mất mạng, thử lại cùng preview/hash/key. Nếu server báo dữ liệu đã đổi,
   cần xem trước lại. Không chuyển thành xóa không điều kiện.
5. URL giữ ID biên nhận. Sau tải lại, thao tác `pending` đã được xác nhận có
   nút tiếp tục cùng ID/hash/key. Biên nhận `preview` chưa chứng minh đã xác nhận;
   người dùng phải xem trước lại. Kết quả phân biệt vừa xóa và đã vắng trước đó.

Server chỉ xét dẫn xuất của tác vụ kết thúc, không còn tham chiếu, đủ tuổi.
Tệp gốc, raw OCR, backup, namespace không biết và tệp vẫn được tham chiếu được
giữ. Còn job chạy/chờ hoặc vượt giới hạn kiểm kê sẽ báo lỗi thay vì xem trước
thiếu. Đây là dọn blob dẫn xuất; khác với dọn generation chỉ mục cũ.

## 3. Đọc đoạn tìm kiếm và nguồn

Vào **Bộ sưu tập → Chỉ mục & Tìm kiếm**, tìm thử rồi chọn **Xem đoạn và nguồn**.

- Xem đầy đủ văn bản hoặc bảng có header, ô gộp, chú thích; năm/trang chưa biết
  giữ là chưa xác định.
- Trước khi hiện nội dung trong ngăn chi tiết, FE kiểm lại phiên bản và quyết
  định xuất bản hiện hành. Nguồn đổi/thu hồi thì yêu cầu tìm lại; lỗi quyền, mạng
  và lưu trữ không bị chuyển thành dữ liệu rỗng.
- Có liên kết đến phiên bản biên soạn chính xác và nguồn OCR với revision/run/
  trang từ citation khi có đủ định danh đúng workspace/collection.
- Mở mục tài liệu bỏ qua để đọc lý do; mở chi tiết xếp hạng để xem trace thật.
  Điểm vector, từ khóa, RRF và rerank khác thang; không quy thành xác suất đúng.

## 4. Đánh giá truy xuất

Tại tab chỉ mục, chọn **Đánh giá RAG** (quản trị hoặc biên tập). Đây là trang
riêng, có liên kết về bộ sưu tập; snapshot được chọn có thể mở lại bằng URL.

1. Chọn generation hoàn tất đang phục vụ. FE đọc run và manifest, tự ghim ID/hash.
2. Nhập phiên bản bộ nhãn, người gán nhãn, K và ngân sách ứng viên (1–50,
   ứng viên không nhỏ hơn K).
3. Soạn 1–20 câu hỏi, tùy chọn nhóm. Với mỗi câu, tìm đoạn gợi ý, đọc đầy đủ
   nguồn rồi chọn các đoạn đáp án chuẩn. Không cần gõ chunk ID hay hash.
4. Nhãn mặc định là nháp. Muốn đánh dấu đã được người rà soát phải xác nhận
   riêng; đổi câu hỏi/nguồn/thiết lập sẽ xóa xác nhận này. Đổi nội dung câu hỏi
   cũng bỏ các đoạn chuẩn của câu đó để tránh dùng nhãn cũ vô ý.
5. Tùy chọn đo rerank, dùng mặc định ModelOps hoặc provider có capability rerank.
   Server giải quyết model/quyền và ghi usage. Không chứa API key trong FE.
6. Chạy để so sánh dense/hybrid và rerank nếu chọn trên cùng snapshot. Lỗi
   snapshot/gold/phạm vi/provider phải sửa rồi chạy lại; không tự đổi snapshot.
7. Xem tổng hợp và từng câu: số hoàn tất/lỗi, Hit@K, annotated recall/precision,
   MRR, thứ tự đoạn và trace. Nhãn rỗng để chỉ số chưa đo, không nhận điểm 0 giả.
8. Xuất JSON (request + result) hoặc CSV. CSV có BOM cho Excel và bảo vệ ô
   bắt đầu như công thức. Nội dung nhãn/nguồn trong tệp là dữ liệu của người dùng.

Giới hạn: mỗi lần gợi ý tối đa 50 đoạn, không bảo đảm bộ nhãn đã đầy đủ; người
gán nhãn cần đối chiếu. Phạm vi UI hiện là toàn bộ tài liệu đủ điều kiện trong
snapshot (`document_ids: null`), không tự suy scope từ các đoạn đã chọn. Không
gán năm tự động. BE chưa có lịch sử đánh giá lưu server; báo cáo chỉ trong phiên,
cần xuất trước khi rời trang. Đây là đánh giá truy xuất, chưa đánh giá độ đúng/
mức bám nguồn câu trả lời, chưa phải bằng chứng chất lượng thực tế hoặc cổng duyệt.

## Trạng thái kiểm chứng

Xem [báo cáo Context679](../bao_cao/context679/REPORT.md) để biết lệnh, kết quả và
giới hạn. Các ảnh minh họa dùng dữ liệu tổng hợp, không phải báo cáo chất lượng QNU.
