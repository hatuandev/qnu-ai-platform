# 33 — RAG policy, metadata, context và kiểm chứng backendV1

### Bổ sung896: tự nhận diện thông tin khi đăng ký

Người dùng không cần nhập hay đánh dấu metadata. Khi mở đăng ký, server đọc lại
nguồn của bản biên soạn đã hoàn tất, nhận diện giá trị có căn cứ và trả bản xem
trước gắn hash. Bấm tạo tài liệu/thêm phiên bản lưu đúng thông tin đó vào bản nháp.
Từ897, hộp đăng ký ẩn phần thông tin chỉ để xem; vẫn giữ bước nhận diện và kiểm
hash khi lưu. Chỉ hiện lựa chọn thêm phiên bản khi kho có tài liệu đích.
Các trường ngoài nhóm chuẩn lưu trong `attributes` JSON; không cần thêm cột DB.
Giá trị mâu thuẫn/không rõ giữ unknown. Năm dữ liệu, ngành và đợt chỉ áp dụng tại
đoạn/ô có căn cứ; không suy phạm vi toàn tài liệu từ một lần xuất hiện.

Đề xuất AI không được chấp nhận chỉ vì chuỗi giá trị xuất hiện trong nguồn: phải
đúng vai trò trường. Ví dụ “mùa tuyển sinh 2026” là năm dữ liệu, không là ngành
hay đợt. Luồng này không gọi thêm model, không sửa bản nguồn và không tự phê duyệt.
Hash thông tin tự nhận diện vẫn nằm trong bundle phiên bản và được kiểm khi duyệt.
API khai báo thủ công cũ giữ tương thích; giao diện đăng ký dùng luồng tự nhận diện.

### Bổ sung861: cần đọc gì, đã bao quát gì, còn thiếu gì

- Sau retrieval, nhận diện nhóm điều/mục/danh sách trong nguồn canonical đã ghim;
  giữ nội dung liên trang/liên phần và ranh giới tài liệu. Expansion tiếp tục lọc
  metadata/quyền, giữ budget và kiểm hash; không nạp OCR chưa được xuất bản.
- Khi câu tra cứu khớp tên mục có danh sách gạch đầu dòng, lấy thêm các block
  liên tục trong đúng mục, kể cả dòng nối ở trang kế tiếp. Dừng ở mục hoặc bảng
  tiếp theo. Các block chưa có trong ngữ cảnh vẫn được báo trong kế hoạch đọc.
- Kế hoạch đọc phân biệt unit đã cấp, chưa cấp và phạm vi chưa xác định. Không
  coi tăng TopK là bằng chứng liệt kê đủ; không mở rộng năm/ngành khi ít kết quả.
- Model trả câu trả lời và đánh giá từng yêu cầu trong cùng một lượt gọi.
  Backend kiểm citation và độ phủ cấu trúc; trả `coverage` cùng phần còn thiếu.
- Có quy định chung nhưng thiếu checklist thì trả phần chung có dẫn chứng, báo
  thiếu chi tiết. Không bịa danh mục hoặc khẳng định cả tài liệu không có dữ kiện.
- UI mở được nguồn còn thiếu citation để đối chiếu. Trạng thái đủ chỉ áp dụng
  phạm vi đã kiểm, không thay kiểm chứng ngữ nghĩa độc lập. Không retry tự động.

Phạm vi backendV1; workspace vẫn là biên giới quyền, collection/publication/source
revision vẫn được kiểm tra trước và sau inference. Không đổi frontend đang được
phát triển riêng hoặc cơ chế dữ liệu của backend cũ.

1. Editor đăng ký bản biên soạn với metadata gắn đoạn/hàng/ô và trích đoạn nguồn.
   Giữ riêng năm dữ liệu, năm ban hành, hiệu lực, ngành và đợt; không biết thì unknown.
2. Reviewer xem nội dung, báo cáo Compiler, metadata và hash; xác nhận metadata
   trong review_ack. Preview/approval/publication ghim cùng bundle; admin xuất bản
   qua quyết định đã xác nhận theo luồng hiện có.
3. Yêu cầu index generation mới để nhận chunker v2, quan hệ mục và metadata.
   Không sửa manifest/generation đang hoạt động hoặc tự thêm OCR chưa duyệt vào context.
4. Admin cấu hình rag_policy của trợ lý: dense/hybrid/rerank, phạm vi cố định,
   context window/budget và kiểm chứng. Hội thoại mới ghim policy; client cũ không
   làm mất policy khi cập nhật các trường giao diện đã có.
5. Khi hỏi, BE kết hợp scope cố định và scope tường minh của lượt hỏi; câu nối tiếp
   kế thừa scope lượt completed gần nhất. Lọc đúng chunk trước Qdrant/FTS TopK;
   không bỏ năm/ngành vì ít kết quả. Bản này chưa tự nhận diện mọi scope từ câu tự nhiên.
6. Sau tìm kiếm/rerank, thêm các đoạn cùng mục, cùng input/version/publication,
   cùng metadata scope trong budget. Giữ bảng, header và chú thích; kiểm lại hash.
7. ModelOps sinh statements/citation. Nếu bật judge, đối chiếu từng statement với
   nguồn được dẫn và trích đoạn nguyên văn. Observe trả kèm kết quả kiểm tra;
   enforce chặn câu chưa được hỗ trợ. Lỗi model/hạ tầng vẫn trả lỗi thật.
8. Kiểm lại quyền, nguồn, generation, provider và trạng thái lượt hỏi; lưu kết quả
   cùng trace/usage trong hội thoại. Khi nguồn bị thu hồi, lịch sử không tiếp tục
   phục vụ câu trả lời cũ như thể nguồn còn hiện hành.

Trợ lý mới mặc định dùng `dense`, lấy thêm tối đa một đoạn liền kề mỗi phía
(`context_window=1`) và tắt kiểm chứng. Hỏi đáp trực tiếp và snapshot cũ thiếu
policy dùng `context_window=0`. Hội thoại mới ghim policy đã lưu của trợ lý.

[Hợp đồng API và ví dụ cấu hình](../../backendV1/docs/rag-policies.md).
[Migration hiện hành](../../backendV1/docs/migrations.md).

Bài học Meilisearch áp dụng ở metadata và chẩn đoán thứ hạng; chưa cài engine,
chưa thêm fuzzy matching tiếng Việt/số/năm, chưa chuyển semanticRatio sang RRF.
Kế hoạch đọc theo cấu trúc và assessment yêu cầu đã có ở861. Query decomposition
thành nhiều truy vấn độc lập, phân trang liệt kê toàn kho và mở rộng phụ thuộc mọi
điều khoản pháp lý vẫn chưa triển khai; không coi độ phủ citation là đủ ngữ nghĩa.
