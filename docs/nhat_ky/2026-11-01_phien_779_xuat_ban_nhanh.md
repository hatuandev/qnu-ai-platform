# Phiên779 — Xuất bản nhanh sau compiler, giữ luồng review mặc định

## Phạm vi được phép

Người dùng yêu cầu xuất bản khi compiler đã xong mà không cần gọi model review, đồng thời giữ quy trình hiện tại. Tiếp tục ba PDF đã biên soạn trong phiên778, xuất bản/lập chỉ mục và hỏi bộ 53 câu với model thật, không retry để đổi kết quả. Không cleanup/init, thay corpus/OCR/compiler, đổi model hoặc prompt giữa cohort.

## Triển khai

- Backend `publication/schemas.py`, `review_gate.py`, `decisions.py`: thêm `review_skip` có xác nhận tường minh, lý do ít nhất 10 ký tự, version/bundle/metadata hash. Chỉ nhận khi approve; cấm đồng thời `review_ack`. Preview/commit và publish kiểm lại xác nhận đúng phiên bản/run. Lưu `mode=skipped` trong receipt và audit; không tạo review/finding giả. Giữ quyền, preview TTL/hash, idempotency, nguồn và trạng thái `draft → approved → published`. Không cần migration.
- Frontend: menu `⋯ → Duyệt nhanh, bỏ qua review`, checkbox và lý do, dialog xem trước/xác nhận; sau đó dùng xuất bản hiện có. Nhãn `Chưa qua review` đọc quyết định đã lưu. Nút duyệt kèm review vẫn giữ.
- Runner: `run admissions-publication --skip-review` yêu cầu `admissions-draft` PASS và compiler hoàn tất, rồi đi qua API approve/publish/index bình thường. Checkpoint lưu `review_mode=skipped`; chat ghi `SKIPPED_BY_USER`. Không giả PASS chặng compiler+review. Thiếu cờ thì gate review không đổi.
- Runner ghi đè `E2E_SKIP_REVIEW` kế thừa từ shell theo đúng cờ CLI, tránh vô tình bỏ review hoặc ghi sai nhãn báo cáo khi chạy luồng mặc định.
- Bổ sung integration API/PostgreSQL và unit kiểm quyền, phiên bản, hash, metadata, compiler binding, đồng thời hai loại ack, không tạo review và idempotency. Test frontend/script giữ cả nhánh mặc định và nhánh bỏ qua review.
- Cập nhật [hướng dẫn test](../quy_trinh/V1_TEST_TB_DIEM_SAN_26.md).

## Kiểm chứng đã thực chạy

| Kiểm tra | Kết quả |
|---|---|
| API/PostgreSQL cô lập: `test_fast_publication_779.py`, review gate666, publication646 | 33 PASS; DB test riêng được dọn sau kiểm tra, không sửa DB phiên live |
| Unit mới `tests/unit/test_fast_publication_779.py` | 6 PASS |
| Backend unit toàn bộ `pytest tests/unit -q --basetemp=../tmp/pytest779-aftermetadata` | **593 PASS / 1 FAIL**; đúng lỗi đã ghi ở772: `test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge` (`invalid_identity`) |
| Frontend `admissions-pipeline-777.test.ts`, `v1-publication.test.ts` | 38 PASS |
| Script `scripts/test_v1_e2e_draft_778.py` | 4 PASS, bao gồm biến môi trường kế thừa không vượt lựa chọn CLI |
| Frontend toàn bộ Vitest | **567 PASS / 33 FAIL**; đối chiếu exact failed test IDs trùng cả33 của778, không có lỗi mới |
| Build, E2E TypeScript, scoped Biome/Ruff | PASS |
| UI Playwright đọc trang và mở dialog | Nhìn thấy menu/checkbox desktop và mobile; trang đã phát hành hiển thị nhãn chưa review; không commit bằng probe UI |
| Live `admissions-publication --headed --skip-review` | PASS: 3 PDF/28 trang, index active 179 đoạn, 30 giây tổng chặng |
| Live `admissions-chat --headed` | **FAIL** sau 5.8 phút: 12 PASS lần đầu, 2 FAIL (F13/F14), 39 NOT_RUN; 14 dispatch, không retry |

Full suite còn lỗi nên vẫn FAIL; không coi các kiểm tra liên quan PASS là toàn repo PASS. Lần pytest đầu gặp lỗi thư mục tạm hệ thống; lần có basetemp riêng ở trên chạy đủ. Các fixture API dùng model giả để kiểm hợp đồng, không dùng kết quả đó chứng minh RAG/model thật.

## Vận hành và bằng chứng

Phiên `93faa11f0caf` được giữ. Dừng supervisor serve cũ sau khi xác minh không có chặng đang chạy; bật supervisor ẩn PID28384 để nạp backend mới. Docker và dữ liệu cũ giữ nguyên; không gọi lại compiler/OCR, không thay key/quota/reasoning policy. Reasoning off task compiler từ778 vẫn giữ; không áp sang answer/review.

- Publication: `tmp/v1-e2e/93faa11f0caf/runs/admissions-publication-1793507729267743800`.
- Chat: `tmp/v1-e2e/93faa11f0caf/runs/admissions-chat-1793507789510629500/admissions-answers.json`.
- Log kiểm chứng trong `tmp/verification779-*`; ảnh UI trong `tmp/fast-publication-779-*.png`. Các artifact này nằm ngoài Git; không chép prompt/corpus/bí mật vào memory.

Bỏ qua review là quyết định của người có quyền, không là chứng nhận nội dung đúng. Nhãn benchmark vẫn draft và kiểm ngữ nghĩa độc lập NOT_RUN. Kết quả hỏi đáp cần đánh giá riêng, không suy từ publication PASS.

## Hai lỗi hỏi đáp, giữ kết quả đầu

- F13: backend trả answered với hai statement, cùng trỏ E1 có citation trang7/8. Bộ chấm `admissions-evaluation.ts` yêu cầu trong **một** statement đồng thời có số15, chủ thể THPT và từ chỉ ngoại lệ; model tách ngưỡng chung và ngoại lệ thành hai statement. Hai điều kiện text của fact đều có trong chunk nguồn, nhưng không có statement vượt bộ lọc candidates. Đây là giới hạn hợp đồng chấm cần rà riêng, chưa phải bằng chứng compiler làm mất nguồn. Không sửa gold/assertion hoặc chuyển FAIL thành PASS trong lượt này; chưa kiểm ngữ nghĩa độc lập.
- F14: upstream chat HTTP200, gateway log server_default, sau đó turn failed `answer_response_invalid`/HTTP502. Backend dùng mã này khi cấu trúc trả lời không đạt schema hoặc sau projection có quá20statement; chưa có raw response để phân biệt chính xác nhánh. Không đủ căn cứ gọi đây là lỗi hết token. Runner chủ động dừng sau lỗi502, để F15 trở đi NOT_RUN; không gửi lại F14 và không sửa model/prompt giữa cohort.

Chức năng xuất bản nhanh đã chạy thành công; bộ hỏi đáp53 vẫn FAIL, cần xử lý đánh giá F13 và hợp đồng model F14 trước một lượt nghiệm thu tiếp theo có chủ đích. Serve hiện tại còn chạy và giữ tất cả lịch sử/báo cáo.
