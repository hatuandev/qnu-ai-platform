# Hợp đồng benchmark và cách dùng Reference Kit

## Phạm vi nguồn

Bộ người dùng cung cấp `RAG_Vibe_Coding_Hybrid_Search_Reference_Kit.zip` là tài liệu học, không phải đặc tả bắt buộc hay số đo đã chạy trên QNU. Không cần đường dẫn máy cá nhân để skill hoạt động; dùng bản được người dùng cung cấp hoặc corpus hiện có đã được phép.

Ở bản đã kiểm tra ngày 15/10/2026 có 82 chunk và 174 câu: 82 original, 82 paraphrase, 10 year-negative; tất cả nhãn câu hỏi là draft_needs_human_check, corpus chỉ 2026. Những con số này mô tả bản kit đó, không phải quy mô bắt buộc hoặc chất lượng corpus production. Không sao chép nguồn nội bộ vào Git.

Alpha=0.3 trong ghi chú paper là hệ số của sparse đã chuẩn hóa trong công thức alpha*sparse+dense, không là 30/70, không là hệ số RRF, không bảo đảm tối ưu tiếng Việt. K=30/30/30/5 chỉ là baseline thử nghiệm; dùng cấu hình thực và ablation.

## Snapshot và nhãn

Manifest thí nghiệm cần corpus/source/index revision/hash, chunking/parser/config, model/deployment/dimension quan sát, retrieval modes, filters, K tại từng bước, query/label version, quyền đọc và thời gian/môi trường chạy. Không ghi credential hay nguyên prompt riêng.

Với mỗi query: ID duy nhất, nội dung, nhóm/chủ đề, scope kỳ vọng, answerable theo snapshot, gold IDs và mức liên quan nếu có, source spans, review status/người duyệt. Gold có thể nhiều ID tương đương; nhãn chưa exhaustive chỉ cho annotated recall. Không dùng ID từ corpus khác khi chưa có mapping có kiểm chứng.

## Kết quả và tính công bằng

Một record mỗi (query_id, strategy), gồm ranked IDs (có thứ tự, không trùng), scope/snapshot, status, lỗi/fallback, thời gian từng stage và tổng cùng boundary. Answer correctness/abstention/citation label được chấm riêng, null khi chưa chấm. Không nhét raw corpus hay secrets vào report.

Giữ contract JSONL evaluator hiện có; nếu cần status/error/trace mở rộng thì quản lý ở sidecar có mapping, hoặc sửa evaluator cùng test. Không mặc định evaluator .NET trong kit chạy được trong repo Python. Có thể dùng CLI offline độc lập hoặc adapter Python tối thiểu khi cần, không thêm worker .NET vào runtime.

Thí nghiệm B (hybrid) và C (hybrid+rerank) lấy cùng fusion candidates trước rerank. A dense giữ thứ hạng dense. Tất cả dùng cùng snapshot/query/filters và chế độ cache; ghi riêng truy vấn embedding, retrieve, fusion, rerank, generation. Warmup không tính vào tập chấm. Báo missing/error records, không chỉ average của các request thành công.

## Các ca bắt buộc khi liên quan

- Tenant B hỏi nội dung A; quyền thay đổi sau cache hit; revision cũ/archived không lọt nguồn đang phục vụ.
- Năm N có nguồn, N+1 thiếu; bảng có nhiều năm, unknown year và bản sửa đổi. Không lấy năm ký làm năm mọi ô.
- Đúng query nhưng gold IDs thuộc snapshot khác; duplicate ranked ID; model thay dimension; reranker thiếu score/ID hoặc timeout.
- Liệt kê vượt TopK: set coverage, pagination và tổng số trong đúng scope; không gọi Recall@5 là exhaustive coverage.
- Follow-up chỉ năm N rồi rút gọn/giải thích/lọc; giữ source discriminator cho unknown year; không dùng assistant prose làm facts.
- Citation đúng ID nhưng quote/metric/đơn vị sai; projected khác achieved; công thức thiếu rule hoặc rounding policy đã duyệt phải từ chối tính.

Một test dùng fake HTTP là contract/regression PASS; live inference, chất lượng corpus và end-to-end production vẫn NOT VERIFIED cho tới khi có bằng chứng riêng.
