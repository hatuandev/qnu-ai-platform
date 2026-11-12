# Phiên 937 — P0 ngân sách ngữ cảnh và chạy lại 10 câu RAG phiên 935 với model thật

- Yêu cầu: (1) triển khai P0 của kế hoạch khắc phục RAG (chặn 422 cứng và abstain sai do mở rộng ngữ cảnh); (2) chạy thử 10 câu phiên 935 với model thật để so sánh trước/sau. Ràng buộc giữ nguyên: không retry câu hỏi model để làm xanh kết quả, không nới assertion/bỏ guard, lỗi nền giữ riêng, `NOT RUN` không phải `PASS`; F13 vẫn là vấn đề chất lượng riêng; không test trên DB ứng dụng, không cài dependency, không commit/push/deploy/reindex.

## P0 — phạm vi đã sửa (chưa commit)

- `backendV1/qnu/domains/rag/answer/structure_context.py`: continuation group chỉ mở rộng đúng mép câu bị cắt quanh anchor, tối đa 6 record/6.000 ký tự mỗi mảnh, gắn `optional: true`, `chain_records`, `truncated`; chuỗi OCR dài không còn biến toàn chuỗi thành bằng chứng bắt buộc.
- `backendV1/qnu/domains/rag/answer/context.py`: precheck ngân sách sớm chỉ tính evidence dạng văn bản (`narrative_bytes`), vì JSON bảng chỉ là biểu diễn retrieval còn model nhận catalog ô/thu gọn; clause group vượt ngân sách bị bỏ nguyên nhóm và đếm `clause_skipped_budget` thay vì 422; `context_window=0` nối lại các part của cùng đoạn (tối đa 4, `kind="part"`, `parts_joined`); trace `added.kind` giữ đúng `continuation|clause|...` thay vì gộp `structure`.
- `backendV1/qnu/domains/rag/answer/packing.py`: chỉ continuation/part là tùy chọn và được cắt ở bất kỳ vị trí nào; clause/table support vẫn bắt buộc; 422 chỉ còn khi envelope bắt buộc thật sự vượt ngân sách.
- `backendV1/qnu/domains/rag/answer/selection.py`: `required_ids` của group `optional` không còn ép chọn.
- `backendV1/tests/unit/test_rag_context_908.py`: cập nhật hợp đồng `kind`; thêm 4 regression: chuỗi dài bị giới hạn/optional, nối part khi window=0, table primary hoãn ngân sách cho envelope, clause vượt ngân sách bị bỏ thay vì 422.

## Kiểm chứng P0 (thực chạy)

- `uv run pytest tests/unit/test_rag_context_908.py tests/unit/test_rag_clause_context_856.py tests/unit/test_rag_modelops_budgets_767.py -q` → **45 passed**, 2,81 giây.
- `uv run --project backendV1 python backendV1/scripts/run_isolated_tests.py tests/integration/test_rag_context_908.py -q` → **3 passed**, 38,69 giây; harness 48,09 giây, DB `qnu_v1_test_ae1bda57f84741af` đã xóa, sentinel giữ, `pytest_exit=0`.
- Ruff check + format check 5 tệp P0: **PASS** (0 lỗi, 5 tệp đã đúng format).
- DB ứng dụng không bị chạy test; chỉ đọc audit để lấy mã lỗi Q1.

## Chạy thật 10 câu trên build P0

- API cũ chạy mã trước P0 (khởi động 18:27, không `--reload`) được dừng và khởi động lại; log ghi `backend_v1_started` lúc `2026-11-11T14:26:31.622023Z`, health 200.
- Giữ nguyên kịch bản phiên 935: collection `col_da0fa3ca3177`, workspace `ws_686011c2a0af`, `hybrid_rerank`, `top_k=5`, `candidate_k=30`, `rrf_k=60`, rerank `prv_adff3afa1648`, verification off, generation 2 `idx_f8d44c0ec319`; model `qwen3.8-27b-q4`/`prv_76af5b1d51eb`.
- Mỗi câu gửi đúng một lần. Q1 gặp lỗi mã hóa console cp1252 của runner khi in tiếng Việt **sau khi** đã nhận phản hồi; không gửi lại Q1, giữ nguyên kết quả 502/19,19 giây và đọc bổ sung mã lỗi `answer_response_invalid` từ audit (chỉ đọc). Q2–Q10 chạy tiếp với `PYTHONIOENCODING=utf-8`.

