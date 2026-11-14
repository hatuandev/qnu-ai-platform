# Phiên 963 — 2026-11-14 — Clear dev, nạp PDF tuyển sinh, tạo trợ lý và chạy kịch bản 12 câu

## Yêu cầu

- Người dùng gửi kèm `docs/tai_lieu/tuyen_sinh/Thông tin TSĐH cập nhật.pdf` và yêu cầu: clear lại môi trường dev, upload PDF vào kho tri thức, tạo và cấu hình trợ lý, rồi lên kịch bản câu hỏi để test thực tế quy trình chạy của app QNU.
- Ràng buộc giữ nguyên: bất kỳ câu hỏi nào cũng do model chat trả lời (không hardcode); thiếu dữ liệu thì trả lời thông minh, trung thực thay vì câu "thiếu bằng chứng" cứng; không chạy pytest khi chưa được yêu cầu; không commit/push; không đụng thay đổi chưa commit của người dùng.

## Clear và dựng lại môi trường

- Sao lưu dữ liệu dev cũ ra `%TEMP%/qnu_dev_backup_962.dump` (ngoài Git) trước khi xóa.
- Xóa dữ liệu Postgres/Redis/Qdrant/MinIO của stack dev; migrate lại **0001 → 0028** (DB mới ở head `0028`, gồm cả 0027/0028 nên không còn phải áp lên DB cũ), seed ModelOps và seed đơn vị shl; không in nội dung tệp tài khoản dev.
- Chạy stack nền `python scripts/run_v1.py dev2`: API :8002, worker V1, FE V2 :3002.

## Nạp PDF và chạy pipeline

- Nguồn `src_aa676aa1f11c` / `rev_c4087b212745`, PDF **14 trang** có text layer, kho `col_9209e90d1a53`.
- OCR `ocr_9f18675ed811`; soát chính tả tự động `spl_aaaa978f357a` **0 gợi ý / 0 withheld** → duyệt zero-change, giữ text version 0 (`text_sha256 9fd7bce8…e24ce`).
- Chuẩn bị `cmp_9e4467418258` → `cdoc_c344954f2405` / `cver_947dc22b3863` (bundle `296cbf04…3ed9`); duyệt `pdec_3a1ff21572b6`, xuất bản `pdec_e90bbf114bee` lúc **16:02:15**.
- Index tự động `idx_0a4fbb712a1e` generation 1, **182 chunk**, manifest `13a71e52…56fee`, readiness `ready`, search 5 hit đúng bản đã xuất bản. Từ upload đến xuất bản khoảng **108 giây** (`16:00:27 → 16:02:15`).

## Trợ lý và cấu hình

- `ast_47f30aaf2665` — "Trợ lý Tuyển sinh 2026", kho `col_9209e90d1a53`, `top_k=5`, `history_turns=3`, `is_active=true`, revision **3**.
- `chat_provider_id=null`, `rerank_provider_id=null` → model chat/rerank do **ModelOps tự chọn theo mặc định hệ thống** (đúng bất biến 5), không ghim model.
- `rag_policy`: `hybrid_rerank`, `candidate_k=40`, `rrf_k=60`, `scope_resolution=explicit`, `context_window=1`, `context_max_bytes=32000`, `verification_mode=off`.
- Hai thay đổi cấu hình có lý do đo được:
  1. `scope_resolution` catalog → **explicit**: planner catalog làm hỏng câu Q2/Q3/Q5 (nhãn thuộc tính chung "Số" khớp nhầm "số lượng"/"số điện thoại"; năm 2026 không có trong metadata chunk).
  2. `candidate_k` 30 → **40**: chunk bảng VSTEP (`ich_b27d88352d33`) không lọt top-30 nhưng đứng **hạng 1** ở 40/60 với top_k=5, nên câu quy đổi VSTEP bị hụt recall ở 30.

## Kịch bản 12 câu và kết quả

Chạy qua API hội thoại thật (`POST /conversations`, gửi lượt kèm `Idempotency-Key`), model `qwen3.8-27b-q4` qua mặc định hệ thống:

