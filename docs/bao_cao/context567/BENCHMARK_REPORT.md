# Context567 — Sửa lỗi RAG và chạy lại benchmark 85%

**Đạt mục tiêu trên bộ benchmark Context566: 51/60 (85,0%) câu tri thức**, trước sửa 34/60 (56,67%). Riêng câu có đáp án: 44/50 (88,0%), trước 28/50 (56,0%). Xã giao: 4/4 (100,0%), không cộng vào mẫu số 60.

Đây là phép đo trên bộ đã biết lỗi và dùng để sửa mã, chưa phải holdout hoặc chứng nhận chất lượng chung. Full backend vẫn **FAIL** vì 18 lỗi nền theo đúng ID/nhóm nguyên nhân lịch sử; không gọi toàn hệ thống APPROVED.

## Kết quả cuối

| Nhóm | Context566 trước sửa | Context567 lượt cuối |
|---|---:|---:|
| Ô số liệu và tên/mã | 12/16 (75,0%) | 16/16 (100,0%) |
| Hàng nhiệm vụ/trạng thái | 1/4 (25,0%) | 4/4 (100,0%) |
| Nhiều chỉ số/năm/mã | 2/5 (40,0%) | 5/5 (100,0%) |
| Liệt kê đầy đủ | 0/1 (0,0%) | 1/1 (100,0%) |
| Hỏi tiếp nối | 2/8 (25,0%) | 8/8 (100,0%) |
| Văn bản/ngoại lệ/chú thích/hình | 11/16 (68,75%) | 10/16 (62,5%) |
| Từ chối/làm rõ/tiền đề sai | 6/10 (60,0%) | 7/10 (70,0%) |
| Xã giao/meta, ngoài mẫu số | 4/4 (100,0%) | 4/4 (100,0%) |
| **Tri thức, ngưỡng >=51/60** | **34/60 (56,67%)** | **51/60 (85,0%)** |
| **Có đáp án, ngưỡng >=43/50** | **28/50 (56,0%)** | **44/50 (88,0%)** |

Hoàn thành đủ 64 case IDs, đúng thứ tự, không thiếu/trùng. HTTP: {"200": 64}. Mọi HTTP/timeout/schema error đều FAIL, không chuyển thành từ chối đúng. 20 ca FAIL cũ thành PASS; 3 ca PASS cũ thành FAIL. Chi tiết đủ 64 IDs ở [CASE_COMPARISON](CASE_COMPARISON.md).

Các ca cuối chưa đạt: **P03; P06; P07; P08; P11; P15; X05; X08; X09**. Đây vẫn là FAIL theo rubric gốc, kể cả khi không bịa ra con số. Lý do và giới hạn ở cuối bảng đối chiếu.

## Những gì đã sửa

1. Phân biệt đại lượng và đơn vị trong câu tự nhiên; thu đủ yêu cầu phối hợp nhiều cột. Ý hỏi mới thắng ràng buộc cũ trong câu nối tiếp.
2. Giải tên/mã và hàng tổng từ chính JSON/canonical row của nguồn đang xuất bản. Không dùng mã ngành catalog cũ làm bằng chứng định danh; không coi số 0 đơn lẻ là mã. Tên giống nhau nhiều nguồn vẫn cần làm rõ.
3. Bảo toàn năm và scope của câu hỏi trước; chỉ sửa địa chỉ trích dẫn lịch sử khi có duy nhất một literal user quote. Không tạo fact từ lời trả lời trước.
4. Bảng phụ chọn được trường text/ngày/trạng thái; liệt kê identity lấy đủ hàng nguồn được xác minh, giữ mã nguyên văn và không bị giới hạn TopK. Hai lượt chọn schema độc lập không được tự tạo giá trị.
5. Khôi phục caption/hình, công thức và điều kiện liên quan từ cùng source units. Hàng tóm tắt bổ sung không vượt thứ hạng đoạn quy định đầy đủ. Bằng chứng luôn đi theo nhóm phụ thuộc nguyên vẹn; không tăng cấu hình K/context.
6. Search excerpt phải ánh xạ duy nhất về canonical block của đúng binding/index/source/hash. Audit và citation dùng body nguồn thực, không dùng prefix trang/heading làm quote. Với body ngắn, model chỉ chọn proof ID và phán định từng mệnh đề; server gắn quote nguyên văn. Không nhận một summary trái với atomic verdicts, không đổi verdict âm thành dương. Body dài giữ exact-subquote contract.
7. Ký hiệu chưa có định nghĩa giữ unknown, không thành số 0 hoặc fact định lượng. Hàng có trường chưa rõ không làm semantic supplemental proof để vượt guard.

Không có mã ca benchmark, giá trị gold hoặc từ điển tên chương trình của tài liệu trong logic ứng dụng mới. Không sửa parser/nguồn/chỉ mục để làm đẹp kết quả.

## Phép đo và mô hình

