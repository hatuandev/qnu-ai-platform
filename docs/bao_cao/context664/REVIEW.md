# Sửa hai lỗi hủy lượt chat — backendV1

**PASS** cho hai lỗi API cập nhật đã tái hiện trong review Context663.

- Tắt trợ lý qua PUT hủy bền vững các lượt đang chạy của mọi hội thoại thuộc đúng
  trợ lý, kể cả khác owner. Chỉ admin được cập nhật trợ lý.
- Archive hội thoại qua PUT chỉ hủy lượt của hội thoại do người gọi sở hữu.
- Dùng chung `cancel_related_jobs` với lifecycle; workspace lock và turn lock
  giữ thứ tự cập nhật. Trạng thái, hủy và audit `cancelled_turns` commit cùng
  transaction. Audit lỗi thì rollback cả trạng thái và hủy.
- Bật/mở lại không hồi sinh lượt đã hủy. Phản hồi muộn không lưu result; replay
  key cũ báo cancelled; key/sequence mới gửi được. Không đổi revision chỉ vì tắt/
  bật; giữ lịch sử completed. Cập nhật active/đổi tên không hủy lượt.

Không thay request/response contract, schema, migration, frontend hoặc ModelOps.
HTTP đã gửi tới server AI có thể vẫn tính toán; usage đã quan sát vẫn ghi nhận.

## Bằng chứng thực chạy

Regression trước sửa: **2 FAIL** đúng HTTP200/completed/có result, 8 deselected.
Sau sửa: focused **50 PASS / 0 FAIL / 0 SKIP**, gồm 10 ca mới; kiểm
phản hồi muộn, replay và lượt mới, phạm vi, quyền, giữ history, active update và
rollback. Full **575 PASS / 0 FAIL / 0 SKIP**, 10 mới/0 mất so 565.
Chỉ siết kiểm tra usage của answer riêng; không đổi assertion từ cancelled thành
completed hoặc bỏ negative cases để đạt PASS.

Ruff/format 4 file, UTF-8 không BOM/LF đạt. 96 path/123 operation OpenAPI giữ.
475 file backend cũ và 12 file migration/config/archive giữ nguyên hash; head
vẫn `0001_initial_schema`. Sáu DB thử đã dọn và sentinel/version legacy giữ;
0 collection vector v1 quan sát sau cleanup.

Cwd `backendV1`, Python `.venv/Scripts/python.exe`.

```text
-X utf8 storage/context661/run_tests.py tests/integration/test_chat_stop_updates_664.py -k stop_and_resume -q
-X utf8 storage/context661/run_tests.py tests/integration/test_chat_stop_updates_664.py tests/integration/test_lifecycle_659.py tests/integration/test_lifecycle_runtime_659.py tests/integration/test_conversations_649.py -q
-X utf8 storage/context664/full_gate.py
-m ruff check qnu/domains/assistants/service.py qnu/domains/conversations/service.py qnu/domains/lifecycle/effects.py tests/integration/test_chat_stop_updates_664.py
-m ruff format --check qnu/domains/assistants/service.py qnu/domains/conversations/service.py qnu/domains/lifecycle/effects.py tests/integration/test_chat_stop_updates_664.py
```

Harness sở hữu DB test riêng và chặn egress ngoài loopback; hạ tầng cục bộ thật,
model HTTP tổng hợp. Full gate chia 65 file thành bốn nhóm không trùng, DB riêng.
Không chạy AI thật hoặc quality benchmark; chưa migration, restart/deploy hay
thay dữ liệu phục vụ. Không làm purge/GC/DR hoặc publish gate trong batch sửa này.

[Regression](../../../backendV1/tests/integration/test_chat_stop_updates_664.py) ·
[Receipt](verification.json) · [Lỗi trước sửa](../context663/REVIEW.md) ·
[Hợp đồng](../../../backendV1/docs/resource-lifecycle.md).
