# Phiên 745 — Compiler hết output trước khi sinh bản nháp

## Bằng chứng hiện tại

Người dùng chạy admissions-compilation ở phiên7082ee7b7311: FAIL sau khoảng3phút, phần1 failed/chat_output_truncated, phần2–3 pending. Đọc GET progress và raw qua API có auth (không gọi model) xác nhận prompt33666, completion8192, total41858; finish_reason=length, content0ký tự, reasoning25084ký tự. Không lưu nội dung reasoning/prompt vào tài liệu. Đây là lượt compiler thất bại thật; test không báo nhầm.

## Thay đổi

- Planner/prompt v2 trong compilation/segments.py: explicit owned/context_only với chỉ số hàng; nêu rõ bảng literal do backend ghép, không yêu cầu viết từng ô ra đoạn văn. Kế hoạch chia cả theo input và proxy kích thước output của nội dung owned, dành75% allowance cho reasoning/JSON. Proxy UTF-8 không phải tokenizer hay cam kết không truncated. Một unit quá lớn vẫn báo lỗi, không cắt nguồn.
- Service chọn nhánh chia phần cả khi toàn input vừa nhưng output proxy vượt mục tiêu. Manifest/config lưu phiên bản, proxy và tỷ lệ. Không đổi default compiler8192/modelcapacity/quota/credential.
- E2E admissions bật JSON Schema, sửa import benchmark còn thiếu. Chạy lại đúng chặng cho phép một recovery khi failed/chat_output_truncated, cùng provider, chưa review/version; lấy output ceiling hợp lệ ModelOps. Khóa recovery xác định theo run lỗi/policy, lưu compilationHistory/recoveryOf, không retry uncertain hoặc lặp lượt lỗi mới.
- Thêm regression planner/output/ownership và helper recovery; chỉnh fixture prose tách khỏi context bảng bắt buộc. Cập nhật hướng dẫn chạy tiếp.

## Kiểm chứng và giới hạn

- Chỉ đọc Git/diff/source và API progress/raw. Không ghi DB/checkpoint, restart, migration, gọi inference hoặc push.
- Test/build/lint/typecheck/live sau sửa: **NOT RUN** theo yêu cầu trước của người dùng. Bộ integration/fullgate chưa được chạy; lỗi nền lịch sử737 vẫn FAIL. Không báo implementation đã nghiệm thu.
- JSON Schema không bảo đảm model không tiêu hết reasoning budget. Recovery dùng ceiling đã khai báo (hiện16K), không hardcode model hoặc tắt thinking. Cần người dùng restart serve rồi chạy lại admissions-compilation; chỉ PASS mới tiếp publication/chat, không cleanup/init/upload/OCR lại.