Lượt cuối 20/10/2026 15:36:27 đến 20/10/2026 15:41:44 giờ Việt Nam, qua TCP backend local thật, actor development có quyền hiện hành. Không mock retrieval/model ở benchmark. Primary vẫn `qwen3.5-9b`; chuỗi fallback hiện hành giữ nguyên. Usage thực tế:

| Model | Status | Fallback | Calls |
|---|---|---|---:|
| qwen3.5-9b | success | Không | 109 |

Lượt cuối quan sát 109/109 lần gọi Qwen thành công, không dùng model dự phòng; chính sách dự phòng hiện hành giữ nguyên. Không gọi LLM để chấm; ô số liệu đối chiếu chính xác tọa độ/giá trị và trích dẫn, phần diễn giải đối chiếu nguồn/rubric offline bởi Codex. Gold/rubric chưa được người duyệt độc lập xác nhận.

Citation resolvability: **93/93**. Trích dẫn giải được chưa đủ chứng minh mọi diễn giải đúng. P50/P95 tri thức: 676.83/21464.47 ms; không suy SLA từ lượt này.

## Tính công bằng và dữ liệu giữ nguyên

- Query/gold SHA256: `44f56799e5a07ccba7e8711c1a1cd66e99beec18a60458e1ee509cde2167d235`; giữ nguyên câu hỏi, gold, rubric, 60+4 và hai ngưỡng từ trước inference.
- Giữ collection `col_admissions`, binding `bnd_fa71a57c9cf1`, source `ks_rev_ca1e7f16d9e0`, index `idx_rev_967891af9d5d`, generation `vg_a6e3190d11af`, epoch65.
- Canonical hash `d466b624e1f873d0aae89ef319dc3d745088dfd9e9aeaa87fd09b61e799a604b`. 262 chunks, 368 facts, 262 vector points và payload seals trước/sau giữ nguyên; source/config/code/vector seals kiểm trong từng lượt.
- Model/provider/embedding/reranker/retrieval config giữ nguyên. Không reindex, republish, thay Quality Gate, restart thủ công hoặc deploy. Backend development tự reload mã theo cấu hình có sẵn.
- Cache physical/config không xóa/đổi. Namespace code đổi từ verified-answer-v2 sang v3/v4/v5 theo từng sửa proof contract để không dùng lại câu trả lời cũ. Vì vậy cache hit/miss và độ trễ không phải thí nghiệm cache đối chứng.

## Toàn bộ các lượt

| Lượt | Tri thức | Có đáp án | Ý nghĩa |
|---|---:|---:|---|
| Context566 | 34/60 (56,67%) | 28/50 (56,0%) | Baseline bất biến |
| Context567 benchmark-1 | 51/60 (85,0%) | 45/50 (90,0%) | Còn lỗi quote thiếu span và điều kiện bị chặn |
| Context567 benchmark-2 | 52/60 (86,67%) | 45/50 (90,0%) | Schema errors và diễn giải thừa vẫn FAIL |
| Context567 benchmark-3 | 51/60 (85,0%) | 44/50 (88,0%) | Lượt cuối trên mã bàn giao |

Không chọn từng response tốt từ nhiều lượt để ghép thành kết quả cuối. Evidence tất cả lượt giữ riêng dưới Storage ignored.

Đối soát cuối sửa điểm X05/X08 của hai lượt đầu từ PASS sang FAIL: từ chối chung chưa đủ lý do đơn vị/đại lượng theo rubric đã có. Giữ bản chấm ban đầu riêng để truy vết; không thay gold hoặc nới tiêu chí. Kết quả cuối chỉ vừa chạm ngưỡng 85%, chưa có biên an toàn lớn.

## Kiểm thử và cleanup

Ruff 36 file: PASS/exit0. Kiểm tra tập trung 118 PASS và hợp đồng dữ liệu 49 PASS/exit0 (có test trùng, không cộng thành số test độc lập). Full cuối 2785 PASS/18 FAIL/17 SKIP, 23 subtests PASS, exit1. Đối chiếu đúng test IDs: 38 case thêm, không ID cũ mất/đổi trạng thái, không có FAIL mới. Xem [VALIDATION_REPORT](VALIDATION_REPORT.md) cho bằng chứng và lỗi nền.

DB test riêng đã kiểm quyền sở hữu trước khi dọn và xác nhận không còn. Lệnh xóa Storage runtime `context567-runtime-282bc5e59949` bị kiểm duyệt tự động chặn với lý do “blocked by policy”; còn giữ 2.969 file, khoảng 43,9 MB. Không thử lại hoặc vượt chặn. Hội thoại/message/gap chỉ do từng benchmark tạo đã được dọn và xác minh; usage audit và bằng chứng private giữ để đối soát. Không xóa dữ liệu người dùng hay runtime cũ.

NOT RUN: retrieval ablation dense/hybrid/rerank, Hit@K/Recall@K/MRR, tải đồng thời/SLA, frontend build/UI và production. Không commit, stage, push, reindex hoặc xuất bản lại. Các thay đổi Context564–566 có sẵn được giữ.
