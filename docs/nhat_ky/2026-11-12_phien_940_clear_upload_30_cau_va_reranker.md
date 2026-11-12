# Phiên 940 — Clear DB, upload tệp kiểm thử phức tạp, 30 câu RAG và xác minh bge-reranker-v2-m3

Ngày: 2026-11-12. Nhánh: `feat/v1-user-workflow`. Không sửa mã ứng dụng; phiên này là reset hạ tầng dev, E2E đường ống, soạn bộ câu hỏi và đo/chan đoán chất lượng RAG.

## 1. Yêu cầu và giả định

- Người dùng yêu cầu: (1) clear lại hết dữ liệu dev, (2) upload tệp `docs/tai_lieu/tuyen_sinh/tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).pdf` qua toàn bộ đường ống, (3) tạo khoảng 30 câu hỏi để thử RAG, (4) kiểm tra lại việc dùng `bge-reranker-v2-m3`.
- Ràng buộc giữ nguyên: mỗi câu hỏi chạy đúng một lần, không retry để làm xanh; không nới assertion/bỏ guard; lỗi nền báo riêng; `NOT RUN` không phải `PASS`; không commit/push/deploy; không chạy test trên DB ứng dụng (chỉ đọc DB để chẩn đoán); không cài thêm dependency.
- Giả định: bộ 30 câu do trợ lý soạn từ văn bản đã xuất bản, gắn nhãn `draft_needs_human_check`, chưa có người duyệt; chấm nội dung bằng đọc thủ công từng câu trả lời và đối chiếu chunk đã packed, không phải benchmark đã hiệu chuẩn.
- Tài liệu kiểm thử là văn bản mô phỏng có chủ đích nhiều bẫy (mã giữ số 0, bảng nhiều năm, ký hiệu chưa giải thích, điều kiện ngoại lệ riêng nhóm). Điểm số không so sánh trực tiếp với các lượt 10 câu đóng băng trước đó (corpus khác, khó hơn).

## 2. Lệnh thật đã chạy

Reset hạ tầng (người dùng cho phép rõ hành động phá hủy này):

```bash
backendV1/.venv/Scripts/python.exe scripts/run_v1.py v1-clear --confirm-local-reset   # docker compose down --volumes
backendV1/.venv/Scripts/python.exe scripts/run_v1.py v1-infra-up
backendV1/.venv/Scripts/python.exe scripts/run_v1.py v1-migrate    # 0001 -> 0025_index_fts_gin
backendV1/.venv/Scripts/python.exe scripts/run_v1.py v1-db-check
backendV1/.venv/Scripts/python.exe scripts/run_v1.py v1-seed-modelops
# seed workspace shl + 4 vai trò dev (khóa local trong backendV1/.local/, không ghi tài liệu)
cd backendV1 && uv run --frozen --env-file ../.env python -m scripts.seed_shl_pilot
backendV1/.venv/Scripts/python.exe scripts/run_v1.py dev           # nền: API 8002 + worker ARQ + FE V2 3002
```

E2E và đo (script tạm trong `%TEMP%`, không đưa vào Git):

```bash
cd backendV1 && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "$TEMP/qnu_e2e_940.py" <stage>
# stage: providers | upload | processing | inspect | review | publish | index | verify
cd backendV1 && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "$TEMP/qnu_e2e_940_rag.py"   # 30 câu, một lượt
cd backendV1 && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "$TEMP/qnu_e2e_940_chunks.py" # dump chunk chỉ đọc
```

## 3. Kết quả đường ống (PASS)

- PDF 18 trang có text layer, SHA-256 `082c412e145a9ef39ae50110ae16cc80c17d612e2f0e00f9d16ee78c7c1c3b02`.
- Workspace `ws_39c202a81045` (shl), collection `col_0daa6e0ed137`; nguồn `src_50f6ed92a4e8`, revision `rev_e15b0b6456cd`.
- OCR `ocr_ae8951d2e380` 18/18 trang; soát chính tả tự động `spl_0b09b4bde08b` **0 gợi ý / 0 withheld** (tài liệu gõ sạch, không phải scan) → duyệt zero-change (giữ version 0, `change_count=0`, đúng nhánh `review_check_id` của `ocr/review/service.py`).
- Chuẩn bị source-first `cmp_515a79a13c96`; đăng ký `cdoc_a954f08966c9`/`cver_a7b7eb6b9553`; duyệt `pdec_78853b57c4c0`; xuất bản `pdec_8629e6ad3577` lúc 09:47:50 (upload bắt đầu 09:42:47).
- Hash: text `460650778aac...848ab2bd`, bundle `5d188823630d...443c61443d`, retrieval metadata `17e865ab590a...41962cdd2`.
- Index tự động `idx_bfd36fae5a30` generation 1, **465 chunk**, active, manifest `f166b78049a9...f0d7c91ac`; readiness `ready` revision 1; search `hybrid_rerank` trả 5 hit đúng `cver_a7b7eb6b9553`.
- Providers sau seed: chat `prv_902ce43408bb` (qwen3.8-27b-q4), embedding `prv_11ee2f5b600b` (bge-m3), rerank `prv_8f5c1f17c932` (bge-reranker-v2-m3), OCR `prv_2cc9652cb832` (mineru), chat phụ `prv_3aac366438d8` (cx/gpt-6-luna, không dùng trong lượt đo).

