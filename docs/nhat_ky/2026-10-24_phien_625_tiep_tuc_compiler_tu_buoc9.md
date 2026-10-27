# Phiên 625 — Tiếp tục compiler từ bước 9

Ngày 2026-10-24. Người dùng cho tiếp tục từ bước 9 sau retry riêng bước 8 đã đạt. Giữ model, ba nguồn và Quality Gate; không reindex, xuất bản hoặc commit/push.

**Chưa nghiệm thu:** tới bước 85, bước 86 `PacketDraft` gặp `ALL_PROVIDERS_UNAVAILABLE` và giữ uncertain. Chưa đủ trace để xác nhận nguyên nhân hạ tầng cụ thể. Không gửi lại lượt chưa rõ kết quả.

Thay đổi trong phiên: `CoverageAudit` chặn ngay supporting context thiếu assertion và unrelated có assertion; thêm bảy test tại `test_compilation_coverage_contract_625.py`, giữ test server backstop trong `test_compilation_semantics_604.py`. Các sửa đổi khác đang có được bảo toàn. Recovery adapter kiểm thử tái dùng candidate/hash/receipt, không thêm API production và không sửa job cũ.

Lệnh thực từ repo root:

```text
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context625_continue.py --execute
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context625_continue_contract.py --execute
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context625_checks.py run --scope checks --label focused
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context625_checks.py run --scope final --label full-final
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context625_compare.py
backend/.venv/Scripts/python.exe -m ruff check backend/app/modules/knowledge/compilation_runtime_schemas.py backend/tests/test_compilation_coverage_contract_625.py backend/tests/test_compilation_semantics_604.py
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context625_checks.py cleanup --scope checks
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context625_checks.py cleanup --scope final
```

Baseline 3 FAIL/4 PASS → focused 93 PASS; Ruff PASS. Full 3.792 PASS/18 FAIL nền/17 SKIP, exit 1; exact failure IDs và nguyên nhân khớp Context623, không regression mới. So sánh và cleanup exit 0. Hai lệnh compiler exit 1 lần lượt vì coverage role binding và provider unavailable. Tổng Context625 có 77 phản hồi, một dispatch chưa rõ kết quả; không chạy lại 1–8. Không coi JSON hợp lệ là đã duyệt nội dung.

Hai database regression đã dọn bằng nonce; Storage giữ chính sách, acceptance DB/checkpoint giữ phục hồi. Shared seals và nguồn không đổi. Chưa có final bundle, readback/idempotency cuối lượt và benchmark 64 NOT RUN. [Báo cáo đầy đủ](../bao_cao/context625/REVIEW.md).
