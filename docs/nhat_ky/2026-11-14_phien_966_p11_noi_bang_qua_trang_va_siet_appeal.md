# Phiên 966 — 2026-11-14 — P1.1 nối bảng phụ lục qua trang cho Q74 và siết điều kiện gọi lại

## Yêu cầu và phạm vi

- Người dùng chọn **phương án 2** trong ba phương án sau P1: **P1.1a** nối bảng phụ lục qua trang cho Q74 ở tầng trả lời (không reindex) + **P1.1b** siết điều kiện gọi lại: chỉ appeal khi một bước kiểm tra xác định xác nhận envelope đã có đủ dữ kiện bắt buộc, để giảm các ca trả lời liều. **P2** (quyết định model qua ModelOps, chạy lại 100 câu) **chưa duyệt**; G3 vẫn chờ duyệt.
- Môi trường đo: trợ lý `ast_47f30aaf2665` rev 3, kho `col_9209e90d1a53`, `top_k=5`, `candidate_k=40`, `hybrid_rerank`, scope explicit, `context_max_bytes=32000`, `verification_mode=off`, model `qwen3.8-27b-q4` (mặc định hệ thống). API :8002 chạy từ mã P1.1 (uvicorn, PID 10436, `/health` 200); worker/FE không đụng; không reindex/migration; DB dev ở head 0028.

## File đã sửa (chưa commit)

| File | Thay đổi | Dòng |
|---|---|---|
| `backendV1/qnu/domains/rag/answer/table_context.py` | `PAGE_BAND_BASIS = "native_page_band_continuation/v1"`, ngưỡng `BOTTOM_BAND=0.88`/`TOP_BAND=0.12`, `_serving_table` (chỉ bảng native đã parse, không review, bbox chuẩn hóa), `_ends_above`, `_opens_table` (header_row/typed_header/multitier), `page_continuations(document, proven)` sinh liên kết giả cho cặp trang liền kề khi bảng trái chạm đáy trang + bảng phải mở đầu trang kế + thẳng cột + không có proof số/typed/multitier nào; `bound_dependencies` chỉ `setdefault` nên không ghi đè proof thật. Link trái `{basis, header: left_ref, chain: [left_ref], previous: None}`; link phải `{basis, header: left_ref, chain: [left_ref, right_ref], previous: left_ref}` — cố ý để `_support_link` kéo cả header (ord 179) lẫn chunk trước (ord 180) | 22–29, 48–53, 96–103, 133 |
| `backendV1/qnu/domains/rag/answer/coverage.py` | `plan_ready(plan)` = không còn `unresolved_references` và mọi group không còn `unprovided_units` — envelope đã mang đủ mọi đơn vị mà kế hoạch chứng minh là bắt buộc | 66–71 |
| `backendV1/qnu/domains/rag/answer/service.py` | Import `plan_ready`; khối appeal: nếu `draft.status == "insufficient_evidence"` mà `plan_ready(plan_for(sources, trace.context))` **sai** → ghi `trace.appeal = {version, attempted: False, outcome: "skipped_structure"}` và giữ abstain, không gọi model; chỉ nhánh `elif` mới chạy appeal một lần như P1 | 23, 406–421 |

Ghi chú: các diff P0 (cells/context/table_support/handlers) và P1 (drafting/schemas) giữ nguyên; `fallback.py` (untracked) vẫn là việc dở phiên trước, không thuộc P1.1.

## Phương pháp đo

- Runner `%TEMP%/qnu_p11_8x3.py` (ngoài Git), cùng 8 câu nhóm P1: Q12, Q19, Q24, Q53, Q74, Q78, Q85, Q88 × 3 lượt = **24 lượt** qua API hội thoại thật (`Idempotency-Key` tiền tố `p11-`, hội thoại mới mỗi lượt); kết quả `%TEMP%/qnu_p11_8x3_results.json`, resume được.
- Token đọc `answer_prompt_tokens` (token model trả lời), cùng nguồn với P1 (`%TEMP%/qnu_p1_8x3_results.json`).
- Chấm tay theo nguồn đã xuất bản trong `kb_index_chunks` run `idx_0a4fbb712a1e` (chỉ đọc): PHỤ LỤC 1 ord 179–180 trang 13 + ord 181 trang 14 (`ev_p014_b003`, "Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204"); bảng danh mục trang 5 ord 165 (hàng ACCA "7340301 AC", 30 chỉ tiêu; hàng Kế toán thường "7340301", 257 chỉ tiêu); mục 6 tổ chức tuyển sinh ord 91–101; quy tắc cộng điểm thể thao/điểm cộng-tie-break.
- Đối chiếu chéo JSON P1.1 với JSON P1 để tách tác động của mã khỏi sampling; mỗi câu kiểm tra `support_ids`/`table_links`/`trace.appeal` thay vì chỉ nhìn câu chữ.