## 4. Xác minh bge-reranker-v2-m3 (PASS — chạy thật)

Ba lớp bằng chứng, không chỉ nhìn cấu hình:

1. Seed ModelOps + danh sách provider live: capability `rerank`, model `bge-reranker-v2-m3`, type `openai_compatible`.
2. Search trực tiếp sau publish: trace `rerank_provider` đầy đủ, usage `usage_b7e014944cf142bd`, **6.358 token, 922 ms**, presentation `qnu.evidence-reading/v1`, weight 2.0 (lưu `%TEMP%/qnu_e2e_940_rerank_proof.json`).
3. Lượt 30 câu: **28/30 phản hồi có rerank áp dụng** trong `trace.retrieval` với đúng model `bge-reranker-v2-m3`; Q04/Q06 lỗi HTTP 502 trước khi hoàn tất nên không có trace rerank.

## 5. Bộ 30 câu và kết quả một lượt

- Câu hỏi lưu `%TEMP%/qnu_e2e_940_questions.json` (không đưa vào Git): 28 câu trả lời được + 2 câu dò abstain (Q28 doanh thu 2025, Q29 ghi nhận 2024 AM-0007 — không có trong tài liệu). Phủ: ngày tháng (Q01–03), ô bảng/bẫy mã (Q04–08), liệt kê (Q09, Q23), ngoại lệ riêng nhóm (Q10–12), công thức (Q13–15), toán tử/bảng cùng tên (Q16–17), ký hiệu (Q18–19), nhiệm vụ (Q20–22), thẩm quyền (Q24), định kỳ (Q25–26), bẫy liên bảng (Q27), gián đoạn (Q30).
- Tham số: `hybrid_rerank`, `top_k=5`, `candidate_k=30`, `rrf_k=60`, rerank `prv_8f5c1f17c932`; model trả lời `qwen3.8-27b-q4`.
- **Token-level: 14/30 PASS** (bộ kiểm tra required/forbidden/abstain trong runner).
- **Chấm nội dung thủ công: 16 đúng / 5 thiếu ý / 5 abstain sai dù bằng chứng đã packed / 2 abstain do lỗi pipeline / 2 lỗi hạ tầng 502.**
- Latency: mean **8,08 s**, p50 7,93 s, max 10,88 s; tổng 89.601 prompt token + 4.954 completion token (30 câu).
- Hai câu dò abstain Q28/Q29 đều abstain đúng (`insufficient_evidence`/`model_abstained`).

### Phân loại 16 câu không đạt token (đã chẩn đoán, không chạy lại)

| Nhóm | Câu | Bằng chứng |
|---|---|---|
| Abstain sai dù đủ bằng chứng trong prompt (lớp F13) | Q05, Q07, Q09, Q19, Q20 | Giá trị đáp án nằm trong chunk đã packed (đối chiếu `ich_3ebc9ee12d5a` 93,3/0120/6 tên, `ich_76e3ea6dac2f` 1233/1149, `ich_df4f0876e810` quy tắc 0/trống/chưa công bố...); `bytes_used` dưới ngân sách 32 KB; model vẫn `model_abstained` |
| Lỗi pipeline thật | Q08 | Chunk nhóm B (`ich_a37335a12e96`, AM-0029/127) có trong lexical top-30 nhưng rơi khỏi fusion top-30 |
| Lỗi pipeline thật | Q13 | Chunk công thức `ich_18e57e5dec06` (Q = 0,45×A + 0,35×B + 0,20×C) rerank #2 / fusion #5 nhưng không được chọn vào prompt |
| Trả lời thiếu ý | Q10 | Thiếu điều kiện phê duyệt Phụ lục II.1 (kiểm định, Phòng Đào tạo) |
| Trả lời thiếu ý | Q12 | Thiếu cơ chế biên bản xác minh trực tuyến / P.HTDN |
| Trả lời thiếu ý | Q18 | Thiếu mã quyết định AM/TN-02 |
| Trả lời thiếu ý (lỗi ngữ nghĩa thật) | Q24 | "05 ngày" đánh rơi "làm việc" |
| Trả lời thiếu ý | Q27 | Không nêu CS-02 = "Cần làm rõ" |
| Nội dung đúng nhưng trượt token | Q16 | Toán tử > 15 vs >= 15 đúng; đơn vị giờ/người, giờ/khoa không hiện nguyên văn |
| Nội dung đúng nhưng trượt token | Q21 | Trả lời đúng đầy đủ; "không được gộp" không khớp chuỗi dò "không gộp" |
| Hạ tầng | Q04, Q06 | HTTP 502 body rỗng từ provider/gateway; giữ nguyên, không retry |

