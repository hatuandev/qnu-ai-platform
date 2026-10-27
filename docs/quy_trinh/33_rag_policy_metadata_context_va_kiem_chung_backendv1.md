# 33 — RAG policy, metadata, context và kiểm chứng backendV1

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

Mặc định tương thích là dense, không mở rộng context, judge off. Bật tính năng
mới cần cấu hình tường minh; metadata/context mới cần generation được tạo và
duyệt theo luồng hiện có. Đổi policy cần hội thoại mới, không đổi ngầm snapshot cũ.

[Hợp đồng API và ví dụ cấu hình](../../backendV1/docs/rag-policies.md).
[Migration hiện hành](../../backendV1/docs/migrations.md).

Bài học Meilisearch áp dụng ở metadata và chẩn đoán thứ hạng; chưa cài engine,
chưa thêm fuzzy matching tiếng Việt/số/năm, chưa chuyển semanticRatio sang RRF.
Query decomposition, structured retrieval và tính toán xác định thuộc giai đoạn sau.
