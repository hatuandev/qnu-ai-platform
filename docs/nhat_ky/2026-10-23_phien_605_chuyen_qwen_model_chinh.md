# Phiên605 — Chuyển Qwen3.5 9B làm model chính

Ngày 23/10/2026. Người dùng yêu cầu chuyển sang Qwen vì ngân sách token Luna gần hết; cho biết trước đây 9router bật Token Saver. Ngoại lệ được phép trong605 là cập nhật cấu hình model đang chạy qua API hiện có. Không mở rộng sang sửa code, đổi credential, provider, dữ liệu tri thức hoặc publication.

## Thay đổi

- ModelOps system defaults: primary provider `prov_rtx5090_vllm`, model `qwen3.5-9b`, chat mode `single`, chain chỉ còn Qwen, không tự dự phòng sang Luna.
- Trợ lý `admissions` có cấu hình riêng ghim Luna, nên đổi preferred provider/primary model sang cùng Qwen; fallback provider/model đặt null. Giữ temperature0.2, max_tokens5000, thinking_budget0 và phần cấu hình khác.
- Không thay provider default model `bge-m3`, embedding/reranker/OCR defaults, key, endpoint, timeout, bốn trợ lý khác hoặc model combos không được chọn.

Đọc AGENTS/memory/diff và skill ModelOps trước thao tác. Đã xác minh ENV development, DB loopback, provider Qwen active/listed có chat capability. API GET defaults/assistant200; kiểm roundtrip contract không làm đổi các phần cấu hình khác. Ghi intent trước PUT/PATCH, không tự gửi lại mutation chưa rõ trạng thái.

## Kiểm chứng thực chạy

| Kiểm tra | Kết quả |
|---|---|
| HTTP PUT ModelOps defaults | 200 |
| HTTP PATCH admissions config | 200 |
| HTTP GET đọc lại cả hai | 200, đúng Qwen/single/no Luna fallback |
| Compiler route resolver từ DB | Qwen, không fallback model |
| Runtime route planner | Chỉ `prov_rtx5090_vllm` / `qwen3.5-9b` |
| Một inference generic qua HTTP ModelOps | 200, observed qwen3.5-9b, finish_reason stop, content không rỗng, is_fallback false |
| Usage | Một success Qwen,20 input/2 output tokens, không gọi Luna trong probe |
| DB seals | Chỉ system_model_defaults và assistant admissions đổi; knowledge/bốn assistants/provider khác giữ |
| App source hashes | Không đổi so đầu605 |
| Full Pytest/FE/build/benchmark/compiler thật | NOT RUN; không sửa mã hoặc yêu cầu chạy lại |

Helper thực chạy từ root: `.antigravity-bridge/validation/context605_switch_qwen.py`, exit0. Receipt đã lọc trường an toàn ở `backend/storage/context605/`; không ghi credential hoặc private prompt vào báo cáo. Sử dụng HTTP API đang chạy, không sửa DB trực tiếp để đổi model, không restart dịch vụ.

## Giới hạn và tiếp tục

Connectivity probe chỉ xác nhận tuyến Qwen hoạt động, không chứng minh chất lượng compiler/RAG hoặc thay điểm benchmark. Blockers604 vẫn giữ; chưa gọi lại compiler, benchmark64, reindex, duyệt hay publish.

Token Saver được ghi nhận là yếu tố chưa kiểm soát trong các thử nghiệm Luna trước. Chưa có đối chứng input/output thực tế khi bật/tắt để kết luận nguyên nhân sai; không xóa kết quả cũ hoặc quy toàn bộ lỗi cho model/Token Saver. Các run tiếp theo phải ghi model/provider và cấu hình thực tế, tách khỏi kết quả Luna lịch sử.

Không sửa source ứng dụng, không commit/stage/push/reindex/publish/restart/deploy. Không tạo DB test hoặc gửi corpus cho inference kiểm tra.
