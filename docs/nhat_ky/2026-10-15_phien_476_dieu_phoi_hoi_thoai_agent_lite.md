# Phiên 476 — Điều phối hội thoại có kiểm soát (agent-lite) cho chatbot liệt kê

## Mục tiêu

Nâng cấp chatbot theo hướng điều phối hội thoại có kiểm soát, giữ RAG làm nguồn bằng chứng: trả lời đúng ý từng lượt, không biến mọi câu tiếp nối thành truy hồi + liệt kê lại. Đã trình nguyên nhân/phương án và được người dùng duyệt kèm 3 điểm chỉnh (gắn đúng lượt trước + nói rõ kiểm tra lại; tên mờ giữ trạng thái cần đối soát; chỉ gộp khi cùng phạm vi có căn cứ; hỏi làm rõ năm chỉ khi mơ hồ thật). Không framework agent mới/DAG/multi-agent, không migration/config mới, không commit/push.

## Nguyên nhân (truy vết code thật)

1. `RagService.ask` chỉ có 4 mode resolver (independent/followup/recheck/clarify): "sao nhiều thế" bị viết lại thành câu liệt kê độc lập rồi `enumerate_combinations` chạy lại toàn bộ → đúng bảng 124 dòng cũ.
2. Không có verified state server-side (history chỉ là prose) nên mọi lượt đều truy hồi lại từ đầu.
3. Số "nguồn" do model tự suy từ citations; không đâu đếm định danh duy nhất/tài liệu thật/phân hoạch năm.
4. Tên OCR lỗi đi qua như fact chắc chắn (probe thật: "Trí tuệ nhân tao", "Sư phạm Tín học", "Công nghệ kỹ thuật ở tôi"...).

## Thay đổi

- `backend/app/modules/rag/conversation_resolution.py`: contract thêm act ngữ nghĩa `explain/reformat/filter` (chung 1 structured_call, giữ guard số/năm/safety; cấm keyword-list). `filter` chỉ thu hẹp năm tường minh (số mới ngoài năm → clarify; phủ định phạm vi → clarify; đổi subject → followup full RAG). `explain/reformat` đổi năm so với lượt trước → clarify.
- `backend/app/modules/rag/conversation_acts.py` (mới): tải lại records lượt trước một cách định danh từ snapshot hiện tại (không tin client, không storage mới); tái dùng scope năm đã kiểm chứng của listing (model plan + validated_scopes, fallback định danh khi model lỗi); render đúng act bằng template định danh (không gọi model lấy số). Mọi bất định → trả None để rơi về luồng cũ. Định danh 3 trạng thái: chuẩn / mờ (giữ riêng, nêu giới hạn) / hỏng cấu trúc (cách ly có đếm). Chỉ gộp trùng khít (mã,tên); cụm gần-giống exact và biến thể dấu (gộp Unicode, không từ điển tên) giữ riêng + ví dụ giới hạn. Đếm đoạn trích ≠ đếm tài liệu; citations nhóm theo tài liệu thật. Không gộp khác năm/unknown-year; không năm đồng hồ. Mở đầu gắn đúng câu hỏi/phạm vi lượt trước + nói rõ kiểm tra lại.
- `backend/app/modules/rag/service.py`: đấu nối 3 act trong `ask()` (kèm `question_resolution`, latency); handler None → luồng cũ.
- `backend/tests/test_conversation_acts.py` (mới, 22 ca chuỗi hội thoại): 10 nhóm yêu cầu (explain không lặp bảng, recheck giữ nguyên, filter năm chuẩn, rút gọn giữ đủ facts, đổi chủ đề độc lập, phủ định/đổi subject, fallback khi mất state/snapshot lạ, biên tenant/client-giả/injection, trùng/mã mở rộng/unknown/OCR, lỗi DB/model không bịa đáp án) + guard resolver + scope tái dùng/fallback + cụm biến thể dấu + đấu nối ask.
- `backend/scripts/probe_conversation_acts_476.py` (mới): probe chuỗi qua luồng chat thật, guard chỉ cho model nội bộ (đã vá bao phủ mọi đường dựng adapter sau khi phát hiện lọt fallback Cloudflare ở lượt 2; lượt 1–2 ghi log thất bại trung thực, không bịa).

## Kiểm chứng

- Mới: 22 pass. Focus `test_conversation_acts` + `test_enumeration_and_followup`: 43 pass.
- Ruff scoped: sạch. Full suite cuối: **1507 pass / 11 fail / 16 skip** — exact 11 IDs trùng baseline 475, không lỗi mới.
- Probe thật (model nội bộ qwen3.5-9b, guard chặn ngoài, fingerprints unchanged): list 124 → "sao nhiều thế" trả giải thích định danh (124 bản ghi / 62 định danh / 5 tài liệu / 2025:34-2026:20-unknown:70 / 22 nhóm gần-giống + ví dụ dấu, hỏi làm rõ năm vì mơ hồ thật); "chỉ lấy năm 2026" trả đúng 20 dòng 2026, không lẫn 2025; "trình bày gọn lại" gom nhóm theo năm giữ đủ facts. Lượt probe 2 toàn lỗi hạ tầng (primary nội bộ sập thoáng qua + fallback Cloudflare 403) được giữ nguyên log, không retry làm đẹp.
- Chưa chạy 82 câu; không tuyên bố ổn định toàn RAG.

## Giới hạn và bàn giao

- Tên OCR sai ở mức dấu (tao/tạo) chỉ bị gắn cờ khi có cặp gần-giống trong cùng tập; tên sai đơn lẻ không phát hiện được bằng cấu trúc — đã nêu rõ, không âm thầm sửa/xóa, ngoài phạm vi sửa OCR/ingestion phiên này.
- Act filter hiện chỉ thu hẹp năm; đổi ngành/điều kiện/phủ định đi followup RAG đầy đủ hoặc clarify.
- Explain/reformat/filter cho đáp án nhánh evidence-pipeline (không phải enumeration) rơi về luồng cũ.
- Cần BE/worker nhận code mới để có hiệu lực live (uvicorn --reload đang chạy sẽ tự nạp; worker arq cần restart khi deploy).
- Ghi nhận sẵn: cảnh báo `failed_to_record_knowledge_gap` (lỗi encoding console Windows trong evaluation_service, có từ trước, ngoài phạm vi) và guard egress harness từng lọt 1 đường (đã vá, cần review độc lập).
