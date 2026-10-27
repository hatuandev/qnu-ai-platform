# Context627 — Chạy lại 121–123 và sửa hướng dẫn chiều quan hệ

Ngày bắt đầu 2026-10-24. **Chiều quan hệ sau sửa đã được kiểm chứng đúng: 5.173 thay thế 4.500. Kết quả tự động của nhóm ba bước vẫn FAIL vì lỗi guard tiêu đề khác; người dùng đã nghiệm thu chức năng theo xác nhận bàn giao dưới đây.**

## Xác nhận bàn giao

**2026-10-24 — Người dùng nghiệm thu chức năng Compiler.** Xác nhận trong hội thoại: “ok vậy là được tôi nghiệm thu chức năng Compiler nhé ko cần chạy làm lại nữa”. Kết thúc phạm vi công việc này; không chạy lại compiler, gọi model hoặc chạy test. Giữ nguyên kết quả kiểm chứng và các hạn chế đã ghi; không đổi machine_complete, quyết định semantic hay publication trong dữ liệu ứng dụng.

## Lượt thử lại theo yêu cầu

Chạy đúng một lượt tuần tự 121–123 bằng `cx/gpt-6-luna`, medium, timeout 30 giây, capacity động. Bước 121 giữ nguyên input đã lưu. Bước 122 và 123 dựng input từ output 121 mới, không kiểm lại candidate cũ.

- Ba response hoàn tất trong 19,718 giây, đều stop, không fallback.
- Lần này không tạo chiều đảo, nhưng trả `relations=[]`, làm mất quan hệ nguồn đã nêu rõ. Kiểm tra endpoint pair riêng đánh dấu FAIL_REVIEW; không coi danh sách rỗng là đã chứng minh đúng chiều.
- Hai section được đánh giá supported. Review chiều rỗng không cung cấp bằng chứng về quan hệ bị bỏ.
- Không sửa hoặc duyệt bundle/job Context626.

## Nguyên nhân và thay đổi

`compilation_engine.SYNTHESIZE` đã có quy ước directed edge. Tuy nhiên `compilation_transport.wire_instruction()` dùng prompt riêng `compilation_grounding.SYNTHESIZE` cho nhánh source-grounded, thay instruction từ engine. Prompt thực này thiếu định nghĩa vai trò source_id/target_id cho từng loại quan hệ.

Server materializer sao chép quan hệ, transport restore ánh xạ ID; không có bước chủ động đảo source/target. Regression đi qua generator và request thực tới ModelOps giả lập kiểm chứng điều này với cả hai thứ tự assertion. Bằng chứng xác nhận thiếu hướng dẫn ở ranh giới gửi model; không kết luận đây là nguyên nhân duy nhất của mọi sai lệch model.

Sửa duy nhất phần prompt trong `compilation_grounding.py`: dùng chung `DIRECTION_RULES` với blind verifier, nêu rõ SUBJECT(source_id) → OBJECT(target_id), không suy từ thứ tự ID, thứ tự assertion hoặc độ lớn số. Giữ liên kết tác giả nêu rõ khi cả hai endpoint được cung cấp và có căn cứ; không bỏ liên kết chỉ để tránh chọn chiều. Quy tắc không suy thay thế từ ngày muộn hơn, scope, điều kiện, nguồn và các kiểm chứng độc lập giữ nguyên.

Không hardcode 5.173, 4.500, mã thông báo hoặc câu hỏi vào mã ứng dụng. Không tự swap endpoint, tạo verdict supported hoặc bỏ guard. Nội dung prompt này đã tham gia configuration hash hiện có; checkpoint cũ không được âm thầm coi là tương thích.

## Kiểm chứng sau sửa

Chạy lại đúng nhóm 121–123 một lượt để kiểm bản sửa, không chạy lại toàn tài liệu:

| Bước | Kết quả |
|---|---|
| 121 — SynthesisDraft | Có quan hệ supersedes: source=5.173, target=4.500; giữ đúng cặp endpoint |
| 122 — SynthesisCheck | Quan hệ supported; cả ba section được model đánh giá supported |
| 123 — RelationDirections | Blind witness supported cùng chiều 5.173 → 4.500; không direction issue |
| Kiểm tra tổng hợp server | Vẫn FAIL: heading_year_outside_assertion_scope tại section 0 |

Ba response sau sửa hoàn tất trong 20,484 giây, đều stop, không fallback. Tổng hai lượt có 6 response. Không có tự gửi lại request uncertain hoặc thử nhiều lần cho đến khi xanh.

Lỗi tiêu đề còn lại: heading là nguyên văn nguồn, gồm năm 2026 và mã `1906/TB-ĐHQN`. `section_guards` dùng regex YEAR bắt cả 1906 như năm lịch, trong khi temporal scope của assertion là 2026. Mã thông báo không chứng minh năm 1906. Chưa sửa lỗi lexer/guard này trong phạm vi chiều quan hệ, không xóa heading hoặc hạ Quality Gate để đổi kết quả thành PASS.

## Regression và giới hạn

- Thêm 8 test qua generator → request ModelOps → parse/restore/materialize, phủ supports, supersedes, prerequisite, exception và cả hai thứ tự assertion.
- Baseline cuối cùng trên snapshot trước sửa: **8 FAIL**, đúng lỗi thiếu hướng dẫn trong system message, exit 1.
- Sau sửa: **8 PASS**; focused cùng grounding/semantics/ModelOps: **129 PASS**, exit 0. Ruff đúng hai file: PASS, exit 0.
- Hai vòng fixture đầu thiếu heading thuộc proof được trích và unit mặc định; đã sửa fixture theo contract, không sửa app để che lỗi. Kết quả cuối được lưu riêng, không ghi đè log các vòng trước.
- Full cuối: **3.800 PASS, 18 FAIL, 17 SKIP**, exit 1; exact failure IDs và nguyên nhân khớp Context625, không regression mới, không mất test. Báo cáo before/after từng ID ở `backend/storage/context627/test-id-comparison.json`. Full suite vẫn FAIL.
- Whole compiler, benchmark 64, frontend, indexing/publication: NOT RUN. Kết quả 121–123 này không thay cho nghiệm thu toàn compiler Context626 đang needs_attention.

## An toàn và bằng chứng

Kiểm tra DB, MinIO, Qdrant local và nonce DB test trước chạy. Test regression dùng DB riêng, LocalStorage tạm, endpoints chặn egress; không migrations trên DB ứng dụng. Model thật đi qua ModelOps hiện có, không đổi model mặc định hoặc credential.

Nguồn ba DOCX/381 proof, hash snapshot, old job/checkpoint, defaults/provider/index và shared domain seals khớp trước/sau hai lượt model. Các artifact qua StorageDriver và đọc lại chính xác. Không reindex, publish, restart, commit/push hoặc tự phê duyệt candidate.

Hai database regression riêng đã dọn sau khi xác minh nonce; Storage giữ theo chính sách bảo vệ. Acceptance DB cũ và checkpoint Context623–626 giữ để đối soát, không bypass xóa.

Bằng chứng cục bộ ở `backend/storage/context627/`: `retry/{result,metrics,postcheck}.json`, `postfix/{result,metrics,postcheck}.json`, `implementation.diff`, `checks/{baseline-final,regression-final,focused-final}.{xml,log}`, `final/full-final.*` và báo cáo so sánh theo test ID. Corpus/request/output chi tiết giữ trong Storage kiểm thử; không đưa vào Git.
