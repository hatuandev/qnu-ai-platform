# Quản trị quy đổi điểm có kiểm chứng

Áp dụng từ phiên 488. Một phạm vi ứng dụng chung; quyền máy chủ và biên collection,
binding, source/index revision, hash, trạng thái xuất bản vẫn bắt buộc.

Khi đưa vào sử dụng, BE và worker phải nhận cùng phiên bản code trước khi nhập/duyệt
quy tắc thật. Các writer metadata (publication/canary/backfill/GC) cần cùng khóa/refresh
để không ghi đè lịch sử. Phiên488 không chủ động restart hoặc deploy thay người vận hành.

## Thao tác trên giao diện

1. Mở **Kho tri thức → chọn kho → Quy đổi điểm** (`?tab=scores`).
2. **Nhập bản nháp**: chọn JSON đã chuẩn bị từ bảng nguồn, hoặc dán định nghĩa.
   Hỗ trợ một định nghĩa hoặc danh sách tối đa 25 mục mỗi lần; toàn lô lưu cùng
   transaction. File chọn không tự upload/lưu cho đến khi bấm Lưu bản nháp.
   Dấu duyệt trong file bị bỏ qua; máy chủ không nhận reviewer/status trong định nghĩa.
   Để sửa một bộ đã có, tạo ID phiên bản mới, không ghi đè lịch sử bản cũ.
3. Bấm tên quy tắc để mở trang chi tiết độc lập. Đối chiếu năm, phương thức,
   tổ hợp gốc/ánh xạ, bảng mốc, làm tròn, source/index/hash và trích đoạn.
4. **Tính thử**: nhập điểm và chọn tổ hợp (có tìm kiếm). Kết quả có hai mốc,
   công thức và dẫn nguồn; đây là preview, không tự duyệt hoặc kích hoạt.
5. **Duyệt**: người có quyền xác nhận đã đối chiếu và ghi lý do. Máy chủ kiểm tra
   lại toàn bộ ô, ánh xạ, quote và nguồn đang xuất bản. Người duyệt lấy từ session.
6. **Kích hoạt**: thao tác riêng sau khi duyệt; cần xác nhận/lý do. Chặn các bộ đang
   hoạt động trùng năm/phương thức nguồn/tổ hợp. Muốn thay bản cũ: ngừng dùng bản cũ
   trước, rồi kích hoạt bản mới.
7. **Ngừng dùng** đưa bản active về approved, giữ kết quả duyệt để có thể bật lại.
   **Thu hồi** ngừng sử dụng, giữ toàn bộ lịch sử và nguồn; muốn dùng nội dung sửa
   phải tạo bản nháp mới. Không xóa nguồn hoặc kết quả chat cũ.

Quyền: xem/tính thử `ai.knowledge.view`; nhập `ai.knowledge.update`;
duyệt/kích hoạt/ngừng dùng/thu hồi `ai.knowledge.review`.

## Hợp đồng máy chủ

- API quản trị: `/platform/v1alpha1/knowledge/collections/{id}/score-rules`;
  POST `/import`, `/{rule_id}/preview`, `/{rule_id}/actions`.
- Registry và audit lưu trong JSONB collection hiện có, khóa hàng + refresh ORM,
  `expected_version` và `request_id` chống ghi đè/lặp. Không cần migration mới.
- Sửa metadata collection thông thường không được ghi đè `score_conversion_registry`
  hoặc `score_conversion_rules`; nhập/duyệt không làm thay source/publication.
- Runtime chỉ dùng bản `active`, vẫn kiểm tra lại snapshot/hash/ô và trích dẫn mỗi
  lần tính. Không ngoại suy, clamp, eval công thức OCR hoặc để LLM tự tính.
- Metadata legacy `score_conversion_rules` giữ nguyên nhưng không tự có quyền active.
  CLI `build_conversion_rules --activate` bị chặn; CLI chỉ chuẩn bị JSON nháp,
  không thay thế danh tính/phê duyệt thật. Import UI bỏ dấu duyệt cũ, phải duyệt lại.
- Runner dry-run482 cũ dùng overlay legacy và kiểm tenant không còn là acceptance
  cho vòng quản trị mới. Dùng preview/API và tests mới; không giả active để làm runner xanh.
- ROUND_HALF_UP ở điểm giữa là chính sách vận hành user xác nhận; không phải câu chữ
  được tự thêm vào văn bản gốc. Cần người duyệt đối chiếu khi áp dụng cho bộ khác.

## Hai hành vi RAG đi kèm

- Explain/reformat ngoài enumeration: tái tra câu hỏi trước trên publication hiện
  tại, không dùng prose của assistant làm bằng chứng; trình bày gạch đầu dòng ngắn.
- Fact chưa xác minh năm: đối chiếu hàng/header/đoạn applicability cùng nguồn,
  chọn phạm vi năm trước chọn ô, audit độc lập. Không suy năm từ filename/ngày ký,
  không ghi ngược năm vừa suy vào fact/source và không tự reindex.
- Các cách ghi khác nhau cho cùng dữ liệu/mùa/ngành phải được cảnh báo kèm nguyên
  văn; không biến NFC thành xác nhận OCR. Khác phương thức/mã ngành hoặc so sánh
  nhiều năm không tự trở thành xung đột.

Chưa có dữ liệu cấu hình không được hiển thị bộ quy tắc mẫu. Không coi kiểm thử
helper hoặc vài câu hỏi là chứng nhận đúng toàn bộ 82 câu hay đủ điều kiện công bố.
