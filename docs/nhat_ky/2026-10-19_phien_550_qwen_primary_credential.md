# Phiên550 — Qwen primary, credential và live retest

Người dùng yêu cầu Qwen3.5 làm model chính rồi cung cấp endpoint/API key để cập nhật. Dùng skill ModelOps, giữ các thay đổi chưa commit của phiên549.

Đổi primary local ModelOps sang `qwen3.5-9b`, fallback `cx/gpt-6-luna`; giữ các default khác bằng kiểm chứng hash/session mới. Cập nhật credential qua service ModelOps, truyền stdin, mã hóa và đối chiếu provider/pool/relational key ở session mới. Endpoint đã đúng, không sửa URL/capability/danh mục model.

Helper mới `backend/scripts/switch_chat_primary.py`; mở rộng `backend/scripts/verify_json_output_contract.py` để probe primary không fallback và thu chẩn đoán HTTP chỉ số/hash. Không sửa application code trong phiên550. Báo cáo/metadata tại [context550](../bao_cao/context550/VALIDATION_REPORT.md).

Live nhỏ trước/sau key đều PASS (exit0); sau key Qwen tiếng Việt 23 input/29 output,643,1ms,stop, không fallback. Hai lượt tài liệu trước key FAIL (exit1): Qwen HTTP400 rồi GPT fallback JSON/schemaPASS nhưng binder scope ambiguous. Lượt API sau key FAIL (exit1): Qwen vẫn HTTP400 context8192/output6000/input ít nhất2193; GPT fallback ReadTimeout. Không biến NOT RUN downstream thành PASS; chưa có proposal hợp lệ/human approval/apply. Ruff2helperPASS(exit0); full Pytest hiện tạiNOT RUN, lịch sử549 vẫn18FAIL/2336PASS/17skip.

DB/MinIO/Qdrant local đã audit; fixture chỉ ghi DB/LocalStorage test có nonce. Xuất metadata, xác minh và xóa DB riêng/runtime tạm hoàn tất. Giữ cấu hình Qwen/key mới theo yêu cầu. Không commit/push/restart/deploy/index/publish hoặc duyệt nguồn. Cần xử lý tương thích context/output budget trước nghiệm thu luồng tài liệu; chưa triển khai ngoài phạm vi.
