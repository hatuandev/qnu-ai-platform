# Phiên 951 — Đo lại cohort F13 và đóng hạng mục F13-940 (5 câu abstain sai)

Ngày: 2026-11-12. Nhánh: `feat/v1-user-workflow`. Không sửa mã ứng dụng; phiên này chỉ đo lại đúng 5 câu thuộc lớp F13 của bộ 940 trên mã hiện hành, một lần mỗi câu, không retry.

## 1. Yêu cầu và giả định

- Người dùng duyệt "chạy bước 1" của đề xuất phiên 950: đo lại cohort F13 (Q05/Q07/Q09/Q19/Q20) trên corpus 940, mỗi câu một lần, không retry, lưu trace; kết quả dùng để quyết định đóng hay mở F13, không phải chạy đến khi xanh.
- F13 là **lớp lỗi** "model từ chối dù bằng chứng đã nằm trong ngữ cảnh" ghi nhận ở phiên 940 (5/30 câu), kế thừa tên từ câu F13 của bộ tuyển sinh cũ (phiên 908). F13 gốc phiên 908 nằm trên corpus đã bị reset ở 940 nên **không thể đo lại** nếu không upload lại hai PDF cũ — nằm ngoài phạm vi lượt này.
- Nhãn 30 câu vẫn `draft_needs_human_check`, chưa có người duyệt; kết quả là kiểm chứng kỹ thuật một lượt, không phải benchmark và không so sánh trực tiếp với các cohort 10 câu trước đó.

## 2. Trạng thái mã và môi trường

- Dev stack khởi động lại lúc 21:32 phiên 950 (`run_v1.py dev`, API 8002 + worker ARQ + FE V2 3002), đã nạp bản dedupe `parse_answer` của phiên 950.
- Workspace `ws_39c202a81045`; collection `col_0daa6e0ed137`; index `idx_bfd36fae5a30` generation 1, 465 chunk (không re-index); corpus phiên 940.
- Trace từng câu xác nhận: prompt `qnu.rag.answer/v28`, grounding `qnu.answer-cells/v7`, projection `qnu.answer-projection/v7`, coverage `qnu.rag.coverage/v2`, selection v2, table-selection v2, payload v3; model chat `qwen3.8-27b-q4`; rerank `bge-reranker-v2-m3` áp dụng cho cả 5 câu.
- `verification.mode="off"` trong trace (chấm số do harness ngoài đối chiếu evidence đã lưu), nên kết luận nội dung dưới đây dựa trên đọc đáp án + đối chiếu nguồn đã dẫn, không dựa vào cờ verification.

## 3. Cách đo

- Script tạm `%TEMP%/qnu_f13_951_cohort.py` (ngoài Git): đăng nhập bằng token cache/`DEV_ACCESS_PASSWORD` từ `.env` gốc (không in ra), gọi `POST /workspaces/{ws}/collections/{col}/answers` cho từng câu đúng **một lần**, timeout 300 s, lưu phản hồi thô `qnu_f13_951_<QID>.json` và bảng tổng hợp `qnu_f13_951_summary.json`.
- Không gửi lại câu nào; không đổi tham số retrieval (mặc định collection, `hybrid_rerank`); không ghi DB ngoài bản ghi phục vụ bình thường của API.

## 4. Kết quả một lượt (21:41–21:42)

