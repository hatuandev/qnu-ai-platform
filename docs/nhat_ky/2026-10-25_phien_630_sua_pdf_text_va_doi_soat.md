# Phiên630 — Sửa PDF text và đối soát

Người dùng giao ưu tiên sửa PDF có lớp văn bản, đồng thời hỏi Qwen3.8-27B so với GPT-OSS120B và thông báo đang cài Nemotron Parse. Áp dụng qnu-knowledge-ingestion, clean-code, ModelOps và tài liệu chính thức cho phần so sánh; giữ toàn bộ dirty changes có sẵn. Không đổi model hoặc thực hiện cài đặt/serving Nemotron.

Sửa header nền trắng bằng bằng chứng typography và ô; ràng buộc độ sâu để giữ dòng body in đậm. Chuyển native projection trùng vào provenance chỉ khi khớp nguyên ô/geometry duy nhất. Thêm kế thừa header khi bảng sang trang không lặp header với chứng cứ lưới/scope/ordinal, giữ từng ô và lineage. Header OCR đọc thêm block có tọa độ hợp lệ, chặn mâu thuẫn và vẫn proposed. PDF cache v6 riêng, v5 integrity dùng policy cũ; DOCX không đổi parser/cache. Phạm vi 7 app files, 1 test mới + 1 test mở rộng; không sửa Quality Gate hoặc schema.

Baseline mới8FAIL/12PASS. Mở rộng safety bắt được first-body-bold và nối bảng không header, đã sửa; log/IDs giữ. Focused cuối219PASS+23subtests, Ruff9PASS. **Full cuối3833PASS/18FAIL nền/17SKIP, exit1,804,06s**; exact18failure IDs/cause khớp627,33testmớiPASS, không thiếu ID/regression. Full chưa hoàn tất trước đó đã dừng vì batch còn cờ dư; không dùng để nghiệm thu. Hash app ổn định suốt full cuối.

Offline4PDF/33trang giữ grid/hash/MD-JSON: quyđổi760→0limitations, đúng23cột/header2, nối4–5; họcphí570→0, đủ56rows/560fields, lineage2trangkhôngheader. Báocáo2024còn184(từ339), môphỏng18tranggiữ51/cachedOCR. TấtcảvẫncònNEEDS_ATTENTION vì hình/vai tròchưarõ; không épAUTO_READY. Đọc cặp v5 thật và4companionmớiPASS. Replay OCR629bổsungđúngsố/ngàyvàsourceblock,không inference mới/khôngtựduyệt.

Model assessment có nguồn chính thức: Qwen dense27B/vision/262K, GPT-OSS MoE117B/5,1Bactive/128K; chưa A/BQNU nên không kết luận hơn. Nemotron phù hợp adapter extraction; chưa tích hợp hoặc đổi endpoint/model.

DB/MinIO/Qdrant loopback được xác minh; DBnonce73d32960b6a8 đã dọn, Storage giữ policy/evidence. Shared collection/source/index/assistant/provider seals khớp; ngoài7appfiles không đổi. Không migration appDB, cloudcalls, LLM/Compilerlive/benchmark64/index/pub/restart/commit/push. Full suite vẫnFAIL18, không ghép điểm RAG cũ thành kết quả hiện tại.

[Báo cáo](../bao_cao/context630/REVIEW.md), [so sánh model](../bao_cao/context630/MODEL_ASSESSMENT.md). Evidence ignored backend/storage/context630; replay-release là bản cuối, các lượt trung gian vẫn giữ.
