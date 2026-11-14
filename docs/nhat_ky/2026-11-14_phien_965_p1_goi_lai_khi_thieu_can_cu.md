# Phiên 965 — 2026-11-14 — P1 gọi lại một lần khi model bỏ trắng dù có dữ kiện (theo kế hoạch 2026-11-14)

## Yêu cầu và phạm vi

- Người dùng duyệt **P1** ("ok duyệt P1") của `docs/ke_hoach/2026-11-14_ke_hoach_sua_16_cau_loi_tro_ly_tuyen_sinh.md` mục 5: một lần gọi lại tối đa khi model trả `insufficient_evidence` dù bằng chứng đã pack, dùng **đúng envelope + catalog** (không đổi bằng chứng), không nới schema/guard số, trace `appeal`, mọi lỗi appeal giữ nguyên abstain trung thực lần 1. **P2** (đo lại 100 câu + quyết định model) **chưa duyệt**; G3 (chạy lại 100 câu) vẫn chờ duyệt.
- Môi trường đo: trợ lý `ast_47f30aaf2665` rev 3, kho `col_9209e90d1a53`, `top_k=5`, `candidate_k=40`, `hybrid_rerank`, scope explicit, `context_max_bytes=32000`, `verification_mode=off`, model `qwen3.8-27b-q4` (mặc định hệ thống). API :8002 chạy từ mã P1 (PID 27332); worker/FE không đụng; không reindex/migration; DB dev ở head 0028.

## File đã sửa (chưa commit)

| File | Thay đổi | Dòng |
|---|---|---|
| `backendV1/qnu/domains/rag/answer/drafting.py` | `APPEAL_VERSION = "qnu.rag.answer.appeal/v1"`, `APPEAL_INSTRUCTION` (yêu cầu đánh giá lại từng ý, trả lời phần có căn cứ, không bịa) và `appeal_messages()` = đúng envelope đã pack + 1 message chỉ dẫn | 16, 18, 35–37 |
| `backendV1/qnu/domains/rag/answer/schemas.py` | `AnswerTrace.appeal: dict = Field(default_factory=dict)` | 121 |
| `backendV1/qnu/domains/rag/answer/service.py` | Khối appeal trong `if cached is None:` sau `assess` lần 1: mọi lượt có `trace.appeal={"attempted": False}`; chỉ khi `draft.status == "insufficient_evidence"` mới reserve usage riêng `answer_id + ":appeal"` (digest có `attempt`, `appeal_version`, catalog/sha/manifest), commit, gọi `chat.complete(appeal_messages(messages), …)`, settle đúng nhánh; parse/materialize/assess phản hồi appeal; **chỉ thay thế** kết quả khi appeal `answered` (lưu `first_tokens`, ghi đè token/contract/coverage/materialization); outcome ∈ {failed, provider_error, invalid, still_insufficient, answered}; `stage_ms["appeal"]`; cache key có `appeal_version` | 406–507 (key: 266) |

Ghi chú: `drafting.py`/`schemas.py` còn diff cũ (prompt v29, `message`) từ các phiên trước — không thuộc P1, không chỉnh thêm. `cells.py`/`context.py`/`table_support.py`/`handlers.py` giữ nguyên mã P0. `fallback.py` (untracked) là việc dở của phiên trước, không thuộc P1.

## Phương pháp đo

- Runner `%TEMP%/qnu_p1_8x3.py` (ngoài Git): 8 câu từng bỏ trắng — Q12, Q19, Q24, Q53, Q74, Q78, Q85, Q88 × 3 lượt = **24 lượt** qua API hội thoại thật (`Idempotency-Key`, hội thoại mới mỗi lượt), lưu đầy đủ `result_trace`; kết quả `%TEMP%/qnu_p1_8x3_results.json`.
- Token đọc **`result_trace.prompt_tokens`** (token model trả lời), cùng nguồn với P0 để so cặp; baseline P0 của đúng 8 câu lấy từ `%TEMP%/qnu_p0_16x3_results.json`.
- Kiểm tra bằng chứng xác định: envelope pack giống hệt nhau ở cả 3 lượt của từng câu (đối chiếu `primary_ids`/`added`/catalog — Q53, Q74, Q85 trùng khít) ⇒ khác biệt câu chữ là sampling của model, không phải retrieval.
- Chấm tay theo văn bản nguồn trong `kb_index_chunks` (run `idx_0a4fbb712a1e`, chỉ đọc): mục "6. Tổ chức tuyển sinh" ord 91–101 (ord 98 = "Xét tuyển theo kế hoạch của Bộ GDĐT: 04/8/2026 – 10/8/2026", nằm trong mục c "Xét tuyển đợt 1"); PHỤ LỤC 1 ord 179–181 (ord 181 là bảng riêng một dòng ở trang 14, `ev_p014_b003`, chứa "Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204"); ord 89–90.

