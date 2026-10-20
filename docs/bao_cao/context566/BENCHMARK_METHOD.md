# Context566 — Phương pháp benchmark RAG

Người dùng yêu cầu đo mục tiêu 85% trên nguồn đang xuất bản. Đây là đánh giá hành vi đầu cuối của trợ lý `admissions`, qua HTTP TCP thật tới backend local; không phải benchmark riêng một model hoặc một thuật toán retrieval.

## Bộ đo chốt trước khi chạy

60 câu tri thức: 50 câu có đáp án trong nguồn và 10 câu cần từ chối, làm rõ hoặc sửa tiền đề sai. Có thêm 4 câu hội thoại, nằm ngoài mẫu số 85%. Câu hỏi, rubric, tọa độ nguồn và đáp án được đóng băng trong Storage riêng trước lượt gọi đầu tiên; không chỉnh câu hỏi sau khi thấy kết quả.

| Nhóm | Số câu |
|---|---:|
| Ô số liệu Bảng 1, mã/tên, năm, đơn vị, chỉ tiêu/ghi nhận/ước tính/tỷ lệ | 16 |
| Hàng ở bảng phụ, nhiệm vụ, trạng thái | 4 |
| Nhiều đối tượng/năm/chỉ số, liệt kê và dòng tổng | 6 |
| Hội thoại nối tiếp, gồm 2 lượt mở đầu và 6 lượt phụ thuộc | 8 |
| Văn bản, chú thích, footnote, hình, điều kiện và ngoại lệ | 16 |
| Thiếu năm/mã/đơn vị, unknown và tiền đề sai | 10 |
| Hội thoại xã giao, chấm riêng | 4 |

Không dùng bộ tuyển sinh 20 câu cũ: đáp án của bộ đó thuộc tài liệu khác, không có ánh xạ gold tới snapshot hiện tại. Cũng không lấy câu trả lời của model làm đáp án chuẩn hoặc dùng độ trùng từ làm chất lượng thực tế.

## Tiêu chí 85%

Một câu tri thức chỉ PASS khi trả lời đầy đủ yêu cầu, đúng đối tượng, năm, vai trò chỉ số, đơn vị, giá trị, điều kiện và phạm vi; trích dẫn phải giải được tới đúng nguồn xuất bản và hỗ trợ kết luận. Câu có đáp án mà bị từ chối vẫn FAIL. Câu nhiều ý chỉ trả lời một phần vẫn FAIL. HTTP 200 không đồng nghĩa PASS.

Hai điều kiện phải đồng thời đạt:

- Ít nhất 51/60 câu tri thức PASS, tương đương 85%.
- Ít nhất 43/50 câu có đáp án PASS, tương đương 86%; ngưỡng nguyên nhỏ nhất đạt yêu cầu 85%. Điều này tránh dùng câu từ chối dễ để làm đẹp tổng điểm.

Lỗi HTTP, timeout hoặc provider được giữ trong mẫu số và chấm FAIL. Với câu không thể kết luận, phải từ chối/làm rõ hoặc sửa tiền đề một cách có căn cứ; không chấp nhận số bịa hay dữ liệu năm khác.

Chấm tự động exact cell/fact ID và citation span trước; sau đó đối soát câu diễn giải, negative và nhánh trả lời bằng ô nguồn theo rubric đã chốt. Chấp nhận diễn đạt tương đương, không bắt đúng mẫu trình bày hay một nhánh triển khai nội bộ. Lưu riêng nhãn tự động và nhãn cuối.

Nhãn do Codex kiểm theo nguồn trước inference; **chưa được người dùng/người duyệt độc lập xác nhận và không phải holdout**. Có một số chủ đề đã dùng trong kiểm thử phát triển Context565. Kết quả là benchmark chẩn đoán trên một tài liệu mô phỏng, không là chứng nhận chất lượng toàn nền tảng.

## Nguồn và cấu hình cố định

- Collection `col_admissions`, epoch 65.
- Binding `bnd_fa71a57c9cf1`, source `ks_rev_ca1e7f16d9e0`, index `idx_rev_967891af9d5d`.
- Canonical SHA-256 `d466b624e1f873d0aae89ef319dc3d745088dfd9e9aeaa87fd09b61e799a604b`.
- 262 chunks, 368 facts; gold ánh xạ vào canonical blocks, hàng/cột JSON và fact thật của cùng revision.
- Model chính `qwen3.5-9b`; fallback sẵn có `cx/gpt-6-luna`. Không thay model, ưu tiên, timeout hoặc chính sách dự phòng. Fallback quan sát được sẽ báo riêng.
- Embedding generation hiện hành `vg_a6e3190d11af`: `bge-m3`, 1024 chiều, cosine. Reranker cấu hình `bge-reranker-v2-m3`.
- Retrieval policy giữ nguyên: dense 20, lexical 20, fusion 30, context 5, tối đa 36.000 ký tự. Evidence policy vẫn ở trạng thái cấu hình sẵn; không bật một nhánh khác để đạt điểm.
- Concurrency 1, không warmup riêng, không retry; cache hiện hữu được giữ, không xóa. Latency đo từ trước gửi request tới sau nhận/giải JSON toàn response.

Luồng fact-first có thể trả lời số liệu không cần LLM/vector search; đó là hành vi sản phẩm hiện tại. Không gọi ca đó là bằng chứng đã chạy dense retrieval. Chỉ số Hit@K/Recall@K/MRR và so sánh dense/hybrid/rerank **NOT RUN**: lượt đo này không có ranked candidate list đủ để chấm các chỉ số đó.

## An toàn và bằng chứng

Đã kiểm cấu hình DB, MinIO và Qdrant local trước khi chạy. Đọc nguồn và cấu hình trong transaction READ ONLY; lưu hash hàng nguồn/index/assistant/provider và hash mã liên quan. Kiểm snapshot/cấu hình trước từng câu. Chỉ gửi chat kiểm thử bằng actor phát triển có quyền; không migration, thay schema, ghi source, tạo revision, reindex, đổi publication, restart hay deploy.

Cuối lượt đối chiếu seals nguồn/cấu hình và vector generation, số point và payload hash Qdrant. Chỉ dọn conversation/message mới thuộc lượt đo và knowledge gap mới khớp câu đã gửi, không đụng hội thoại/gap có trước; giữ usage audit và artifact benchmark làm bằng chứng.

Artifact riêng: `backend/storage/context566/manifest-frozen.json`, `queries-gold-frozen.json`, `source-private.json`, `responses-private.json`, `usage-private.json`, `cleanup.json`, các seals trước/sau và báo cáo chấm. Corpus/câu hỏi đầy đủ không được sao chép vào tài liệu Git.

Không sửa mã ứng dụng, không commit/push. Full Pytest/lint ứng dụng không chạy lại vì không đổi hành vi; kết quả full backend Context565 là lịch sử FAIL với 18 lỗi nền, không được đổi nhãn thành PASS bởi benchmark này.
