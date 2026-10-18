# Phiên 506 — Kiểm tra 12 câu trọng tâm sau bản sửa 505 (chỉ đo, không sửa)

Ngày: 2026-10-16. Không đè báo cáo 493–497 maupun 505.

## 1. Pre-check

- Backend port 8001: process cha từ 19:07 nhưng worker con reload 20:36, sau edit 505
  cuối (20:34); kiểm chứng hành vi (Q30 ngoài tập đo nay answered, mẫu từ chối mới
  không hotline live ở Q62) → đang phục vụ mã 505. Không restart (không cần).
- Assistant `admissions` / `col_admissions`; retrieval configured 20/20/30/5;
  preferred vLLM + embed/rerank nội bộ; fallback cloud null (vẫn off từ 498).
  served_models 12 lượt toàn `fb=False` → 0 egress.
- Config 515497a7 + snapshot b7456674 trước/sau trùng; guard runner 3 unchanged true;
  cache hit 0/12. Runner 453 (chat API WebUI, đã gọn tenant ở 498): tuần tự, hội
  thoại mới mỗi câu, 1 lượt, checkpoint từng câu, 0 retry.

## 2. Kết quả 12 câu

PASS 7 (3, 5, 9, 18, 25, 31, 43), PARTIAL 2 (40 thiếu lõi PT5; 55 thêm tin bổ sung),
FAIL 2 (Q2 địa chỉ nguyên văn bị verifier bác; Q34 quy tắc NV1–5 nguyên văn bị từ
chối), CORRECT_ABSTENTION 1 (Q62: không passage công thức chung, từ chối tính đúng,
mẫu mới sạch). ERROR 0, NOT RUN 0. Latency answered p50 12,61s / max 34,23s.
Cải thiện so lượt 82: 8 câu; không đổi 3; Q62 chuyển sang từ chối đúng. Khớp probe505.

## 3. Nhóm lỗi tiếp theo (bằng chứng trong REPORT, không sửa ở đây)

1. Verifier/VISIBLE bác nguồn nguyên văn (Q2, Q34) — `evidence_verification.py`,
   `response_audit.py` (câu 505 chưa đủ).
2. Rớt facet PT5/tổ hợp ở đáp án liệt kê (Q40) — `evidence_claims.py` (so với Q15 đúng).
3. Theo dõi template/UNVERIFIED sớm — `citation_guard.py` mẫu mới đã sạch.

Artifact: `backend/storage/review506_12q/` (JSON+JSONL+CSV+REPORT). Không secret/
prompt/context trong log. Không code/config/test/build/commit/push. Không tuyên bố
RAG ổn định từ 12 câu.