## Kết quả (24 lượt)

| Câu | P0 answered/3 | P1 answered/3 | Appeal kích hoạt | Outcome appeal | Chấm nội dung P1 | Kết luận |
|---|---|---|---|---|---|---|
| Q12 | 1/3 | 2/3 | 0 | — | 2/2 lượt trả lời đúng (PT1 mã 100, PT5 mã 405); lượt 2 thiếu caveat điều kiện năng khiếu của PT5 | **PASS**; lượt 3 502 `answer_response_invalid` |
| Q19 | 2/3 | 3/3 | 1 (lượt 3) | answered | 3/3 đúng | **PASS** |
| Q24 | 1/3 | 0/3 | 0 | — | 0/3 | **FAIL** — lượt 1 `answer_response_invalid`, lượt 2–3 `answer_cell_invalid` (`lookups.0.cell_id: not_in_catalog`); guard đúng, ngoài phạm vi P1 |
| Q53 | 3/3 | 3/3 | 1 (lượt 1) | answered | 1/3 (chỉ lượt 3 đúng 20/5–15/6) | **FAIL** |
| Q74 | 1/3 | 3/3 | 1 (lượt 1) | answered | 0/3 | **FAIL** — hàng quyết định ở ord 181 (trang 14, block `ev_p014_b003`) không được pack; liên kết bảng PHỤ LỤC 1 qua trang bị đứt |
| Q78 | 3/3 | 3/3 | 0 | — | 3/3 nhưng thiếu "chính thức được Bộ VHTT&DL xác nhận đã hoàn thành nhiệm vụ" và điều kiện huy chương; lượt 1 lẫn kiện tướng + thêm điều kiện sức khỏe/chiều cao | **PARTIAL** |
| Q85 | 2/3 | 3/3 | 1 (lượt 2) | answered | 1/3 (lượt 1 đúng 04/8–10/8; lượt 2 gán sai "đợt 2" cho 04/8–10/8) | **FAIL** |
| Q88 | 3/3 | 3/3 | 0 | — | 3/3 đúng | **PASS** |

