# Phiên 496 — Chạy lại full 82 câu chatbot tuyển sinh theo 4 giai đoạn

Ngày: 2026-10-16. Theo yêu cầu người dùng: test lại 82 câu, ~20 câu mỗi giai đoạn,
trên mã hiện tại (sau batch 494/495). Không đè báo cáo 493/494/495.

## 1. Thiết lập và sự cố harness

- Fixture: `backend/storage/admissions_eval412_run2.json` (82 cases ID 1–82, đáp án kỳ
  vọng không gửi cho assistant). Runner `backend/scripts/evaluate_evidence_417.py`
  route `chat`, fingerprint guard code/config/publication, lưu từng câu, `--resume`.
- GĐ1 (20): 1,3,5,6,9,11,13,16,19,22,25,38,48,51,62,66,75,80,81,82.
  GĐ2 (20): 2,4,7,8,10,12,14,15,17,18,20,21,23,24,26,27,28,29,30,31.
  GĐ3 (20): 32–37,39–47,49,50,52,53,54. GĐ4 (22): 55–61,63,64,65,67–74,76–79.
- Backend port 8001 đang chạy mã cũ từ 09:40 (mã 494/495 sửa 12:32–13:35) — đã hỏi và
  người dùng restart (process mới 13:52, đúng mã mới) rồi mới chạy. Probe tối thiểu
  (không corpus): vLLM qwen3.5-9b OK, không fallback; `/tokenize` vẫn 404.
- Runner 417 gãy trên mã hiện tại: `assistant["tenant_id"]` KeyError (API single-application
  không còn tenant). Đã sửa harness tối thiểu 2 dòng sang `assistant.get("tenant_id")`
  (None = scope chung, đúng chữ ký hiện tại) — chỉ sửa runner, không đụng runtime.
- Artifacts: `backend/storage/admissions_eval496_phase{1,2,3,4}_{20,20,20,22}.json`
  (riêng tư, không commit). Mọi lượt giữ nguyên, không retry săn đáp án đẹp.

## 2. Kết quả tổng (82/82 attempts)

| Giai đoạn | HTTP 200 | answered | insufficient | Lỗi hạ tầng |
|---|---|---|---|---|
| GĐ1 (20) | 16 | 6 | 10 | 4 (2×503, 2×502) |
| GĐ2 (20) | 14 | 9 | 5 | 6 (2×503, 4×502) |
| GĐ3 (20) | 17 | 15 | 2 | 3 (2×503, 1×502) |
| GĐ4 (22) | 19 | 16 | 4 | 3 (3×502) |
| **Tổng** | **66** | **46** | **20** | **16 (6×503, 10×502)** |

- Decisions HTTP 200: supported 44 (42 `VERIFIED_PROSE_FALLBACK` + 2
  `VERIFIED_ROW_COORDINATES`), missing `ROW_AUDIT_REJECTED` 1, `NUMERIC_GROUNDING_FAILED`
  2, `VISIBLE_ANSWER_NOT_SUPPORTED` 12, template chung 5.
- Lỗi: 6×503 `ALL_PROVIDERS_UNAVAILABLE` (vLLM 502 giữa lượt + fallback ngoài bị chặn);
  9×502 `EVIDENCE_MODEL_CONTRACT_INVALID` (model echo schema 2 lượt — repair cap/skip
  phiên 495 chỉ cứu ngân sách, không cứu được model không chịu ra data);
  1×502 `Kiểm chứng mệnh đề không đầy đủ` (Q55).
- Guard fingerprints: `code_unchanged/configuration_unchanged/publication_unchanged =
  true` ở cả 4 file. Model phục vụ: vLLM qwen3.5-9b (384 lượt success) + 6 lượt lẻ
  Cloudflare llama fallback. Không đổi model/provider/preset/config/kho.

## 3. Đối soát chất lượng theo nguồn (không lấy HTTP200/answered làm đúng)

- Toàn vẹn trích dẫn: 97/101 citations phân giải đúng binding/index/source khớp snapshot
  và quote phi rỗng. 4 thiếu là đường chat (Q56×3, Q65×1): có binding/index/source đúng
  nhưng `canonical_hash`/`span` null — truy được tới revision nguồn, thiếu粒度 span.
  Ghi nhận là khoảng trống provenance của route chat, không phải bịa căn cứ.
- Rà số học toàn bộ 46 answered: **0 con số đa chữ số nào ngoài trích dẫn** (so Decimal
  chuẩn hóa nghìn/phân cách như gate runtime).
- Điểm nóng đọc tay theo nguồn:
  - Q15 (GDTC): row path trả đủ bảng 19/–/–/19 + tổ hợp + legend "–" — đúng hướng batch A.
  - Q11/Q21/Q27/Q37: trả đúng cấp nhóm (sư phạm/PT2/PT3) có trích TB263; riêng Q11 hỏi
    "ngành nào" mà chỉ nêu nhóm (như chuẩn partial của 445) — answered ở đây ở mức nhóm.
  - Q32: 445 conflict về IELTS, lượt này answered với claim có phạm vi "PT1/PT2" kèm trích
    đúng phạm vi đó — thay đổi cần theo dõi, chưa kết luận hết mâu thuẫn nguồn.
  - Q74: 445 missing, lượt này answered đủ (28 ngành/456 chỉ tiêu/22-08-2026) có trích.
  - Q56 (300.000đ, phân biệt lệ phí thi vs xét tuyển) và Q65 (sàn vs chuẩn) đúng trích.
  - Nghi ngờ false-missing: Q62 (công thức tự tính) về template trong khi nguồn có nguyên
    tắc "không tự chuyển thang" như Q10 — cần đào sâu, chưa xử lý trong phiên.
  - Template chung (Q16/Q18/Q30/Q57/Q62): từ chối đúng hay oan tùy từng câu — chưa chấm
    hết, không gộp thành "không có dữ liệu" (lỗi kỹ thuật đã tách riêng ở mục lỗi).
- 12 `VISIBLE_ANSWER_NOT_SUPPORTED` + 2 `NUMERIC_GROUNDING_FAILED`: guard chặn bản nháp
  (đúng chức năng), nhưng chưa phân biệt được bao nhiêu là oan do audit chặt (cảnh báo
  493§4.3) — cần vòng chấm demanding hơn, ngoài phạm vi chạy này.

## 4. So với phiên 445 (đọc có điều kiện)

445: 82/82 HTTP200, 72 supported/8 partial/1 conflict/1 missing trên mã trước batch
492–495, 0 lỗi hạ tầng. Lượt này: 46 answered/20 insufficient/16 lỗi hạ tầng trên mã mới,
model cùng loại nhưng phiên bản phục vụ/vận hành khác thời điểm. Ba nguồn chênh lệch:
hạ tầng (16), guard chặt hơn có chủ đích (audit độc lập, prose recovery, row audit —
không tồn tại ở 445), và dao động model. **Không suy ra chất lượng giảm hay tăng**;
supported/answered không phải accuracy, insufficient không phải sai.

## 5. Kiểm thử và bàn giao

- Không tuyên bố accuracy/TM-08. Không sửa runtime trong phiên (trừ 2 dòng harness).
  Không nguồn/vector/config/restart (trừ restart do người dùng thực hiện trước giờ chạy)
/reindex/deploy/commit/push. Artifacts giữ trong storage riêng tư.
- Việc tiếp theo: chấm demanding từng insufficient (oan vs đúng), đào Q62/Q32, thêm mẫu
  khi provider ổn định, xử lý các mục 493 ngoài batch (concurrency, ngân sách lượt gọi,
  conversation state, nhãn Faithfulness UI).
