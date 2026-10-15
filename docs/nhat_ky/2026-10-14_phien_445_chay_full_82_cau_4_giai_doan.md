# Phiên 445 — Chạy full 82 câu chatbot tuyển sinh theo 4 giai đoạn

Ngày: 14/10/2026, Asia/Bangkok. Theo yêu cầu người dùng: ưu tiên 20 câu giai đoạn 1, rồi 20/20/22.

## Phạm vi và giới hạn

- Fixture: `backend/storage/admissions_eval412_run2.json` (82 cases, ID 1–82, câu hỏi gốc; đáp án kỳ vọng không gửi cho assistant).
- Runner có sẵn `backend/scripts/evaluate_evidence_417.py` (route `chat`, fingerprint guard code/config/publication, lưu từng câu, `--resume` khi ngắt).
- GĐ1 (20): 1,3,5,6,9,11,13,16,19,22,25,38,48,51,62,66,75,80,81,82 — đúng bộ 20 đã đối soát ở 443/444.
- GĐ2 (20): 2,4,7,8,10,12,14,15,17,18,20,21,23,24,26,27,28,29,30,31.
- GĐ3 (20): 32,33,34,35,36,37,39,40,41,42,43,44,45,46,47,49,50,52,53,54.
- GĐ4 (22): 55,56,57,58,59,60,61,63,64,65,67,68,69,70,71,72,73,74,76,77,78,79.
- Không đổi model/provider/reranker/token/quota/config/kho; không reset/reindex/publish/DAG/backup/FE. Không commit/push.
- Một vá runtime nhỏ phát sinh trong phiên (xem dưới) + 1 regression; còn lại chỉ chạy và đọc.

## Kết quả tổng (82/82 HTTP 200, 0 lỗi hạ tầng)

| Giai đoạn | File | answered | insufficient | Ghi chú decision |
|---|---|---|---|---|
| 1 (20) | `admissions_eval445_phase1_20.json` | 18 | 2 (11, 62) | 18 supported, 2 partial |
| 2 (20) | `admissions_eval445_phase2_20.json` | 17 | 3 (15, 21, 27) | 17 supported, 3 partial |
| 3 (20) | `admissions_eval445_phase3_20.json` | 17 | 3 (32, 37, 54) | 17 supported, 2 partial (37, 54), 1 conflict (32) |
| 4 (22) | `admissions_eval445_phase4_22.json` | 20 | 2 (56, 74) | 20 supported, 1 partial (56), 1 missing (74) |

- **Tổng: 72 supported, 8 partial, 1 conflict, 1 missing.** Toàn bộ `code_unchanged/config_unchanged/publication_unchanged=true`, fingerprint kho `733f3faf2f247c16e3a2`.
- Latency trung bình 20,78s, cao nhất 34,03s. Vài lượt fallback Gemma lẻ (failover bình thường), không timeout nào.
- Đối soát trích dẫn đọc DB: **225 spans + 3 reviewed-facts, 100% khớp** identity/span/hash/giá trị hàng; decision integrity 0 lỗi. (2 cảnh báo span ở GĐ2 + 1 ở GĐ3 là hàng fact không span theo chuẩn — đã kiểm identity đầy đủ, đều khớp.)

## Đối soát điểm nóng

- **Q13 lượt này supported đúng phạm vi** ("Một số ngành đào tạo giáo viên phù hợp có thể sử dụng PT4…", trích đoạn chính sách nhóm 3207:3326, giữ "một số"). Xác nhận guard phiên 444 chặn được suy rộng hàng-đơn; dao động giữa các lượt vẫn còn (ghi nhận ở 444).
- **Q75 lượt này supported kèm liên hệ chung** (câu 151 + hotline/cổng chung 676:886 ghi rõ "để theo dõi thông tin", không khẳng định cổng chung là đường dẫn bổ sung). Không bịa URL. Locator-gap vẫn chặn các đáp án deictic thuần (đã chứng minh ở probe 444).
- **Q62**: lượt GĐ1 partial đúng (có công thức, thiếu legend) → phát hiện rule legend-gap của 444 quá chặt (chặn cả khi chỉ thiếu dòng dẫn "Trong đó:"). Đã vá: bỏ qua thành viên chỉ là dòng dẫn kết bằng ":". Regression mới + focus 107 pass + Ruff sạch. Probe lại 2 lượt: lần legend đủ → supported; lần legend vắng → partial đúng (cả audit model và gap cùng kết luận). Hệ thống giờ trung thực cả hai hướng.
- **Q37**: row-gap 444 hoạt động trên câu chưa từng thấy ("chỉ mới có bằng chứng cho Sư phạm Lịch sử; chưa đủ căn cứ cho phạm vi Sư phạm") — hàng fact khớp identity.
- **Q32 conflict**: fail-closed đúng chính sách (nguồn mâu thuẫn về IELTS thay điểm, không suy đoán).
- **Q74 missing**: enumeration phương thức bổ sung không đủ claims (đã corrective 1 lượt) — thiếu trung thực, không bịa.
- Partial còn lại đều có bằng chứng trích đúng và missing cụ thể: Q11 (thiếu liệt kê ngành, mới có chính sách nhóm), Q15 (hàng fact thiếu mã PT5), Q21 (đòi định nghĩa lại PT2 dù claims đã nêu — audit chặt, ứng viên vòng sau), Q27 (đòi nhắc lại câu nguồn + năm dù claims đã có — tương tự), Q54 (thiếu mốc giờ 17:00 ngày 14/07), Q56 (thiếu proof năm cho mức phí 300.000đ).

## Kiểm thử

- Focus evidence: **107 pass** (444 + 1 ca intro-dòng-dẫn mới), Ruff `app/modules/rag/` + test sạch.
- Full suite cuối: **1276 pass / 11 fail / 15 skip / 0 errors** (`--basetemp` do ACL thư mục pytest cũ). 11 fail trùng hệt baseline 441/443/444, không fail mới.
- Không tuyên bố accuracy: supported/partial là trạng thái kiểm chứng, chưa phải đánh giá đúng/đủ toàn diện hay TM-08.

## Bài học

- Rule "legend phải trích" cần trừ dòng dẫn thuần (kết bằng ":") nếu không sẽ tạo false-partial mới — cùng họ lỗi đã sửa ở 6/9.
- Đáp án where-question kèm liên hệ chung đúng scope là chấp nhận được; điều cấm là khẳng định cổng chung thay đường dẫn riêng và bịa URL — lượt này không vi phạm.
- Audit-strictness kiểu "đòi nhắc lại" (Q21/Q27) là ứng viên vòng sau, cần phân biệt diễn đạt lại vs thiếu thật.
