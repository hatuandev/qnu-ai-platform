# Context566 — Benchmark RAG trên nguồn đang xuất bản

**Chưa đạt mục tiêu 85%: 34/60 câu tri thức PASS (56,67%).** Riêng 50 câu có đáp án trong nguồn: 28 PASS (56%). Hoàn thành đủ 64/64 HTTP requests, gồm 4 ca hội thoại chấm riêng; không thiếu, trùng hoặc loại ca lỗi khỏi mẫu số.

Lượt chạy thật: 20/10/2026, 14:15:35–14:22:42 giờ Việt Nam (07:15:35–07:22:42 UTC), qua backend TCP local. Không sửa mã ứng dụng, đổi cấu hình model, reindex, xuất bản lại, restart, deploy, commit hay push.

## Kết quả

| Nhóm | PASS / Tổng | Tỷ lệ |
|---|---:|---:|
| Ô số liệu, mã/tên, năm, chỉ tiêu/ghi nhận/ước tính/tỷ lệ | 12/16 | 75% |
| Hàng nhiệm vụ/trạng thái ở bảng phụ | 1/4 | 25% |
| Nhiều mã/năm/chỉ số, liệt kê và dòng tổng | 2/6 | 33,33% |
| Hội thoại nối tiếp, gồm cả 2 lượt mở đầu | 2/8 | 25% |
| Văn bản, điều kiện, chú thích, footnote và hình | 11/16 | 68,75% |
| Từ chối/làm rõ/sửa tiền đề sai, chấm đầy đủ lý do | 6/10 | 60% |
| **Tri thức, mẫu số mục tiêu 85%** | **34/60** | **56,67%** |
| Hội thoại xã giao/meta, nằm ngoài mẫu số | 4/4 | 100% |

Ngưỡng đã chốt trước inference: ít nhất 51/60 câu tri thức và 43/50 câu có đáp án phải PASS. Hiện còn thiếu 17 ca PASS tổng và 15 ca PASS trong nhóm có đáp án. Không sửa câu hỏi/đáp án hay nới tiêu chí sau lượt chạy.

29/60 câu tri thức trả `insufficient_context`; trong đó **20 câu thực sự có đáp án trong nguồn**. Có 30 câu có đáp án được trả `answered`, nhưng M04 thiếu một chỉ số và F03 trả sai chỉ số, nên chỉ 28 câu đạt. Một negative khác, X05, cũng trả `answered` nhưng sai đơn vị.

## Vấn đề quan trọng nhất

1. **Sai đại lượng hoặc bỏ sót ý hỏi:** F03 đổi sang số ghi nhận nhưng vẫn trả chỉ tiêu của lượt trước. M04 hỏi cả chỉ tiêu và ghi nhận, hệ thống chỉ trả một cột. N02/N07/M03 có câu hỏi ghi nhận rõ ràng nhưng bị `METRIC_UNVERIFIED`. Đây là lỗi trả lời/hiểu truy vấn, không phải bằng chứng nguồn mất dữ liệu.
2. **Đơn vị trong câu tự nhiên chưa được bảo vệ đủ:** X05 hỏi theo lớp, hệ thống trả số SV mà không thông báo không có phép quy đổi. Citation khớp nguồn vẫn không làm câu trả lời đúng yêu cầu.
3. **Nhận diện theo tên và hàng tổng còn hở:** N15 bị phân tích thành mã ngành từ catalog cũ thay vì định danh của bảng nguồn; F05 hỏi chương trình có trong nguồn nhưng không tìm được fact. N11 bỏ lỡ hàng thật; M06 không trả được dòng tổng. N15 có bằng chứng cả response analysis và mã `MAJOR_NAME_TO_CODE` trong query router; chưa quy mọi ca khác về cùng nguyên nhân.
4. **Bảng phụ, liệt kê và diễn giải còn bị chặn quá mức:** N17/N18/N19/P06 bị `ROW_METRIC_SCOPE_UNRESOLVED`; M05/P07/P11/P13 bị `VISIBLE_ANSWER_NOT_SUPPORTED`; P01 bị `NUMERIC_GROUNDING_FAILED`. Gold đã có hàng/đoạn nguồn tương ứng. Chưa có ranked candidate list đủ để kết luận tất cả là do retrieval K hoặc context window.
5. **Ngữ cảnh nối tiếp và lời giải thích từ chối cần sửa:** F04 mất scope; F06–F08 nằm trong chuỗi có seed F05 đã thất bại, không phải ba nguyên nhân độc lập đã được cô lập. X08 từ chối đúng phần nghiệm thu 2027 nhưng thêm nhận định sai về quan hệ mã/tên. X07/X09 không bịa số nhưng chưa giải thích đúng căn cứ thiếu theo rubric.