| Câu | 935 lần đầu | P0 | Bằng chứng chính |
| --- | --- | --- | --- |
| Q1 | 502 soạn/kiểm tra | 502 `answer_response_invalid` | 19,19 giây; model trả cấu trúc không hợp lệ, không có body do runner lỗi mã hóa |
| Q2 | PASS | 502 `answer_response_invalid` | 9,56 giây; root validator từ chối `status`/`statements` |
| Q3 | 502 | 200 `answered`, **PASS theo token** | 18,20 giây; nêu 51 ngành + 01 CLC Kế toán + hai ngành dự kiến mở, nhưng vẫn thêm đoạn "04 ngành/16 chỉ tiêu" của mục tiến sĩ |
| Q4 | PASS | 502 `answer_response_invalid` | 12,89 giây; cùng lớp lỗi Q2 |
| Q5 | abstain sai | 200 `insufficient_evidence` | 12.599/16.000 byte (văn bản 2.156); continuation 1 group `optional`, 119 `required_ids` không còn ép chọn, thêm 50 chunk; model vẫn abstain |
| Q6 | retrieval miss | 200 `insufficient_evidence` | 14.553/16.000 byte; 2 group optional, thêm 53 chunk; 4 nguồn nhưng chỉ 1 TSDH, thiếu `5.173` |
| Q7 | retrieval miss | 200 `insufficient_evidence` | 11.931/16.000 byte; thêm 1 chunk; 0 nguồn trích dẫn |
| Q8 | PASS kèm lỗi phụ | 200 `insufficient_evidence` | 8.033/16.000 byte; 0 nguồn trích dẫn dù evidence học phí có trong ngữ cảnh |
| Q9 | 422 ngân sách | 422 `answer_context_budget_exceeded` | 6,93 giây; "Bằng chứng bắt buộc vượt ngân sách context." tại envelope bắt buộc |
| Q10 | 422 ngân sách | 422 `answer_context_budget_exceeded` | 6,28 giây; cùng nguyên nhân |

- Tổng: **1/10 đạt theo bộ kiểm tra token** (chỉ Q3). Thời gian 10 lượt gồm cả lượt lỗi: trung bình 13,30 giây, trung vị 13,70, cao nhất 19,58.
- Bằng chứng: `%TEMP%\qnu_e2e_935_p0_rag_all.json` (đủ phản hồi + `trace.context`), `%TEMP%\qnu_e2e_935_p0_rag_rest.log/json`, `%TEMP%\qnu_api_8002_p0.log`, runner `%TEMP%\qnu_e2e_935_p0_rag.py`; token chỉ đọc từ `%TEMP%\qnu_e2e_token.txt`, không in.

## Diễn giải

- P0 đạt đúng mục tiêu cơ chế: continuation group đã `optional` và bị giới hạn (Q5 không còn kéo 55 chunk/12.671 byte bắt buộc như baseline; nay 50 chunk/12.599 byte tùy chọn), clause vượt ngân sách bị bỏ thay vì 422, precheck sớm không còn tính JSON bảng.
- P0 **không cải thiện kết quả cuối** trên corpus này: Q5/Q6/Q7/Q8 vẫn abstain, Q9/Q10 vẫn 422. Q9/Q10 nay lỗi ở bước đóng gói vì cả 5 primary hit đều là bảng lớn bắt buộc, không còn phần tùy chọn để cắt — cần P2 (grounding bảng/cell catalog), không phải P0.
- Q1/Q2/Q4 502 `answer_response_invalid` là model trả `status`/`statements` không khớp root validator; cùng lớp lỗi đã xuất hiện ở phiên 936 (Q1/Q3/Q4) trước P0, nên không quy cho P0, nhưng vẫn là lỗi mở thuộc P3.
- Q6/Q7 vẫn là retrieval/rerank bỏ sót chunk đúng (P1); Q5/Q8 là model bỏ bằng chứng ngay trong ngữ cảnh (grounding, P2/P3).
- Q3 chỉ đạt theo token; câu trả lời còn trộn chi tiết mục tiến sĩ nên chưa đạt nội dung.

## Giới hạn

- Full Pytest cô lập: **NOT RUN**. Baseline lịch sử **FAIL 4/1627** (phiên 928) giữ riêng, không chạy lại.
- F13 vẫn mở; đây là kịch bản chẩn đoán một lượt, không phải benchmark; chưa commit/push/reindex, không đổi mặc định RAG.
- P1 (recall rerank/fusion), P2 (grounding bảng), P3 (ngữ nghĩa lỗi/verification), P4 (hiệu năng/đo lường) và P5 (tách embedding, cần duyệt reindex) chưa triển khai.
