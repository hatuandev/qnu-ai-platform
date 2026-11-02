---
name: qnu-rag-evaluation
description: Build or independently review QNU RAG benchmark labels, fair retrieval experiments, source and year correctness, citation quality and measured reports. Use for evaluation or retrieval quality gates; not ordinary code formatting or UI-only edits.
---

# Đánh giá RAG độc lập

Mục tiêu là bằng chứng chất lượng và giới hạn của nó, không làm đẹp chỉ số. Đọc `backendV1/qnu/domains/evaluation`, tests/report hiện có, retrieval API và snapshot trước khi thêm runner. Có service evaluation không đồng nghĩa đã đo đủ mọi biến thể.

## Thiết lập thí nghiệm

1. Xác định câu hỏi sản phẩm, phạm vi dữ liệu, metric và tiêu chí chấp nhận trước khi tuning. Đọc [hợp đồng benchmark](references/benchmark-contract.md) khi tạo/chấm corpus hoặc so các retrieval mode.
2. Giữ raw source, source revision/hash, mapping gold IDs tới chunk/fact/block thật. Phân biệt draft, đã duyệt và holdout; người duyệt và phiên bản nhãn phải truy vết được. Không dùng expected answer nháp làm căn cứ chính thức.
3. Freeze cùng corpus/index/embedding/config, query set, scope/filter và môi trường đo. Baseline dense, hybrid và hybrid+rerank có tên rõ; hai biến thể sau dùng cùng candidate list để cô lập hiệu quả rerank. Nếu runtime chưa hỗ trợ mode nào, ghi NOT RUN/gap thay vì tạo kết quả giả.
4. Phân biệt PostgreSQL FTS, BM25, learned sparse; RRF/weighted RRF/DBSF/normalized score. Đổi sparse, K, chunk hoặc model là thí nghiệm riêng; không gộp nhiều thay đổi rồi quy toàn lợi ích cho rerank.
5. Câu gốc có trong corpus dễ leakage; tách original/paraphrase và câu hỏi thực độc lập, group theo chủ đề/nguồn để tránh train-test overlap. Câu negative năm chỉ negative đối với snapshot đã chốt; không coi năm 2027 luôn thiếu khi dữ liệu đã cập nhật.
6. Ghi đúng một kết quả mỗi query/strategy, kiểm tra missing/duplicate/unknown IDs, count completed/expected, ranked IDs/scores/provenance và failure status. Error không phải abstained/no-data; không bỏ lỗi khỏi mẫu để tăng điểm.

## Đánh giá và bàn giao

- Retrieval: Hit@K, annotated Recall@K, MRR@K; nDCG chỉ khi có relevance labels phù hợp. Candidate recall và context recall khác nhau; TopK không đo exhaustive enumeration.
- Answer: correctness, groundedness, citation support/resolvability, đúng năm/metric/đơn vị, refusal/clarification. Human labels hoặc judge có cấu hình/rubric rõ; judge không được tự phê duyệt dữ kiện hay tool. Groundedness không thay thế correctness.
- Vận hành: cùng ranh giới latency, warmup/concurrency/cache regime, p50/p95, error/timeout/fallback và observed usage/cost. Thiếu phép đo để null/NOT RUN, không ghi số ước lượng như quan sát.
- Báo từng nhóm câu, số đã chấm, failures và baseline; ghi provenance test/result. Không nói toàn suite PASS khi còn baseline failure hay chỉ có fake adapter tests.
- Chạy regression tenant/scope/cache/snapshot, wrong year, missing citations, malformed rerank, conversation follow-up và phép tính khi liên quan. Dùng [gate chung](../../rules/verification.md).

Live benchmark chỉ được chạy trong môi trường và phạm vi dữ liệu/provider đã được phép; offline evaluator chỉ chấm log, không chứng minh đã gọi Qdrant. Không reindex/publish hoặc chuyển active nguồn để khớp benchmark. Bàn giao cải thiện đo được, regression, giới hạn nhãn và quyết định tiếp theo; không kết luận production readiness từ bộ học tập.