Hướng xử lý tiếp theo là sửa từng lỗi ở tầng hiểu câu hỏi, nhận diện theo nguồn, lựa chọn ô, bảo toàn scope và trình bày blocker; giữ các kiểm tra toàn vẹn. **Lượt benchmark này không hạ guard/Quality Gate, không chỉnh model hoặc tăng context để che các lỗi.** Chưa triển khai các sửa chữa nêu trên.

## Cách đọc điểm negative và citation

X01/X02/X03/X04/X06/X10 PASS. X05/X07/X08/X09 FAIL theo tiêu chí cả câu hỏi và lý do, không chỉ kiểm có từ chối hay không:

- X05: đáp số theo SV cho câu hỏi theo lớp.
- X07: hỏi lại chỉ tiêu/ghi nhận thay vì nói ký hiệu chưa được định nghĩa.
- X08: có nêu cột dự kiến, nhưng kèm nhận định sai mã không khớp tên.
- X09: chặn chốt số Q, nhưng chỉ báo chưa đối chiếu chắc con số, không nêu không thể tính vì thiếu A. Đây là FAIL về độ đầy đủ của lý do; không phải bịa ra kết quả Q.

Nếu chỉ kiểm “có từ chối, không tạo đáp số” thì 9/10 negative được chặn. Ngay cả cho **toàn bộ 10 negative PASS**, tổng tối đa vẫn chỉ **38/60 = 63,33%**, không thể đạt 85%. Sự khác nhau trong chấm lời giải thích không đổi kết luận.

**57/57 citation** có binding/index/source/hash đúng và `canonical_markdown[start:end]` khớp quote. Đây là **khả năng giải trích dẫn**, không phải 100% correctness/groundedness. F03 và X05 là ví dụ citation hợp lệ nhưng trả sai phạm vi hỏi. Không có citation không được tự tính là citation PASS.

N14 được chấm tự động sơ bộ FAIL vì nhánh trả lời dùng `cells`, không dùng `claim_bindings`. Audit độc lập xác nhận đúng tên/hàng/cột/header/value và citation, nên chấm cuối PASS. Không đổi gold hoặc ép sản phẩm phải dùng một nhánh nội bộ cụ thể.

## Model, vận hành và giới hạn phép đo

