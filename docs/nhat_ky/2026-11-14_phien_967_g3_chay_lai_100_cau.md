# Phiên 967 — 2026-11-14 — G3 chạy lại 100 câu trên mã P1.1 và chẩn đoán theo công đoạn

> Số liệu và diễn giải đã được đối chiếu lại với kết quả baseline, G3 và các lượt chẩn đoán.

## Yêu cầu và phạm vi

- Người dùng duyệt G3: **"vậy chạy lại 100 câu đi, nếu phát triển lỗi nữa thì phân tích tìm hiểu nguyên nhân ở quy trình chỗ nào"** — chạy lại đủ bộ 100 câu tuyển sinh trên mã P0+P1+P1.1 (chưa commit), so với mốc baseline (84 đúng / 2 tạm đạt / 2 sai / 8 thiếu căn cứ / 4 lỗi 502 cứng; 6 câu 502-thoáng-qua-retry vẫn tính trong 84), và với mọi ca lệch phải chỉ rõ **công đoạn nào của pipeline** gây ra.
- Định nghĩa cổng G3 (mục 9 kế hoạch): 84 câu đúng cũ phải giữ nguyên đúng, cho phép tối đa **1 ca lệch có giải trình**.
- Không sửa mã, không reindex/migration, không commit/push; chỉ đọc DB và chạy API thật.

## Môi trường

- API :8002 chạy từ mã P1.1 (uvicorn `qnu.main:app --app-dir backendV1`, PID 10436, `/health` 200); worker V1/FE V2 không đụng.
- Trợ lý `ast_47f30aaf2665` rev 3, kho `col_9209e90d1a53`, index run `idx_0a4fbb712a1e` (182 chunk: 161 paragraph + 21 table), `top_k=5`, `candidate_k=40`, `hybrid_rerank`, scope explicit, `context_max_bytes=32000`, `verification_mode=off`; model `qwen3.8-27b-q4`; prompt `qnu.rag.answer/v29`.
- DB dev head 0028; chỉ truy vấn đọc (`chat_turns`, `workspace_events`, `kb_index_chunks`).

## Cách chạy

- Runner `%TEMP%/qnu_g3_100.py` (ngoài Git): 100 câu từ `Cau_hoi_tuyen_sinh_QNU_2026 (1).md`, **1 lượt/câu**, mỗi câu một hội thoại mới, `Idempotency-Key` tiền tố `g3-100-{n}-`, token đọc từ `%TEMP%/qnu_e2e_token.txt` (không in). Kết quả `%TEMP%/qnu_g3_100_results.json` + log tiến độ `%TEMP%/qnu_g3_100.log`; **không ghi đè** baseline `%TEMP%/qnu_questions_100_results.json`.
- So sánh: `%TEMP%/qnu_g3_compare.py` (trạng thái + token số); chẩn đoán: `%TEMP%/qnu_g3_rediagnose.py` → `%TEMP%/qnu_g3_diag_results.json` (câu lỗi × 4 lượt chạy lại, **chỉ để chẩn đoán nội dung, không dùng để "làm xanh" cổng**).

## Kết quả tổng (100 lượt single-shot)

- **answered 89/100**; insufficient 2 (Q53 và Q99 đều giữ trạng thái như baseline); lỗi 9: Q2 409; Q26, Q28, Q33, Q40, Q41, Q44, Q45, Q73 502.
- Mã lỗi từ `chat_turns.error_code`: `answer_table_value_not_extractive` ×3 (Q26, Q41, Q73); `answer_cell_invalid` ×2 (Q28, Q40); `answer_coverage_invalid` ×3 (Q33, Q44, Q45); `conversation_clarification_required` ×1 (Q2). 0 `answer_evidence_changed`, 0 lỗi provider.
- **Cổng G3: FAIL** — 7 câu thuộc nhóm 84 đúng cũ lệch đã xác định (Q2, Q26, Q33, Q40, Q44, Q45, Q73) > 1 ca cho phép. Q45 thuộc nhóm 84 sau khi thử lại ở baseline.
- Độ trễ mean/median/max: baseline 12,7/10,9/29,6 s → G3 10,4/10,2/18,8 s. Token prompt +3–4% so envelope baseline (dải hạng P0 `rank_band: 5`).

## Chẩn đoán theo công đoạn