## Kết quả đo (24 lượt)

| Câu | P1 answered/3 | P1.1 answered/3 | Appeal P1.1 | Chấm nội dung P1.1 | Kết luận |
|---|---|---|---|---|---|
| Q12 | 2/3 | 3/3 | 0 | 3/3 đạt: nêu PT1/mã 100; lượt 2–3 nêu thêm PT5/mã 405 nhưng thiếu vế "điểm thi năng khiếu" của PT5 (cùng mức chấp nhận đã dùng ở phiên 965) | **PASS** |
| Q19 | 3/3 | 3/3 | 0 | **1/3**: chỉ lượt 1 nêu đủ "điểm thi THPT 2026 + điểm thi năng khiếu GDMN/GDTC"; lượt 2–3 chỉ nêu điểm THPT | **FAIL** |
| Q24 | 0/3 | 1/3 + 1 abstain | 1 (`invalid`) | **0/3**: lượt 1 abstain sai vì cho rằng tài liệu "chưa có" ngành ACCA (thực tế có), appeal lỗi schema `lookups[0].cell_id` nên giữ abstain trung thực; lượt 2 trả lời nhầm hàng Kế toán thường (7340301, 257 chỉ tiêu); lượt 3 502 `answer_table_value_not_extractive` | **FAIL** |
| Q53 | 3/3 | 3/3 | 0 | **1/3**: lượt 2 đúng 20/5–15/6; lượt 1 đảo mốc 15/6–20/6; lượt 3 lấy ngày thi 19–21/6 | **FAIL** |
| Q74 | 3/3 | 3/3 | 0 | **2/3**: lượt 2–3 tách đúng "Tiếng Trung → Ngôn ngữ Trung Quốc" và "Đông phương học cần Lịch sử"; lượt 1 gộp Đông phương học cho cả Tiếng Trung (sai) | **PASS mục tiêu hẹp** (dẫn chứng), nội dung 2/3 |
| Q78 | 3/3 | 3/3 | 0 | **2/3**: lượt 2 thiếu cụm "cộng 3 điểm" và điều kiện đã thi năng khiếu, chỉ còn "≤4 năm" + điều kiện thể chất | **PARTIAL** |
| Q85 | 3/3 | 3/3 | 0 | **3/3** đúng 02/7–14/7 | **PASS** |
| Q88 | 3/3 | 3/3 | 2 (`answered` ×2) | **3/3** đúng: điểm cộng thấp hơn trước, bằng nhau thì nguyện vọng cao hơn | **PASS** |

