# Phiên 764 — Sửa projection bảng, báo cáo replay và prompt v4

Ngày 2026-10-31. Người dùng yêu cầu sửa ba lỗi ở review763, cập nhật PROMPT_VERSION và test lại. Giữ các thay đổi chưa commit của người dùng, gồm sắp evidence theo citation và quota E2E10M. Không sửa nguồn OCR, biên soạn lại, xuất bản, reindex, đổi cấu hình model hoặc restart phiên đang phục vụ.

## Thay đổi

- Thêm `answer/projection.py`: giữ nguyên text của bảng chưa parsed/legacy/custom. Với bảng có cấu trúc đầy đủ, chỉ bỏ đúng suffix JSON do chunker sinh khi khớp hoàn toàn structure; không tìm dấu ngoặc rồi cắt tùy ý.
- Giữ đầy đủ rows, row_span, col_span, header, row_indices, số cột/hàng, source_table_citation, context và chú thích. Bản nguồn/SearchHit không bị sửa.
- `context.evidence_size` và `drafting.messages_for` dùng cùng projection. Đo trên46chunk của index hiện có: biểu diễn đầy đủ163665byte xuống91558byte, giảm44.1%; đây là byte JSON, không phải token tokenizer.
- Prompt lên `qnu.rag.answer/v4`. Không coi cùng số cột/ô đầu trống/trang liền nhau là chứng minh nối bảng; thiếu quan hệ rõ phải abstain.
- `admissions-chat.ts`: phân biệt fresh/replayed/resumed; đọc trạng thái server khi thiếu turnID, không nuốt lỗi GET rồi gửi mới. failed/uncertain/cancelled giữ lịch sử và dừng; running tiếp tục chờ. Không retry theo đáp án.
- Replay/resume không tính first_attempt_pass, inference_ms=null; lượt fresh lấy generation latency từ server thay vì lấy thời gian GET. Lịch sử thất bại đã biết không được tính lại là lần đầu. Report thêm origin, client_elapsed_ms, prompt_versions/configuration_hashes và các bộ đếm fresh/replayed/resumed.

## Regression trước và sau sửa

- Backend4test mới tái hiện RED: mất text rawtable; mất spans/identity; cắt nhầm JSON trong text; version cũ. Sau sửa4PASS.
- Frontend test đầu tiên RED (sau khi chỉ export helper để gọi được): replay không có origin. Sau sửa8test PASS: replay, thiếu localID, fresh abstain không retry,3terminal statuses, running resume và lỗi GET không phát sinh POST.
- Thêm1API test thật xác nhận payload giữ cấu trúc bảng đã published và trace promptv4, citation vẫn server-bound.

## Kiểm chứng thực chạy

| Kiểm tra | Kết quả |
|---|---|
| Pytest focused projection764 |4PASS,exit0|
| Full backendV1 unit |532PASS/1FAIL,exit1,53.34s|
| API integration test_answers_api648, DB cô lập |21PASS,exit0,201.42s|
| Vitest replay764/capacity735/provider-selection |22PASS,exit0|
| Frontend build (Vite+TypeScript) |PASS,exit0; còn cảnh báo Vite có sẵn|
| E2E TypeScript |PASS,exit0|
| Scoped Ruff/Biome |PASS,exit0|
| Git diff check và UTF-8 no BOM/LF |PASS|

Lỗi nền unit còn đúng ID `tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`, `invalid_identity` tại workspaces/access.py39; tổng full unit vẫn FAIL. Không sửa lỗi ngoài phạm vi. Integration dùng database `qnu_v1_test_5adc5e0bd266497d`; receipt xác nhận đã drop và giữ legacy sentinel. Không chạy lại nhóm metadata672 đang lỗi fixture trong763.

## Live API,19 câu mới cùng cấu hình

- Chạy mã hiện tại qua ASGI API/middleware/auth thật, storage/Qdrant/ModelOps/provider thật trên workspace E2E đã cho phép. Không restart server của người dùng và không dùng checkpoint câu trả lời cũ. Đây là API smoke evaluation, không phải một lượt Playwright CLI mới.
- Index giữ `idx_876119b2d82a`, version `cver_acecc644ec20`;19hội thoại/answerID mới, mỗi câu gửi một lần, không retry theo gold. Cùng assistant revision, một chat configuration hash, promptv4 vàtop_k20/candidate_k50.
- Kết quả **18PASS/1FAIL/0NOT_RUN**, tổng thời gian các câu275.35s. F15=`model_abstained`; input18526/completion12, không phải hết output. Chunk điều kiện riêng đã có trong rerank top4; chưa đủ căn cứ quy nguyên nhân từ chối cho lỗi projection hay token. Không chỉnh assertion/prompt để ép PASS và không hỏi lại câu đó.
- F12 và cả3câu negative F17–F19 đạt. Nhãn benchmark vẫn draft, semantic_reviewNOT_RUN; không khẳng định mọi phát biểu được duyệt độc lập.
- Report: `tmp/review764-fc9ef1a797b1/admissions-answers.json`. Bộ API21PASS và unit regression không thay thế kết quả live18/19.

## Bàn giao

Ba lỗi và promptversion đã sửa, regression đạt. Chất lượng trả lời F15 còn cần phân tích riêng; chưa nghiệm thu toàn bộ admissions-chat. Không cần upload/OCR/compiler/publish lại vì các thay đổi này. Cửa sổ serve của người dùng chưa nạp mã mới; khi chạy CLI thông thường cần dừng/mở lại serve để nạp mã. Những câu từ checkpoint sẽ được đánh replay thay vì lần đầu; không xóa lịch sử để làm xanh report.
