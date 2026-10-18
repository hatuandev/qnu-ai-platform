# Phiên 498 — Benchmark 82 câu, profile configured 20/20/30/5 (chỉ đo, không sửa)

Ngày: 2026-10-16. Theo yêu cầu: chạy lại 82 câu sau khi admissions cấu hình Top K
20/20/30/5; chỉ kiểm tra-ghi nhận, KHÔNG sửa code. Không đè báo cáo 493–497.

## 1. Chuẩn bị (ghi nhận, không đổi để làm đẹp)

- Đã đọc AGENTS.md, skill evaluation (+ benchmark-contract), fixture 82
  (`admissions_eval412_run2.json`, giữ expected_answer, không gửi khi chạy).
- Runtime xác minh đọc-only: assistant `admissions`, `col_admissions` (22 nguồn),
  retrieval configured 20/20/30/5 đúng yêu cầu; preferred vLLM nội bộ; embedding bge-m3
  + reranker bge-reranker-v2-m3 cùng box nội bộ (xác minh provider_id).
- Vấn đề chặn: fallback là Cloudflare ngoài, key ACTIVE — hiccup là corpus ra cloud.
  Người dùng cho phép TẮT fallback riêng `admissions` (scoped, có before/after
  e3657561→515497a7, preferred giữ nguyên, KHÔNG bật lại). API xác nhận hiệu lực ngay.
  Kết quả: 0 fallback, 0 byte ra cloud cả lượt.
- Backend sống 8001, mã 494/495 (user restart trước đó). Probe vLLM OK.
- Runner `evaluate_admissions_453.py` (sequential = concurrency 1 vì hạ tầng từng lỗi
  liên tục; không retry runner; câu 1 tính luôn không warm-up; hội thoại riêng từng câu
  vì fixture không thiết kế follow-up): sửa harness tối thiểu — bỏ `tenant_id` (3 chỗ),
  dừng khi 3 lỗi kết nối liên tiếp (không kích hoạt), JSONL sidecar mỗi kết quả,
  gắn cờ `cache_hit` từ diagnostics (0 hit cả lượt → toàn bộ là đo mới).

## 2. Chạy 82 câu, checkpoints 20–20–20–22 (IDs 1–20/21–40/41–60/61–82)

| Chặng | answered | insufficient | ERROR 502 | NOT RUN |
|---|---|---|---|---|
| GĐ1 | 8 | 5 | 7 | 0 |
| GĐ2 | 9 | 8 | 3 | 0 |
| GĐ3 | 9 | 3 | 8 | 0 |
| GĐ4 | 9 | 7 | 6 | 0 |
| **Tổng** | **35** | **23** | **24** | **0** |

ERROR toàn là model (17 MODEL_CONTEXT_EXCEEDED + 7 contract echo), 0 hạ tầng
(khác hẳn lượt 496: 16 lỗi router/upstream). Guard fingerprints code/config/
publication unchanged cả 4 chặng. Không timeout, không connection loss.

## 3. Chấm thủ công theo nguồn (không LLM judge) + đối soát máy

- Nhãn: PASS 27, PARTIAL 7 (thiếu ý/phụ thêm: 8, 10, 29, 40, 50, 72, 76),
  FAIL 24 (23 từ chối + Q23 sai năm 2024), ERROR 24. Tổng khớp 82.
- Máy: numeric gaps 0/35 answered; citations 79/79 tới được revision đã xuất bản
  (72 có hash+span, 7 đường chat thiếu hash/span — khoảng trống provenance đã biết);
  latency HTTP200 p50 17,23s / p95 27,58s / max 32,86s.
- Hai góc nhìn: chất lượng trên 58 câu chấm được — PASS 46,6% / PARTIAL 12,1% /
  FAIL 41,4% (mẫu số ghi rõ; gold chưa re-verify hết độ tươi nên không phải accuracy);
  vận hành trên 82 — answered 42,7% / insufficient 28,0% / error 29,3%.
- Phát hiện cấu trúc lớn nhất: context configured 36000 ký tự vs cửa sổ qwen 8k —
  17 overflow kể cả câu đơn giản (cả section VIII gục), lỗi 495 đặt tên đúng thay vì
  giả dạng outage như trước. Phát hiện lẻ: Q23 "2024" cho hỏi 2026; 4 template 0-call;
  VISIBLE loại 12 bản nháp (oan/đúng chưa phân biệt — 493§4.3 còn nguyên).
- So sánh: 496 legacy 46 answered/20 insuf/16 hạ tầng (khác profile+mã+thời điểm —
  chỉ đối chiếu định tính); 445 (mã tiền-492) không so số học.

## 4. Bàn giao và việc tiếp theo (đề xuất, không triển khai)

- Gói kết quả: `backend/storage/eval498_configured_20-20-30-5/` (4 JSON + 4 JSONL
  82 IDs duy nhất + CSV BOM + labels + REPORT). 5 nhóm lỗi ưu tiên trong REPORT §5;
  batch tiếp theo đề xuất B1–B5 trong REPORT §7.
- Fallback Cloudflare của admissions ĐANG TẮT (theo ủy quyền, không tự bật lại) —
  người dùng quyết định khi nào khôi phục.
- Không sửa code/test/config (trừ harness đo + thao tác fallback được ủy quyền),
  không full pytest/build/benchmark khác, không commit/push. Báo cáo 493–497 giữ nguyên.
