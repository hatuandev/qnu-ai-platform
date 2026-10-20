# Context572 — Benchmark RAG trên nguồn đang xuất bản

Đã chạy đủ bộ 64 câu đóng băng. **52/60 câu tri thức đạt (86,67%)**, vượt mục tiêu 85%; 43/50 câu có đáp án, 9/10 câu negative và 4/4 câu xã giao. Vẫn còn 8 FAIL, không phải toàn hệ thống đã đạt.

| Nhóm | Luna Context568 | Context572 |
| --- | ---: | ---: |
| Tri thức | 51/60 (85%) | 52/60 (86,67%) |
| Có đáp án | 43/50 | 43/50 |
| Negative | 8/10 | 9/10 |
| Xã giao, ngoài mẫu số | 4/4 | 4/4 |

Chuyển FAIL → PASS: P07, P08, P10, P16, X05, X08. Chuyển PASS → FAIL: P03, P05, P09, P15, X07. Tăng ròng một câu; không suy rằng mọi thay đổi đều tốt hơn hoặc đây là kết quả thống kê ổn định từ một lượt.

| ID chưa đạt | Nguyên nhân |
| --- | --- |
| N19 | Từ chối chung dù dòng CT-01 xác định giá trị 0 có chứng cứ và đại lượng tương ứng. |
| M05 | Không liệt kê được 12 mã và tên dù các dòng đều có trong nguồn. |
| P03 | Đúng thứ tự ba mức nguồn nhưng thiếu ràng buộc bản tổng hợp không vượt chứng cứ gốc. |
| P05 | Từ chối chung, không nêu dữ liệu dự kiến chỉ lập kế hoạch và không áp sang Ghi nhận 2026. |
| P06 | Chỉ trả ma trận E-A, thiếu mốc từ hạn ban đầu và điều kiện thông báo kiểm định trùng đợt khóa, quyết định gia hạn của Phòng Đào tạo. |
| P09 | Từ chối chung thay vì xác định / chưa có nghĩa công bố và phải bảo toàn unknown, không đổi 0. |
| P15 | Từ chối chung dù nguồn có ngày ban hành 18/10/2026 và bắt đầu áp dụng 01/11/2026. |
| X07 | Lỗi HTTP/timeout/runtime, không được tính là từ chối đúng. |


## Phạm vi phép đo

Nguồn `ks_rev_ca1e7f16d9e0`, index `idx_rev_967891af9d5d`, binding `bnd_fa71a57c9cf1`, collection `col_admissions`, epoch65; 262 points và hash payload giữ. Chạy benchmark trước khi tạo revision mới hoặc sửa lỗi tích hợp parser trong phiên này. RAG dùng sửa đổi Context570; parser Context571 chưa được áp vào nguồn phục vụ.

Query/gold SHA256 `44f56799e5a07ccba7e8711c1a1cd66e99beec18a60458e1ee509cde2167d235` giữ. Cùng rubric và real ASGI route như Context568; không dependency override/lifespan, không gọi judge LLM. Cấu hình chung Luna chính/Qwen dự phòng giữ; test scope server chỉ cho Luna như baseline để không trộn model. Fallback Qwen chưa được kiểm thử ở lượt này.

64 request gồm 63 HTTP200 và X07 HTTP503 `ALL_PROVIDERS_UNAVAILABLE`; log xác định upstream ReadTimeout. Không replay câu lỗi hoặc đổi thành từ chối đúng. Usage audit quan sát 119 Luna success/0 Qwen chat/0 fallback, còn failed timeout có trong request log nhưng không nằm trong 119 usage success; không coi 119 là toàn bộ số lần thử upstream. Prompt tokens quan sát 510405, completion28897, max prompt9727; không tự quy đổi thành chi phí.

90/90 citations trả ra đúng span/hash/source/index. Điều đó không chứng minh nội dung trả lời đầy đủ. Latency tri thức p50=539.66ms, p95=31609.65ms; tải provider/cache không được kiểm soát hoàn toàn. Không chạy retrieval ablation/Hit@K/Recall@K/MRR.

Nhãn là agent đối chiếu nguồn, chưa có human signoff độc lập; đây là tập phát triển đã dùng để sửa, không phải holdout. [Đối chiếu đủ 64 IDs](CASE_COMPARISON.md). Bằng chứng riêng được giữ ở `backend/storage/context572`, không đưa corpus/credentials vào Git.
