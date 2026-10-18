# Phiên 497 — Vì sao lỗi 502 lặp lại + gọn runner theo single-application

Ngày: 2026-10-16. Theo yêu cầu: (1) bỏ tenant_id/collection_id khỏi runner,
(2) tìm nguyên nhân 502 lặp lại. Không sửa runtime, không benchmark, không đè 493–496.

## 1. Runner gọn theo single-application

- API `/assistants/admissions` hiện không còn `tenant_id` (đã xác minh response);
  `collection_id` vẫn còn và `resolve_retrieval_snapshot` vẫn bắt buộc cần nó nên giữ.
- `backend/scripts/evaluate_evidence_417.py`: bỏ hẳn kwarg `tenant_id` ở 2 chỗ resolve
  snapshot (thay cho `.get()` tạm ở phiên 496). Syntax OK. Route chat vốn chỉ gửi
  message+conversation_id nên không dùng 2 trường này từ trước.

## 2. "Lỗi 502" là ba bệnh khác nhau (bằng chứng từ artifacts 496 + probe trực tiếp)

- **A. Upstream 502 thoáng qua → backend trả 503 (6 câu: 9,13,7,12,42,47).**
  Chuỗi: vLLM :8000 trả HTTP 502 giữa pipeline (sau các calls tốt) → adapter ghi circuit
  failure → fallback CF bị chặn 403 → `ALL_PROVIDERS_UNAVAILABLE`.
- **B. App 502 do model echo schema (9 câu: 66,75,10,20,24,31,39,61,79).**
  `EVIDENCE_MODEL_CONTRACT_INVALID` sau 2 attempts — hành vi model nhỏ, không phải hạ tầng.
  Repair cap/skip phiên 495 chỉ cứu ngân sách, không cứu được model không chịu ra data.
- **C. App 502 verdict lệch claim (1 câu: Q55).** `EVIDENCE_VERIFICATION_INVALID` —
  model trả verdicts thiếu/trùng claim_id. Hành vi model, fail-closed đúng.

## 3. Truy nguyên nhân A: router 502, không phải prompt to hay proxy ngoài

- Thang prompt trực tiếp qua ModelOps (2k/8k/20k chars tổng hợp, không corpus):
  cả 3 OK, latency ~0.5s. **502 không tương quan kích thước**, không tái hiện theo cầu.
- Server trực tiếp (không proxy): header `server: uvicorn` ở mọi endpoint; `/health`
  200 healthy; `/version` vLLM 0.1.14.dev6; `/metrics` mở.
- Metrics của chính server (`:8000`) tổng hợp 3 engine pods `127.0.0.1:8001/8002/8003`
  (bge-m3 / reranker / qwen3.5-9b), kèm `healthy_pods_total` — đây là topology
  **router :8000 trước engine pods**, không phải một engine đơn. 502 là mã của tầng
  router khi engine hiccup, khớp ReadError rải rác cùng đợt.
- Đếm lỗi phía server: qwen **74 errors / 937 requests (~8%)**, tất cả ≤0.05s
  (tổng 0.81s) — từ chối nhanh, không phải timeout/generation chậm; bge-m3 có 6 errors
  tương tự (khớp đợt embedding "All connection attempts failed" ở 492).
  `num_requests_swapped = 0`, hiện idle (0 running) — server đang khỏe.
- Thời điểm lỗi rải 06:57–07:22 UTC (tính từ started_at + elapsed cộng dồn từng file
  496), không dồn một cửa sổ chết — đúng mẫu hiccup từng request trên box 5090 chạy
  chung chat+embed+rerank, không phải sập kéo dài.
- Giới hạn chứng cứ: body của các 502 chưa từng được giữ (log ta chỉ lưu phân loại
  `provider_request_failed`), và log engine/router nằm trên máy AI (không truy cập
  từ đây). Khẳng định "router 502 do engine hiccup" là suy luận mạnh từ metrics +
  topology + mẫu thời gian, chưa phải proof từ log server.

## 4. Đề xuất (chưa code, chờ duyệt)

- **P1 chẩn đoán (nhỏ, an toàn):** log body lỗi 5xx của provider (đã redact secret/URL
  bằng `safe_error_message`, cắt ngắn) trong `model_inference_failed` — 502 sau sẽ kèm
  nguyên nhân (pod/reason của router). Không đổi hành vi.
- **P2 resilience (cần duyệt thiết kế):** một retry giới hạn cho 502/503 retryable trong
  vòng negotiation sẵn có của `post_chat` (đã có mẫu MAX_NEGOTIATIONS cho 400) trước khi
  failover provider; không nhân tầng retry, không tính thêm circuit failure cho retry.
  Bằng chứng ủng hộ: calls ngay sau lỗi vài giây đều thành công.
- **P3 vận hành (phía máy AI):** kiểm tra log router/engine quanh 06:57–07:22 UTC ngày
  16/10 (KV pressure/OOM/restart pod qwen :8003 trên 5090 chạy chung 3 models);
  cân nhắc tách tải embed/rerank khỏi chat nếu hiccup lặp lại ~8%.
- **P4 model (quyết định cấu hình):** echo schema 9/82 là bệnh model nhỏ — repair chỉ
  chữa ngân sách; muốn giảm phải đổi model audit hoặc hợp đồng chặt hơn (vượt phạm vi
  diagnose này).

Artifacts diagnose nằm /tmp (không vào Git). Không nguồn/vector/config/runtime đổi;
không migration/restart/reindex/deploy/commit/push. Mốc giờ lỗi chi tiết:
C:\Users\AnhTuan\AppData\Local\Temp\opencode\errtime.txt (giữ local).