Tổng: answered 16→20/24; **abstain 6→0**; 502 cứng 2→4, toàn model-output/guard thiết kế (`answer_response_invalid` ×2: Q12#3, Q24#1; `answer_cell_invalid` ×2: Q24#2–3), 0 `answer_evidence_changed`, 0 lỗi provider/hạ tầng. Appeal: 4/4 kích hoạt đều `answered` (Q19#3, Q53#1, Q74#1, Q85#2), 0 `still_insufficient`; **chỉ 1/4 kết quả appeal đúng nội dung** (Q19#3), 3/4 còn lại trả lời tự tin nhưng sai (Q53#1, Q74#1, Q85#2).

## Kết quả cổng

| Cổng | Kết quả | Chi tiết |
|---|---|---|
| Mục tiêu hẹp P1 — hết bỏ trắng vô cớ | **PASS** | 0 lượt `insufficient_evidence` (P0: 6); 4 lượt được gọi lại, 4/4 chuyển sang `answered`; Q24 không còn bỏ trắng nhưng hỏng hợp đồng model |
| G2 — chấm nội dung (≥ 7/8 đúng, 0 số bịa) | **FAIL** | 3/8 đúng trọn (Q12, Q19, Q88); Q78 partial 3/3; Q53 1/3; Q85 1/3; Q74 0/3; Q24 0/3. **0 số bịa**, nhưng có sai gán nhãn/điều kiện (Q85#2 gọi 04/8–10/8 là "đợt 2"; Q78#1 lẫn kiện tướng) |
| G1-style — 502 cứng | **FAIL 4/24** | Toàn model-output/guard thiết kế; không hạ tầng/provider; 0 `answer_evidence_changed` |
| G4 — token | **PASS trong phạm vi** | Token trả lời từng câu trùng khít P0 (cùng bằng chứng): Q12 2866, Q19 4858, Q53 2713, Q74 8066, Q78 7096, Q85 4530, Q88 2634; trung vị 4530→4651. Appeal phát sinh thêm **20.612 token** trên 4/24 lượt (hai lần gọi 42.417 thay vì 21.805; tổng 24 lượt 99.937 thay vì ~79.325 ≈ **+26%** trên nhóm này) |
| Độ trễ | **PASS** | Trung vị 8,0→9,1 s; appeal cộng 2,5–6,1 s ở lượt kích hoạt |
| G5 — mã | **PASS** | Ruff sạch 3 tệp (`drafting.py`, `schemas.py`, `service.py`); import/khởi động API OK |
| G6 — quan sát | **PASS** | Cả 24 lượt có `trace.appeal` (`attempted` false/true + outcome); 4 lượt có token hai lần gọi + `first_tokens` |
| pytest | **NOT RUN** | Theo yêu cầu thường trực — không phải PASS |

## Bài học giữa chừng

- **Appeal không sửa chất lượng bằng chứng**: lượt appeal của Q74 vẫn sai vì hàng quyết định chưa từng nằm trong envelope; envelope không đổi thì gọi lại chỉ đổi cách model suy diễn trên cùng dữ kiện.
- **Appeal có rủi ro trung thực**: 3/4 lượt appeal biến một lần bỏ trắng trung thực thành câu trả lời tự tin nhưng sai. Chỉ dẫn appeal đã cho phép giữ `insufficient_evidence` khi thật sự không có căn cứ; rủi ro đến từ mệnh đề "chỉ cần một phần có căn cứ là bắt buộc answered" khi model chọn nhầm bằng chứng. Muốn dùng tiếp cần siết điều kiện kích hoạt (ví dụ chỉ khi kiểm tra coverage xác nhận dữ kiện bắt buộc đã có trong envelope) hoặc nới mệnh đề bắt buộc trả lời; nếu không, giữ abstain trung thực đúng bất biến 1.
- **Q24 là lỗi hợp đồng model** (`cell_id` không thuộc catalog / response không hợp schema), `materialize` hành xử đúng thiết kế P0.2 — không phải hồi quy P1.
- **Lỗi liên kết bảng nối trang (Q74)**: PHỤ LỤC 1 bị tách thành 3 block (ord 179–180 trang 13, ord 181 trang 14 riêng); context hiện không nối tiếp block bảng qua trang. Finding mới cần duyệt riêng (P1.1/P2), không sửa trong P1.

## Lệnh thật đã chạy

- Ruff: `backendV1/.venv/Scripts/python.exe -m ruff check qnu/domains/rag/answer/drafting.py qnu/domains/rag/answer/schemas.py qnu/domains/rag/answer/service.py` → sạch.
- API: dừng PID :8002 cũ, chạy `backendV1/.venv/Scripts/uvicorn.exe qnu.main:app --app-dir backendV1 --host 127.0.0.1 --port 8002` (nền, PID 27332); `/health` OK.
- Đo: runner 24 lượt; đọc DB chỉ đọc qua `docker exec -i qnu_postgres bash -lc 'psql ...'` cho usage/event và đọc chunk đối chiếu qua `AsyncSessionFactory` (`qnu.platform.database`, `IndexChunk` ordinal/kind/text, run `idx_0a4fbb712a1e`).
- Không in/xu lộ secret, token, nội dung nguồn; file đo trong `%TEMP%`, ngoài Git. Không commit/push/deploy; không reindex/migration.

## File đo (ngoài Git)

- `%TEMP%/qnu_p1_8x3.py` (runner), `%TEMP%/qnu_p1_8x3_results.json` (24 lượt), `%TEMP%/qnu_p0_16x3_results.json` (so sánh P0), `%TEMP%/qnu_questions_100_results.json` (baseline 100 câu).

## Rủi ro còn lại và bước sau

1. **G2 FAIL (3/8) và G3 chưa chạy** — G3 cần duyệt chạy lại 100 câu một lượt.
2. **Q74** — đề xuất P1.1 nối tiếp bảng qua trang/khối ở tầng trả lời (không reindex) — chưa duyệt.
3. **Appeal trung thực** — cân nhắc chỉ kích hoạt khi coverage xác nhận dữ kiện bắt buộc đã có, hoặc nới mệnh đề "bắt buộc answered"; chưa duyệt.
4. **Q24/Q53/Q85/Q78** là chất lượng model/hợp đồng output; P2 quyết định model qua ModelOps nếu được duyệt.
5. P2 (đo 100 câu) **chưa duyệt**.