Tổng: **answered 20→22/24**; abstain 0→1 (trung thực, giữ nguyên sau appeal lỗi); 502 cứng 4→1 (`answer_table_value_not_extractive` Q24#3, guard thiết kế; 0 `answer_evidence_changed`, 0 lỗi provider/hạ tầng). Appeal: P1 4/4 `answered` nhưng 3/4 sai nội dung; P1.1 chỉ 3 lượt kích hoạt — 2 `answered` đúng nội dung (Q88#2–3), 1 `invalid` giữ abstain (Q24#1); **0 `skipped_structure`** trong mẫu này.

## Bằng chứng Q74 — mục tiêu chính của P1.1a

- Cả 3 lượt Q74 đều có `ich_676e38631065` (ord 181, trang 14, `ev_p014_b003`) trong `support_ids`/`primary_ids`; trace `table_support: resolved`; `table_links` = 6, trong đó 3 link basis `native_page_band_continuation/v1` nối `ocr_9f18675ed811:ev_p013_b003` → `ev_p014_b003`; `supports()` chỉ gắn đầu block kế khi `original_row_count - 1` nằm trong `row_indices`, nên hàng quyết định đến được envelope.
- Hệ quả: **phủ định sai của P1 biến mất** — P1 cả 3 lượt nói "không có/không tìm thấy ngành Ngôn ngữ Trung Quốc" (0/3); P1.1 2/3 trả lời đúng, 1 lượt còn over-claim Đông phương học. Đây là lỗi chọn dòng của model trên envelope đã đủ, không phải lỗi dẫn chứng.
- Giới hạn có chủ đích: rule chỉ nhận bảng **native** ở đáy/đầu trang liền kề, bỏ qua proof số/typed/multitier (không ghi đè), và bỏ qua trang trích `hybrid` — nên khoảng nối 28 hàng `ev_p011_b014` → `ev_p012_b001` (trang 12 hybrid) vẫn chưa được nối; chưa có bằng chứng cần mở rule cho hybrid.

## Q24 — dẫn chứng đủ nhưng model chọn sai

- Lượt 2 P1.1 có `ich_cc631adf9438` (ord 165, trang 5, rows 0–7, chứa đúng hàng "7340301 AC | Kế toán ( Định hướng ACCA) | 1,2,3,4 | 30") trong `primary_ids`, nhưng model chọn hàng Kế toán thường 257 chỉ tiêu. Đây là lỗi chọn hàng/hợp đồng output, không phải thiếu envelope; guard extractive của lượt 3 phản ứng đúng.
- Tương tự Q19/Q53/Q78: envelope không đổi so với P1, khác biệt câu chữ là sampling của model 27B cục bộ. Các câu này thuộc nhóm chất lượng sinh, không sửa được bằng nối bảng hay siết appeal.

## Kết quả cổng

| Cổng | Kết quả | Chi tiết |
|---|---|---|
| T1 — Q74 có dẫn chứng qua trang | **PASS** | `ich_676e38631065` trong envelope cả 3/3 lượt; link basis mới trong trace; 2/3 trả lời đúng |
| T2 — Siết điều kiện appeal | **PASS cơ chế, NOT OBSERVED trên live** | `plan_ready` chặn nhánh appeal khi thiếu đơn vị bắt buộc và ghi `skipped_structure`; mẫu 24 lượt không có lượt nào rơi vào nhánh này (0 `skipped_structure`), nên tác dụng giảm trả lời liều chưa được quan sát trực tiếp; 3 appeal còn lại đều có cấu trúc đủ (Q24#1 lỗi ngữ nghĩa/schema, Q88#2–3 model abstain dù đủ) |
| G2 — chấm nội dung (≥7/8 đúng, 0 số bịa) | **FAIL** | **3/8 đúng trọn** (Q12, Q85, Q88); Q74 2/3, Q78 2/3, Q19 1/3, Q53 1/3, Q24 0/3. **0 số bịa**; sai sót là chọn nhầm dòng/thiếu vế điều kiện |
| 502 cứng | **1/24** | Q24#3 `answer_table_value_not_extractive` (guard trung thực); 0 `answer_evidence_changed`, 0 lỗi provider |
| Chi phí token | **PASS trong phạm vi** | Trung bình token/lượt trả lời 4.819,6 → 4.826,7 (+0,15%); tối đa 8.308 → 8.129 (−2,2%); Q53 2.955→2.713, Q74 8.308→8.129; các câu còn lại cùng dải |
| Độ trễ | **PASS** | Trung bình 9,5 → 8,9 s (−6%); tối đa 16,8 → 17,2 s (+0,4 s) |
| G5 — mã | **PASS** | Ruff sạch 3 tệp (`table_context.py`, `coverage.py`, `service.py`); import `qnu.main` OK; API khởi động lại và `/health` 200 |
| G6 — quan sát | **PASS** | 24/24 lượt có `trace.appeal`; 3 lượt có token hai lần gọi; trace Q74 có basis liên kết trang mới |
| pytest | **NOT RUN** | Theo yêu cầu thường trực — không phải PASS |

## Đính chính số liệu P1 (đọc lại JSON đã lưu, không chạy lại)

- Danh sách "3/8 đúng trọn" ở nhật ký 965/mục 14 ghi **(Q12, Q19, Q88)**; rà lại JSON P1: Q12 chỉ **2/3 lượt trả lời được** (lượt 3 502) nên không thể tính 3/3. Với cùng quy tắc "cả 3 lượt trả lời được và đều đúng", P1 đạt trọn **Q19, Q78, Q88** (Q78 vẫn kèm ghi chú thiếu điều kiện phụ như mục 14). Kết luận **G2 vẫn FAIL 3/8**, không đổi.
- Q19 P1 đạt 3/3 (đủ vế năng khiếu); Q53 1/3, Q74 0/3, Q85 2/3 đúng như mục 14.

## Bài học

- **Nối đúng trang là điều kiện cần, không phải điều kiện đủ**: hàng trang 14 giờ như trang giấy bị rời đã được dán lại đúng chỗ trong tập tài liệu; nhưng thí sinh vẫn có thể đọc nhầm dòng (Q24) hoặc gộp hai ngành (Q74#1). Sửa dữ kiện không thay được sửa cách chọn.
- **Appeal chỉ đáng dùng khi envelope đã đủ**: với Q24#1, envelope có dòng ACCA nhưng model hiểu sai ngữ nghĩa; nếu `plan_ready` không phát hiện được "đủ nhưng chọn sai", appeal vẫn có thể trả lời liều. Vì vậy T2 mới chỉ chứng minh cơ chế, chưa chứng minh hiệu quả giảm liều trên mẫu này.
- **Abstain trung thực vẫn được giữ**: appeal lỗi schema → outcome `invalid` → giữ nguyên `insufficient_evidence`, đúng bất biến 1.
- **Không có `skipped_structure`** nghĩa là các ca `insufficient_evidence` lần đầu trong mẫu đều do model (ngữ nghĩa), không do thiếu đơn vị cấu trúc — muốn thấy cổng mới hoạt động phải có ca envelope thiếu thật (ví dụ Q24 cũ của P0).

## Lệnh thật đã chạy

- Ruff: `backendV1/.venv/Scripts/python.exe -m ruff check qnu/domains/rag/answer/table_context.py qnu/domains/rag/answer/coverage.py qnu/domains/rag/answer/service.py` → "All checks passed!".
- Import smoke: `import qnu.main` → "import ok".
- API: dừng PID cũ, chạy `backendV1/.venv/Scripts/uvicorn.exe qnu.main:app --app-dir backendV1 --host 127.0.0.1 --port 8002` (nền, PID 10436); `/health` 200.
- Đo: runner 24 lượt qua API hội thoại; đọc `kb_index_chunks` chỉ đọc qua `AsyncSessionFactory` (`qnu.platform.database`, `IndexChunk` ordinal/kind/text, run `idx_0a4fbb712a1e`).
- Không in/xu lộ secret, token, nội dung nguồn; file đo trong `%TEMP%`, ngoài Git. Không commit/push/deploy; không reindex/migration; không đụng worker/FE.

## File đo (ngoài Git)

- `%TEMP%/qnu_p11_8x3.py` (runner), `%TEMP%/qnu_p11_8x3_results.json` (24 lượt), `%TEMP%/qnu_p1_8x3_results.json` (so sánh P1), `%TEMP%/qnu_questions_100_results.json` (baseline 100 câu).

## Rủi ro còn lại và bước sau

1. **G2 vẫn FAIL** — 3/8 đúng trọn; các câu còn lại là chất lượng chọn dòng/ngữ nghĩa của model 27B. **P2** (đổi model qua ModelOps) chưa duyệt.
2. **G3 chưa chạy** — cần duyệt chạy lại 100 câu để chắc 84 câu cũ không hồi quy; P1.1 chưa được đo trên toàn bộ.
3. **T2 chưa thấy tác dụng live** — không có `skipped_structure` trong 24 lượt; muốn đánh giá giảm trả lời liều cần mẫu có abstain do thiếu cấu trúc thật.
4. **Nối bảng qua trang cho trang `hybrid`** (khoảng 28 hàng `ev_p011_b014` → `ev_p012_b001`) chưa xử lý — có chủ đích, cần bằng chứng trước khi mở rule.
5. Nhóm 502 extractive-guard cũ (task #163) và Q24-content vẫn là việc mở; không thuộc phạm vi P1.1.