Ghi chú chất lượng thêm: Q23 đúng và đủ nhưng là trích nguyên văn ô NV-30 (~2.003 ký tự, 78 completion token, 1 statement) thay vì tổng hợp.

## 6. Sửa trong phiên (không phải mã ứng dụng)

- Runner `qnu_e2e_940_rag.py` đọc nhầm `trace.ranking`/`trace.rerank_provider` ở cấp trên cùng trong khi trace trả lời lồng dưới `trace.retrieval` → summary ban đầu báo `rerank_applied_count=0`. Đã tính lại summary và trường rerank từng câu **từ phản hồi đã lưu**, không gửi lại câu hỏi nào; ghi chú trong `summary.rerank_note`.
- Chấm nội dung thủ công ghi vào `content_review` từng câu + `summary.content_review` trong `%TEMP%/qnu_e2e_940_rag_results.json`.
- Hai lỗi đánh máy tiếng Trung lẫn vào file câu hỏi lúc soạn đã sửa ngay trước khi chạy.

## 7. Kiểm chứng và giới hạn

- E2E đường ống 8 stage: **PASS** (biên nhận `%TEMP%/qnu_e2e_940_report.json`, `result=PASS`).
- Xác minh reranker 3 lớp: **PASS**.
- Lượt 30 câu: chạy thật một lượt; token 14/30, nội dung 16/30 — **không phải benchmark**, nhãn chưa người duyệt.
- Full Pytest cô lập: **NOT RUN**; baseline lịch sử **FAIL 4/1627** (phiên 928) giữ riêng, không chạy lại.
- **F13 vẫn mở**: lớp abstain-sai-dù-đủ-bằng-chứng tái diễn trên corpus mới (5/30 câu), prompt v24 của phiên 939 không chặn được lớp lỗi này ở tài liệu phức tạp hơn. Không tuyên bố đã sửa.
- Không sửa mã sản phẩm, không đổi mặc định retrieval, không reindex ngoài index tự động của lần publish này, chưa commit/push. DB ứng dụng chỉ đọc để chẩn đoán (dump chunk), không chạy test trên đó.
- Dev stack vẫn chạy nền (API 8002 + worker + FE V2 3002).

## 8. Rủi ro và bước sau (chưa duyệt)

1. Chẩn đoán 5 câu abstain sai (Q05/Q07/Q09/Q19/Q20): đối chiếu envelope thật và hành vi model; đây là lớp F13, cần hướng riêng, không nới guard.
2. Q08: vì sao chunk nhóm B rơi khỏi fusion dù có trong lexical top-30 (RRF/trọng số hay dedup).
3. Q13: vì sao selection loại chunk công thức xếp rerank #2 (nhóm clause/required_ids hay ngân sách).
4. Q04/Q06: lỗi 502 hạ tầng provider — theo dõi riêng, không quy về chất lượng RAG.
5. Người duyệt rà 30 nhãn `draft_needs_human_check` trước khi dùng làm thước đo.
6. Cân nhắc bộ câu đóng băng đa tài liệu để so sánh công bằng giữa các phiên.

## 9. Artifact (ngoài Git, trong %TEMP%)

`qnu_e2e_940.py`, `qnu_e2e_940_state.json`, `qnu_e2e_940_report.json`, `qnu_e2e_940_questions.json`, `qnu_e2e_940_rag.py`, `qnu_e2e_940_rag_results.json`, `qnu_e2e_940_rerank_proof.json`, `qnu_e2e_940_chunks.py`, `qnu_e2e_940_chunk_dump.json`, `qnu_940_pdf_text.txt`.