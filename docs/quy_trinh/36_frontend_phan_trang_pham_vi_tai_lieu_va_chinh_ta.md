# 36 — Frontend phân trang, phạm vi tài liệu và kết quả chính tả

Áp dụng cho `frontendV1/` và `backendV1/`, sau quy trình35. Triển khai theo
ba ưu tiên F1–F3 của [kiểm kê680](../bao_cao/context680/FE_BE_INVENTORY.md).

## 1. Xem toàn bộ danh sách và lịch sử

Trong kho tài liệu, các tab Compiler, tài liệu biên soạn và chỉ mục có nút
Trang trước/Trang sau, cùng bộ chọn10/20/50/100dòng. Trang chi tiết tài liệu
có phân trang phiên bản và lịch sử xuất bản. Tab rà soát Compiler có phân
trang các lần review và giữ mã lần review được chọn trên URL.

Trang và kích thước trang nằm trong URL; đổi tab danh sách hoặc kích thước
trang sẽ về trang1. Trang cuối rỗng vẫn cho quay lại. Nếu trang Compiler tải
lỗi, có thể tải lại hoặc quay lại trang trước.

Các API này trả mảng, chưa có tổng số. FE lấy thêm một dòng để biết có trang
tiếp theo; chọn100dòng thì gọi100dòng và thêm1dòng ở offset kế tiếp. Không
hiển thị tổng số trang suy đoán. Bộ lọc tiêu đề tài liệu chỉ lọc trang đang
mở. Dữ liệu thêm/xóa trong lúc phân trang offset có thể làm dịch chuyển hàng;
nút Làm mới đọc lại trang hiện tại, không tạo snapshot cố định.

BE list Compiler nhận thêm `offset >= 0`, mặc định0, giữ `limit`1–100 và
quyền workspace/collection như trước. Không cần migration. Ví dụ lấy lượt
101trở đi bằng `limit=20&offset=100` trên endpoint list Compiler hiện có.

## 2. Chọn tài liệu cho tìm kiếm và đánh giá

Ở Tìm kiếm thử, chọn **Chọn tài liệu**, tìm theo tiêu đề trong trang hiện
tại, thêm các tài liệu cần dùng và chuyển trang khi cần. Tối đa100tài liệu;
không thêm trùng. Nút Bỏ gỡ từng lựa chọn. Không có lựa chọn nghĩa là toàn
bộ tài liệu đủ điều kiện trong collection.

Danh sách cho phép chọn tài liệu đã đăng ký; server vẫn quyết định bản nào
đang xuất bản và có thể truy xuất. Tài liệu được chọn nhưng chưa đủ điều kiện
không làm mở rộng phạm vi sang tài liệu khác. Lỗi tải danh sách cũng không
tự xóa lựa chọn. Khi đổi lựa chọn, kết quả tìm kiếm cũ được bỏ, kể cả phản
hồi đang tải về muộn. Lựa chọn ở biểu mẫu không được lưu bền vững qua F5.

Ở đánh giá RAG, chọn phạm vi riêng cho từng câu hỏi. Chỉ thêm tài liệu có
trong manifest của snapshot đang đánh giá. Cùng `document_ids` được gửi vào
cả tìm đoạn gán nhãn và chạy đánh giá. Phản hồi tìm đoạn khác snapshot hoặc
ngoài tài liệu đã chọn bị từ chối. Đổi phạm vi xóa gold cũ và bỏ xác nhận đã
rà soát nhãn; cần gán nhãn lại. JSON/CSV xuất báo cáo giữ phạm vi tài liệu.

Đánh giá vẫn cần người gán nhãn kiểm tra độ đầy đủ; chức năng này không tự
chứng minh chất lượng model hoặc tính đúng đắn của câu trả lời.

## 3. Mở lại kết quả kiểm tra chính tả

Khi tạo lần kiểm tra từ màn hậu OCR, URL giữ `revisionId`, `runId`,
`subTab=review`, `tab=ocr` và `checkId`. Giữ URL này để mở lại sau F5. FE đọc
biên nhận bằng GET trong đúng workspace/collection/source/revision/run;
không tự gửi lại yêu cầu chạy model. Lần đang chạy được đọc lại trạng thái;
lỗi quyền/không tìm thấy được hiển thị như lỗi.

Kết quả hiện đoạn văn, vị trí trang, từ sai, từ đề xuất và lý do. Chỉ áp dụng
khi phiên bản/hash trùng văn bản đang mở, đoạn và vị trí còn khớp, người gọi
có quyền sửa và bản nháp chưa lệch base. Nếu là kết quả cũ, chọn đúng phiên
bản văn bản để đối chiếu trước. Trạng thái chưa rõ/thất bại không được hiển
thị như kiểm tra thành công.

**Áp dụng vào nháp** chỉ cập nhật bản nháp trên màn hình. **Lưu thay đổi**
tiếp tục dùng API lưu hậu OCR có kiểm tra phiên bản/hash để tạo MD/JSON dẫn
xuất mới; OCR gốc được giữ nguyên. Bỏ qua đề xuất chỉ có hiệu lực trong lần
mở màn hình, chưa là quyết định lưu trên server. Kiểm tra chính tả dựa trên
văn bản và chưa đối chiếu ảnh gốc; không có đề xuất không có nghĩa OCR đúng.

Đổi revision hoặc run xóa deep link check cũ; đổi phiên đăng nhập không giữ
bản nháp/kết quả cục bộ của phiên trước. Link không thay thế quyền server.

## Giới hạn và kiểm chứng

Phạm vi này chưa làm collection answers playground, tải raw review, dashboard
QNU, lịch sử evaluation bền vững, streaming, feedback hoặc chia sẻ chatbot.
Không thay auth bypass, provider, credential hay quy trình xuất bản/index.
Kết quả kiểm tra của phiên này ghi ở báo cáo681; dữ liệu giao diện thử là
tổng hợp, không thay thế nghiệm thu với dữ liệu và model thật.
