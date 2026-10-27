# Phiên 627 — Chạy lại và sửa chiều quan hệ 121–123

User yêu cầu chạy lại 121–123 một lần, nếu vẫn đảo thì tìm nguyên nhân và sửa. Giữ cx/gpt-6-luna, nguồn, Quality Gate; không toàn tài liệu hoặc publication/Git.

Lượt đầu: ba response/19,718 giây/0 fallback, không đảo nhưng bỏ hẳn quan hệ. Không coi omission là PASS. Tìm thấy engine guide bị thay bằng grounded prompt thiếu vai trò directed endpoints. Sửa grounded prompt dùng chung DIRECTION_RULES, giữ explicit link khi đủ căn cứ và tất cả guard. Không sửa endpoint bằng thuật toán swap.

Lượt sau sửa: ba response/20,484 giây/0 fallback; 121 tạo đúng 5.173 → 4.500, 122 supported, 123 blind witness cùng chiều. Nhóm ba bước vẫn FAIL do guard bắt mã 1906/TB-ĐHQN trong heading như năm 1906; không sửa lỗi ngoài phạm vi hoặc báo toàn compiler đạt.

File thay đổi: phần prompt trong `compilation_grounding.py`, test mới `test_compilation_direction_prompt_627.py`, báo cáo/memory/procedure. Baseline app trước sửa lưu để đối chiếu diff, giữ toàn bộ dirty changes có trước.

Baseline cuối 8 FAIL → 8 PASS sau sửa; focused 129 PASS/Ruff hai file PASS. Fixture trung gian đã sửa đúng contract heading/unit; log lỗi giữ riêng. Full cuối: **3.800 PASS, 18 FAIL, 17 SKIP**, exit 1; exact failure IDs và nguyên nhân khớp Context625, không regression mới, không mất test. Báo cáo before/after từng ID ở `backend/storage/context627/test-id-comparison.json`. Full suite vẫn FAIL.

Lệnh thực từ repo root:

```text
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context627_retry_synthesis.py --execute
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context627_postfix_synthesis.py --execute
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context627_checks.py setup --scope checks
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context627_checks.py run --scope checks --label baseline-final --baseline tests/test_compilation_direction_prompt_627.py
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context627_checks.py run --scope checks --label focused-final tests/test_compilation_direction_prompt_627.py tests/test_compilation_grounding_616.py tests/test_compilation_semantics_604.py tests/test_compilation_modelops_603.py
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context627_checks.py setup --scope final
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context627_checks.py seed-defaults --scope final
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context627_checks.py run --scope final --label full-final
backend/.venv/Scripts/python.exe -m ruff check backend/app/modules/knowledge/services/compilation_grounding.py backend/tests/test_compilation_direction_prompt_627.py
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context627_compare.py
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context627_checks.py cleanup --scope checks
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context627_checks.py cleanup --scope final
```

Baseline exit 1 đúng missing instruction; focused/Ruff và hai script model exit 0. Exit 0 của script model xác nhận chạy/lưu thành công, không đổi kết quả kiểm chứng tổng hợp FAIL_REVIEW. Không gọi full compiler/64, không ModelOps defaults/source/index writes. Hai database regression riêng đã dọn sau khi xác minh nonce; Storage giữ theo chính sách bảo vệ. Acceptance DB cũ và checkpoint Context623–626 giữ để đối soát, không bypass xóa.

[Báo cáo đầy đủ](../bao_cao/context627/REVIEW.md).

**2026-10-24 — Người dùng nghiệm thu chức năng Compiler.** Xác nhận trong hội thoại: “ok vậy là được tôi nghiệm thu chức năng Compiler nhé ko cần chạy làm lại nữa”. Kết thúc phạm vi công việc này; không chạy lại compiler, gọi model hoặc chạy test. Giữ nguyên kết quả kiểm chứng và các hạn chế đã ghi; không đổi machine_complete, quyết định semantic hay publication trong dữ liệu ứng dụng.
