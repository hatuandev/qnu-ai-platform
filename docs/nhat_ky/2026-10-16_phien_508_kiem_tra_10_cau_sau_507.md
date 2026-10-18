# Phiên 508 — Kiểm tra 10 câu sau bản sửa 507 (chỉ đo, không sửa)

Ngày: 2026-10-16. Không đè báo cáo 493–497, 505–507.

## 1. Pre-check và phiên bản

- Backend đã nạp 507 (worker reload 22:23:47 sau edit cuối 22:23:03 + kiểm chứng hành
  vi Q30/mẫu mới). Không restart. Config 20/20/30/5, fallback null, snapshot
  b7456674 trước/sau trùng; 0 cache hit, 0 egress cloud.
- 8 câu nguyên văn fixture (IDs 2,34,40,55,62,11,48,80) qua runner 453 chat API;
  2 câu wording người dùng (Q7≈38, Q10≈82, KHÁC NGUYÊN VĂN) qua script cùng flow
  (fresh conversation, checkpoint JSON+JSONL, usage lookup). 1 lượt, tuần tự, 0 retry,
  0 lỗi kết nối.

## 2. Kết quả

PASS 5 (địa chỉ, NV6, lệ phí NV, học phí, + công thức nội dung), PARTIAL 2 (Q40 thiếu
lõi PT5; Q10 thiếu mức tiền/điều kiện), FAIL 2 (Q11 VISIBLE oan; Q7 numeric gate oan
dù nguồn có nguyên văn), ERROR 1 (Q48 contract echo). NOT RUN 0.
Answered p50 24,88s. Cải thiện so 506 ở 5 IDs tương thích (2,34,55,62 + 40 giữ PARTIAL).
UI NOT RUN (không kênh xem trực quan; layout công thức Q62 chưa nghiệm thu).

## 3. Nhóm tiếp theo (bằng chứng trong REPORT, không sửa)

1. Từ chối dù nguồn đủ (VISIBLE/numeric) — response_audit/verification/citation_guard.
2. Thiếu lõi PT5/mức tiền-điều kiện — evidence_claims coverage.
3. Contract-echo model nhỏ — evidence_model/quyết định cấu hình.

Artifact: `backend/storage/eval507_10q/` (JSON+JSONL+CSV+REPORT). Không secret/prompt/
context. Không code/config/test/build/commit/push. Không suy toàn chatbot từ 10 câu.