| Công đoạn | Có phải nguyên nhân? | Bằng chứng |
|---|---|---|
| Upload/OCR/bóc tách/chunk/index | **Không** | Dữ kiện quyết định có nguyên văn trong `kb_index_chunks`; câu guard lỗi nhận envelope đầy đủ (225 ô – Q26, 271 ô – Q33, đơn vị plan đủ); 6 câu từng đúng ở baseline chạy lại cho đáp án khớp baseline; Q28/Q41 lặp lại lỗi baseline |
| Truy xuất/fusion/rerank | **Không** | Cùng envelope sinh ra đáp án đúng khi chạy lại; không câu lỗi nào thiếu chunk quyết định |
| Packing/context | **Không phát hiện lỗi mới** | P1.1 page-band không xuất hiện trong envelope lỗi nào; P0 band (+5 chunk văn bản) có mặt cả lượt đúng lẫn lượt lỗi |
| Định tuyến hội thoại | **Có, 1 ca (Q2)** | Route v4 tự đánh dấu câu "Thông báo tuyển sinh này…" là cần làm rõ → 409 trước truy xuất; 4/5 lượt chạy lại định tuyến đúng, trả lời đúng (Chính quy). `rewriting.py` không thuộc phạm vi P0/P1/P1.1 |
| Sinh câu trả lời + materialize/guard | **Có, 8 ca guard (6 thuộc nhóm 84 đúng cũ)** | Q26/Q41/Q73 `table_value`; Q28/Q40 `cell_invalid`; Q33/Q44/Q45 `coverage` — guard trung thực chặn output không trích được/bind sai ô/mã dẫn chứng trùng hoặc ngoài danh sách trong assessment; 4 lượt chẩn đoán bổ sung: HTTP 200 ở Q26 2/4, Q33 3/4, Q40 3/4, Q44 2/4, Q45 2/4, Q73 2/4. Một lượt Q40 trả về chỉ tiêu thay vì yêu cầu về môn Địa |
| Coverage/appeal | **Không** | Appeal P1.1 không gây lỗi nào trong 100 lượt; Q53 giữ abstain như baseline |

- **Lỗi guard có sẵn từ baseline, ngẫu nhiên theo lượt:** hai tệp baseline ghi **10/100** lượt đầu và **4/10** lượt thử lại bị guard 502 (**14/110** gộp) trên Q16, Q21, Q25, Q31, Q38, Q41, Q45, Q47, Q49, Q97 lần đầu — chính vì vậy baseline phải retry nhóm transient. G3 single-shot có 8/100 guard. Nhóm lỗi đã có ở baseline. So tỷ lệ lượt đầu theo cùng cách đếm là 10/100 và 8/100; đây là số quan sát, chưa cô lập tác động của P0.
- **Dấu vết P1.1 ở nhóm lỗi:** Q74 — câu duy nhất hưởng link trang — nay trả lời được (2/3 nội dung ở phiên 966; G3 tiếp tục trả lời). Không envelope lỗi nào chứa `native_page_band_continuation/v1`.
- **P0 chưa thể tách tuyệt đối:** dải hạng 6–10 làm prompt +3–4%; không có A/B (chưa duyệt) nên không loại trừ được gia tăng nhỏ xác suất guard, nhưng không có bằng chứng hồi quy tất định (cùng lớp envelope vừa đúng vừa lỗi).

## Cải thiện so với baseline (chấm tay nhóm 16 câu lỗi cũ)

- **PASS trọn mới:** Q12, Q19, Q21 (Kinh tế số 7310109, 45), Q38 (danh sách tổ hợp), Q85, Q88.
- **Q5:** đủ 3 website chính thức (trước chỉ 1) — từ tạm đạt lên đạt.
- **Partial:** Q16 (lẫn 402/402A), Q29 (thiếu chỉ tiêu CNTT), Q74, Q78, Q6 (chỉ nêu mục, thiếu nội dung).
- **Q24:** trả lời nhưng sai nội dung (học phí thay vì mục/chỉ tiêu) — trước đó abstain.
- **Q53:** insufficient như baseline. **Q28/Q41:** vẫn lỗi (baseline: sai nội dung / 502 cứng) — không phải hồi quy câu đúng.
- **Q99:** baseline và G3 đều ghi insufficient, cùng thông điệp chưa thể khẳng định trúng tuyển.

## Giới hạn / NOT RUN

- Chấm lại **nội dung đầy đủ 77 câu** còn trả lời được của nhóm 84 cũ: **NOT RUN** (mới so trạng thái, đối chiếu token số và spot-check các câu từng lỗi). Vì vậy không có tuyên bố "84 câu nội dung vẫn đúng" — chỉ có "77 câu vẫn trả lời, spot-check không thấy sai mới".
- A/B tách ảnh hưởng dải hạng P0: **NOT RUN** (chưa duyệt). pytest: **NOT RUN**. Không commit/push.

## Kết luận và hướng tiếp (chưa duyệt)

- G3 **FAIL**. Trace ghi 8 lỗi kiểm tra đầu ra và 1 lỗi định tuyến. Sáu ca bảng đã đối chiếu có cùng danh sách nguồn và danh mục ô giữa lượt đúng và lượt lỗi. Kết luận này áp dụng cho các ca có trace tương ứng.
- Hướng tiếp cần người dùng quyết: (a) P2 chọn model qua ModelOps; (b) siết cấu trúc coverage/guard cho câu bảng (giảm phụ thuộc may rủi của model); (c) đo lặp để tách phương sai trước khi chốt lại tiêu chí cổng theo lượt thay vì single-shot.

## File đo (ngoài Git)

- `%TEMP%/qnu_g3_100.py`, `%TEMP%/qnu_g3_100_results.json`, `%TEMP%/qnu_g3_100.log`, `%TEMP%/qnu_g3_compare.py`, `%TEMP%/qnu_g3_rediagnose.py`, `%TEMP%/qnu_g3_diag_results.json`; baseline `%TEMP%/qnu_questions_100_results.json` (không đổi).
