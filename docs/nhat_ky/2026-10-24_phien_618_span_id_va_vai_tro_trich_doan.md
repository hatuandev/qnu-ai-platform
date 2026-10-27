# Phiên618 — Span ID tường minh và role của trích đoạn

Yêu cầu: bổ sung span_id để compiler chọn trích đoạn đúng sau lỗi Context617. Đã kiểm Git/diff, memory và code thật; giữ mọi thay đổi chưa commit.

Thay đổi tối thiểu: thêm `compilation_span_menu.py`, gửi span_id/evidence_id/literal/start/end/allowed_roles thay mảng ẩn ID ở dictionary key; prompt phân biệt span/proof/record, feedback sai role có ID được phép và không lộ input lạ. Role enum và server materialization giữ nguyên, không thêm q7/q84 vào role sai. Version menu tham gia configuration hash. Canonical source/hash/proof và policy không đổi; q-ID chỉ thuộc request, không thêm cột DB hoặc sửa Markdown.

Kiểm chứng trước sửa10FAIL/exit1; sau sửa79PASS, broad232PASS, final-focused92PASS/exit0, có15regression mới. Ruff6filePASS. Full cuối3759PASS/18FAIL nền/17SKIP, exit1,840,58giây; exact18ID/cause khớp baseline6173744/18/17,15ID thêm đềuPASS, không lỗi mới/test mất. Không ghép subtest lịch sử vào log hiện tại. Runner `context618_checks.py`, Python3.12 trong venv, cwd pytest=backend; XML/exit receipts ở `backend/storage/context618`.

Probe đúng một gói cũ trên nguồn frozen3DOCX/381proof, hash giữ nguyên. q7 là nhãn cột; q84 là số đã có record, đều không được dùng cho role LLM chọn ở lượt617. Lượt mới GPT-OSSmedium:1draft/22341input/2234output/stop/0fallback. Server giữ đúng1record, kiểm độc lập exact entity/assertion PASS. Không có semantic/coverage review hoặc whole compiler mới nên chưa APPROVED; không benchmark64. Có calibration riêng khi discovery cache trống, không gộp vào số1draft. Preflight đầu bị chặn trước inference do fixture identity thiếu; không resend uncertain.

DB/MinIO/Qdrant loopback; pytest trên DB nonce/LocalStorage riêng với egress guard. Live ModelOps chỉ usage/lease được phép, không sửa defaults. Hai DB618 đã dọn theo nonce, Storage chứng cứ giữ policy. Sáu nhóm shared domain seals và6file Ruff hashes giữ nguyên; không đo lại vector payload. Kết quả xem [REVIEW618](../bao_cao/context618/REVIEW.md). Không parser/source/QG/model change, reindex, publish, restart, commit/push.
