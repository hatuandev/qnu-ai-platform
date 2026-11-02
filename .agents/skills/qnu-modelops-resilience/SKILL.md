---
name: qnu-modelops-resilience
description: Configure or review QNU AI providers, model selection, protected credentials, inference contracts, fallback, quotas and usage in the existing ModelOps subsystem. Use for model/runtime integrations, not general UI styling or parsing.
---

# ModelOps theo cấu hình thực tế

Đọc `backendV1/qnu/domains/modelops`, `backendV1/qnu/adapters/providers`, schema và nơi runtime phân giải model; tìm file thực trước khi đặt tên lớp. Đọc [quy định bảo mật](../../rules/security-and-git.md) khi liên quan credential/network, và [gate](../../rules/verification.md) khi kiểm thử.

1. Phân biệt provider/endpoint, credential, model/capability và task routing theo schema thật. Giữ model động từ DB/UI; chuyển preferred provider/model qua assistant/workflow/DAG đến adapter trong phạm vi quyền, không thay model cũ âm thầm.
2. LLM credential đi qua ModelOps DB được bảo vệ và quy trình hiện có; không thêm .env key để override UI. DTO/log/error chỉ trả trạng thái an toàn; test ở API/handler/runtime, không chỉ helper masking. Tenant không được chọn tùy ý secret/config của máy chủ để gửi tới endpoint riêng.
3. Discovery chỉ cho biết model được liệt kê. Verify cần request inference tối thiểu đúng capability và schema: vector số hợp lệ/dimension quan sát, rerank index/score hợp lệ, chat content theo protocol, OCR layout theo hợp đồng. Không seed verified/cost/dimension giả.
4. Probe/discovery/runtime dùng nhất quán endpoint/path, auth scheme, timeout và egress. Chặn đổi host/redirect ngoài policy; quyền private-network lấy từ server, không từ prompt/boolean client hay loại adapter. Thiếu cấu hình/auth, response sai và timeout phải phân biệt; không trả danh sách rỗng hoặc đáp án giả thay lỗi.
5. Connection/model disabled phải bị loại ở mọi tác vụ. Đổi endpoint/model/revision ảnh hưởng danh tính inference phải vô hiệu kết quả kiểm định liên quan; embedding phải tương thích active index generation, không repoint tức thì qua cờ do caller tự khai.
6. Circuit breaker/retry/backoff/concurrency/timeout lấy từ chính sách vận hành thật. Giới hạn tổng budget và tránh retry nhân tầng. Không cố định ngưỡng lỗi/cửa sổ chung cho cloud chat, OCR và embedding batch.
7. Fallback theo task/scope/capability đã được phép; phân biệt chuyển provider, template, bỏ rerank và no-answer. Lỗi quota/quyền/tenant/cancellation không được mở rộng quyền. Bảo toàn failure trace khi primary hỏng; nếu không còn lựa chọn hợp lệ, trả lỗi AppException/RFC7807 phù hợp.
8. Quota kiểm tra trước thực thi; usage ghi token/latency/units từ quan sát. Giá và chi phí chỉ tính theo tariff có nguồn và thời điểm, không ghi 0 như thể đã đo khi thực tế chưa biết. Secret rotation audit actor/đối tượng/lý do/thời điểm, không ghi key hay tuyên bố thu hồi upstream nếu chưa làm.

Kiểm chứng: adapter payload/auth, response malformed, disabled, wrong capability, expiry/quota, timeout/cancellation, fallback policy, secret không lộ, cross-tenant, probe/runtime parity và thay model không phá index. Live call chỉ khi môi trường/dữ liệu/provider được phép; dùng fake HTTP cho regression thông thường.