| # | Câu hỏi | Kết quả | Đối chiếu PDF |
|---|---|---|---|
| 1 | Xin chào | `direct_reply` greeting | Đúng vai trợ lý tuyển sinh |
| 2 | Mã cơ sở đào tạo + số điện thoại | `DQN`, `1800.55.88.49` | Đúng |
| 3 | Tổng số lượng tuyển sinh 2026 | `5.173` | Đúng |
| 4 | Các phương thức xét tuyển + mã | 100, 200, 402A, 402B, 405; xét tuyển thẳng 301 | Đúng |
| 5 | Ngôn ngữ Anh: chỉ tiêu + tổ hợp | 261; (Toán, Văn, Anh), (Văn, Sử, Anh), (Văn, Địa, Anh), (Toán, Lý, Anh) | Đúng (lặp lại 2 lần, chỉ mỹ quan) |
| 6 | Hạn đăng ký đợt 1 (Bộ GDĐT) | 02/7/2026 → 14/7/2026 | Đúng |
| 7 | Học phí toàn khóa | 83–97 triệu (4 năm); 112,3 triệu (4,5 năm) | Đúng |
| 8 | IELTS 6.5 quy đổi | 9.5 | Đúng |
| 9 | "Còn VSTEP 6.0 thì sao?" (follow-up) | `resolved_question` giữ mạch; VSTEP 6.0 → 9.0 | Đúng, memory v4 hoạt động |
| 10 | Điểm chuẩn Sư phạm Toán 2025 | 25.85 | Đúng |
| 11 | Điều kiện thể chất Giáo dục Thể chất | 1,65 m/45 kg nam; 1,55 m/40 kg nữ; không dị tật | Đúng |
| 12 | Học phí ngành Y đa khoa 2026 | Khung chung 83–97 triệu + nói rõ "tài liệu không nêu riêng ngành Y đa khoa" | Trung thực, không bịa |

- **12/12 lượt HTTP 200 `completed`**, 0 clarify, 0 failed/uncertain; câu 12 là ví dụ đúng tinh thần "trả lời thông minh khi thiếu dữ liệu": trả phần có căn cứ và nói rõ phần thiếu.
- Kết quả lưu ở `%TEMP%/qnu_scenario_962_results.json` (bản catalog và explicit-30 lưu riêng để so sánh), script `%TEMP%/qnu_scenario_962.py` — đều ngoài Git.

## Lỗi/lỗi tìm thấy ở chế độ catalog (chưa sửa mã)

1. `query_scope.attribute_scope` khớp nhãn thuộc tính chung như "Số" vào từ thường ("số lượng", "số điện thoại") → 409 clarify sai.
2. `year_choices` nhận năm 2026 trong câu nhưng catalog không có chunk gắn 2026 (bảng hai năm chỉ gắn 2024/2025) → facet `no_match`.
3. Guard đa facet trong `answer/retrieval.py` so trace `manifest_sha256`/`rerank_provider`; facet `no_match` không có hai khóa này nên bị coi là "cấu hình đổi giữa các ý hỏi" → 409 `answer_evidence_changed`.
4. Recall: `candidate_k=30` mặc định hụt chunk bảng VSTEP dù rerank xếp hạng 1 ở 40.

Cả 4 điểm đã được xử lý bằng **cấu hình trợ lý** (explicit + candidate_k 40), không sửa code. Sửa gốc cần người dùng duyệt riêng vì ảnh hưởng hành vi benchmark catalog.

## Kiểm chứng và giới hạn

- pytest: **NOT RUN** (người dùng yêu cầu không chạy) — `NOT RUN ≠ PASS`.
- Không sửa mã nguồn nên không chạy Ruff/Biome/tsc; không migration viết tay, không re-index ngoài index tự động của nguồn mới; không commit/push.
- Kịch bản là 12 lượt thật một lần, không phải benchmark; nhãn đối chiếu do người viết kịch bản so với PDF gốc.
- Stack dev đang chạy nền (API :8002, FE :3002) để người dùng test tiếp trên UI.