| Câu | HTTP / status | Thời gian | Token | Dẫn chứng | Chấm token 940 | Nội dung (đọc + đối chiếu nguồn) |
|---|---|---|---|---|---|---|
| Q05 | 200 `answered` | 4,94 s | 4.416 | E1, E2 | PASS | Đúng 93,3% cho An toàn thông tin 2026, đúng ô đã xác lập ở 945 |
| Q07 | 200 `answered` | 6,33 s | 3.002 | E1, E3 | PASS | Đúng 1233 chỉ tiêu / 1149 ghi nhận, TỔNG CỘNG 12 chương trình 2026 |
| Q09 | 200 `answered` | 6,88 s | 4.074 | E5, E9, E10 | PASS | Đủ 6 chương trình nhóm A, không lẫn nhóm B |
| Q19 | 200 `answered` | 12,26 s | 4.961 | E1–E4, E7–E14 | PASS | Khớp cả hai quy tắc nguồn: 0 hợp lệ phải có bằng chứng không phát sinh; ô trống giữ nguyên; "Chưa công bố" chỉ ghi nhận, không suy đoán trị số |
| Q20 | 200 `answered` | 7,51 s | 5.693 | E1 | **FAIL token** (thiếu literal "Đào tạo") | Đúng nghĩa: P.ĐT chủ trì, hạn 30/11/2026, nghiệm thu đủ 12 mã và giữ số 0 đầu; đáp án dùng đúng chữ "P.ĐT" trong ô nguồn trang 9, cụm "Phòng Đào tạo" chỉ xuất hiện ở bảng trang 14 không liên quan nên ngữ cảnh được cấp không có bản mở rộng |

- Tổng 5 lượt: **5/5 HTTP 200 `answered`**, **0 abstain**, **0 lỗi 502**, 0 retry; tổng 22.146 token, tổng thời gian gửi 37,92 s.
- Coverage trong trace: Q05/Q19/Q20 `complete`; Q07/Q09 `partial` do `scope_status="unresolved"` (không phải thiếu đơn vị — mọi requirement/structure liên quan đều `covered`).

## 5. Kết luận và đóng hạng mục F13-940

- **Trạng thái hạng mục:** F13-940 **ĐÓNG** ngày 2026-11-12 theo kết quả đo phiên 951 (một lượt, 5/5 `answered`, 0 abstain, không retry); F13-908 **vẫn mở** (corpus đã bị reset ở 940, chưa đo lại) — hai hạng mục tách riêng, không gộp kết luận.
- Lớp F13 (abstain sai dù đủ bằng chứng) **không tái diễn** trong một lượt đo trên mã cuối: cả 5 câu đều trả lời, đúng nội dung theo đối chiếu nguồn.
- Q05/Q07 đã được xử lý ở 945/943 và tái xác nhận ở 946; Q09 thực chất là lỗi hợp đồng dẫn chứng (502 do lặp alias), đã sửa ở 950 và tái xác nhận ở lượt này; Q19 trước đó đạt ở 943 và nay tái xác nhận trên v7; Q20 không còn abstain, chỉ còn khác biệt token do viết tắt — thuộc nhóm G3 "thiếu ý/nhãn", không phải F13.
- **Không tuyên bố F13 gốc phiên 908 đã sửa** (corpus đã reset, chưa đo lại). Không tuyên bố chất lượng toàn bộ 30 câu hay độ bền nhiều lượt; kết quả chỉ là một lượt, nhãn draft.

## 6. Kiểm chứng và giới hạn

- Bằng chứng: 5 phản hồi thô + summary trong `%TEMP%`, mốc 21:41:39–21:42:12; trace từng câu xác nhận đúng phiên bản prompt/grounding/projection.
- **Không sửa mã**, không re-index, không đổi cấu hình/retrieval, không reset DB, không commit/push.
- Full Pytest: **NOT RUN** (hai tiến trình full-suite cũ PID 18888/22164 vẫn treo, không can thiệp; baseline lịch sử FAIL 4/1627 phiên 928 giữ riêng). `NOT RUN ≠ PASS`; token PASS không đồng nghĩa nội dung đúng — cột nội dung ở trên là đọc thủ công + đối chiếu nguồn đã dẫn.
- Giới hạn: một lượt/câu, một corpus; Q20 có thể đạt token nếu đáp án mở rộng "P.ĐT (Phòng Đào tạo)" nhưng ngữ cảnh được cấp không chứa bản mở rộng; nhãn 30 câu chưa người duyệt.

## 7. Artifact (ngoài Git, trong %TEMP%)

`qnu_f13_951_cohort.py`, `qnu_f13_951_Q05.json`, `qnu_f13_951_Q07.json`, `qnu_f13_951_Q09.json`, `qnu_f13_951_Q19.json`, `qnu_f13_951_Q20.json`, `qnu_f13_951_summary.json`.