- 64/64 HTTP 200, không exception/timeout ở client. HTTP 200 không được tính mặc định là câu trả lời đúng.
- Usage audit quan sát 131 record `success`: 128 lời gọi Qwen `qwen3.5-9b`, **3 lời gọi dự phòng `gpt-6-luna`** tại M05/P12/P13. Chính sách hiện có chọn Luna; không có thao tác đổi cấu hình. Đây là **benchmark luồng sản phẩm hiện tại, không phải Qwen-only**. Lý do chi tiết kích hoạt fallback chưa được xác minh từ artifact scoped này; không đoán là thiếu context.
- 361.832 prompt tokens và 28.737 completion tokens theo usage audit; không gọi thêm judge LLM để chấm. Không chuyển đơn giá giả định thành chi phí thực.
- Prompt lớn nhất được audit: 7.495 tokens/lời gọi. Không có HTTP `MODEL_CONTEXT_EXCEEDED` hoặc `EVIDENCE_CONTEXT_MISSING` trong lượt này. Dữ liệu này không hỗ trợ kết luận Qwen 32K thiếu context gây các ca FAIL; chưa phải kiểm tải hoặc kiểm đầy 32K.
- Latency 60 câu tri thức: p50 **2,414 giây**, p95 **33,939 giây**, lớn nhất **45,774 giây**. Concurrency 1; cache giữ nguyên, không có warmup riêng. Tính cả các câu thất bại về chất lượng.
- Snapshot hiện tại: 1 DOCX mô phỏng An Minh, 262 chunks/368 facts. Bộ câu hỏi có các chủ đề đã xuất hiện khi phát triển; chưa có nhãn duyệt độc lập bởi con người và không phải holdout. Không suy chất lượng toàn bộ PDF/DOCX hoặc tuyển sinh thật từ điểm này.
- Hit@K/Recall@K/MRR, ablation dense/hybrid/rerank và full backend suite trong task này: **NOT RUN**. Full Context565 lịch sử vẫn FAIL với 18 lỗi nền; không bị thay nhãn bởi benchmark.
- Chưa có lượt benchmark trước dùng chính xác cùng tập câu này, nên không tuyên bố tăng/giảm bao nhiêu điểm so với Context565.

## Dữ liệu và bàn giao

Đã kiểm môi trường development và endpoint DB/MinIO/Qdrant local trước khi chạy. Nguồn/index/assistant/provider seals trước/sau giống nhau; vector generation, số point 262 và hash payload Qdrant giữ nguyên. Hash mã RAG/knowledge được theo dõi cũng giữ nguyên. Việc so payload không phải phép băm lại toàn bộ giá trị vector.

Đã dọn **58 conversation**, message tương ứng và **29 knowledge gap** mới của lượt đo; kiểm READ ONLY xác nhận không còn dữ liệu chat/gap thử. Thread có trước và tần suất gap có trước được giữ; 131 usage audit và bằng chứng benchmark được lưu. Không tạo test DB/schema hoặc runtime Storage mới cần xóa.

Các lệnh đều chạy từ root repository, dùng Python trong `backend/.venv`; đường dẫn dưới đây là script đánh giá riêng, không là mã ứng dụng:

| Script | Exit code | Ý nghĩa |
|---|---:|---|
| `backend/storage/context566/preflight.py` | 0 | Cấu hình local và transaction READ ONLY đã xác minh |
| `backend/storage/context566/export_source.py` | 0 | Đọc snapshot/nguồn hiện tại, không ingest |
| `backend/storage/context566/freeze.py` | 0 | 64 IDs, gold và manifest chốt trước gọi thật |
| `backend/storage/context566/run_benchmark.py` | 0 | Đã thực hiện đủ 64 requests và cleanup, execution COMPLETE |
| `backend/storage/context566/adjudicate.py` | 0 | Ghi quyết định source-rubric offline, 0 judge LLM calls |
| `backend/storage/context566/score.py` | **1** | **Quality target FAIL**, có summary/nhãn đủ từng ID |
| `backend/storage/context566/verify_cleanup.py` | 0 | Kiểm chứng độc lập cleanup, usage còn nguyên |

Exit 0 của runner nghĩa là hoàn thành phép đo, không phải đạt 85%. Scorer cuối trả exit 1 vì thiếu ngưỡng; không chạy lại live để lấy kết quả khác. Có một lần xem metadata ban đầu bị lỗi encoding console, đã chỉnh UTF-8 cho việc đọc; không phát sinh request benchmark lặp.

[Phương pháp và tiêu chí chốt trước](BENCHMARK_METHOD.md) · [Từng test ID và kết quả](CASE_RESULTS.md).

Artifact đầy đủ lưu riêng tại `backend/storage/context566/`: manifest/query gold đã đóng băng, source spans và tọa độ thật, responses, nhãn tự động/nhãn cuối, summary, usage, cleanup-verified và seals trước/sau. Không sao chép nguyên corpus hoặc bí mật vào báo cáo Git.
