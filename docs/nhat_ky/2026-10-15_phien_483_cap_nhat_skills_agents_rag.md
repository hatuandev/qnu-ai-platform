# Phiên 483 — Cập nhật skill và vai trò agent RAG

## Yêu cầu và phạm vi

Ngày 15/10/2026; người dùng đồng ý cập nhật sau khi đọc Reference Kit và khảo sát skill.
Chỉ sửa hướng dẫn trong qnu-ai-platform, không đổi ứng dụng, môi trường hoặc repo Nexora.
Giữ ngoại lệ người dùng về EnsureDeletedAsync/EnsureCreatedAsync trong Nexora; không áp quy tắc từ repo khác để tự sửa ngoại lệ đó.

## Nội dung

- AGENTS.md gọn, routing skill/role và bất biến scope/provenance/model/quyền.
- Cập nhật 7 skill QNU: 4 skill chuyên môn viết lại ngắn gọn, 3 skill backend/frontend/clean-code chỉnh gate có phạm vi.
- Thêm qnu-rag-evaluation và benchmark contract: draft/gold/holdout, ID mapping, fixed snapshot/candidates, metrics và missing/error records.
- Thêm 5 hợp đồng vai trò cùng handoff; chỉ nạp thủ công, không hứa IDE auto-discover hoặc agent runtime hoạt động.
- Chuyển UI patterns từ root sang reference; thêm verification/workflow/security rules, đồng bộ mục Validation frontend/AGENTS.md.
- Đồng bộ nhật ký/index/WORK_LOG/memory/snapshot; giữ nội dung phiên trước, không đổi số liệu runtime lịch sử.

## Kiểm chứng

Gate của task này là frontmatter, link local, encoding/LF, diff/phạm vi và tình huống sử dụng.
Kết quả kiểm chứng thực tế và manifest được lưu cùng bộ thay đổi sau khi chạy validator.
NOT RUN: pytest, Ruff ứng dụng, frontend build/typecheck, OCR/LLM/Qdrant thật, benchmark và kiểm tra host tự nhận role; không có thay đổi ứng dụng hoặc tích hợp host cần các phép chạy đó.

## Rủi ro và bước sau

Tài liệu mới không chứng minh runtime đáp ứng mọi bất biến; verifier phải đọc code và kiểm tra riêng.
Corpus 82/174 từ kit còn draft; chưa nạp, chưa chấm và chưa có kết quả chất lượng mới.
Các vai trò không tự đăng ký host và không thay quyền công cụ thực; có thể nối host sau khi được yêu cầu.

## Kết quả kiểm chứng tài liệu thực tế

- PASS: validator `skill-creator/scripts/quick_validate.py` cho 8 skill được tạo/chỉnh, qua helper kiểm chứng; không có lỗi frontmatter/name.
- PASS: kiểm tra 27 tệp trong manifest bằng SHA-256; UTF-8 không BOM, LF, NFC và newline cuối tệp.
- PASS: 46 liên kết local được kiểm tra trong các tài liệu thuộc phạm vi; không lỗi liên kết.
- PASS: 14 quy tắc UI ngoài gate cũ được giữ khi chuyển sang reference; gate cũ được thay bằng bảng chung.
- Đã chạy `python -X utf8 .../qnu-skill-update/validate.py` trước ghi và cùng lệnh có `--live` sau ghi, exit 0 cả hai.
- Rà soát thủ công hướng dẫn qua các tình huống: nhãn draft không thành gold, hybrid/rerank cùng candidates,
  enumeration vượt TopK, follow-up giữ scope năm, lỗi provider khác no-evidence, helper test khác API/runtime proof.
  Đây là review nội dung hướng dẫn, không phải chạy các kịch bản trên ứng dụng hoặc agent con.
- NOT RUN: pytest/Ruff ứng dụng, frontend build/typecheck, model/DB/Qdrant thật, benchmark và host discovery;
  task chỉ thay tài liệu/skill, không có kết quả runtime mới.
