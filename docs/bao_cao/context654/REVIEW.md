# Context654 — Nối hậu OCR, review tự động và sửa Compiler

## Phạm vi và kết quả

Người dùng chọn triển khai mục1→2→3 trên backendV1. Đã nối lựa chọn text version
đã lưu vào Compiler/review/publication/index/citations; thêm review job bền vững
sau Compiler; thêm preview và chấp nhận sửa nội dung thành Compiler run con.
UI làm sau. Không thay dữ liệu phục vụ, cấu hình ModelOps, reindex hoặc restart.

Mỗi nguồn giữ hash OCR/manifest gốc cùng ID/hash bản sửa nếu được chọn. Omission/0
dùng gốc. Run cũ không tự đổi sang latest và không backfill review. Bản sửa Compiler
không có raw LLM giả, không gọi lại Compiler, giữ parent và bảng/citation bảo vệ,
lưu MD/JSON mới có readback và tạo review riêng. Duyệt/xuất bản vẫn có quyết định riêng.

Chi tiết contract: [Compiler workflow](../../../backendV1/docs/compiler-workflow.md).
Mã mới chủ yếu ở `knowledge/compilation/workflow/`, migration0013 thêm2bảng và
binding/provenance; worker vẫn dùng ARQ v1. Khóa auto cố định chống request lặp;
failed/uncertain không tự gửi lại model. Preview gắn actor/hash/expiry và audit.

## Kiểm chứng chức năng

Cwd `D:/DuAnPhanMem/qnu-ai-platform/backendV1`. Dùng venv hiện có và wrapper
`storage/context654/run_checks.py` gọi harness `scripts/run_isolated_tests.py`.
Mỗi lượt dùng PostgreSQL loopback mới, giữ sentinel legacy, tự drop DB sau test;
OCR/chat/embedding là HTTP fixture tổng hợp, Redis/ARQ và Qdrant là adapter thật.

| Lượt | Kết quả thật |
|---|---|
| Baseline ba ranh giới | 3FAIL: chưa nhận text_versions, chưa có auto-review/edit-context |
| API/migration đầu | 4PASS |
| Workflow trọng tâm | 22PASS |
| Queue thật đầu | 1FAIL: burst đầu thoát khi queue tạm rỗng, chỉ tiêu thụ Compiler |
| Queue sau điều chỉnh harness thành hai burst | 1PASS, hai job/hai HTTP và review completed |
| Đầu cuối nguồn sửa→review→child→publish→Qdrant/search | 1PASS |
| Tương thích cũ, nguồn, lưu lỗi/đồng thời | 18PASS |
| Uncertain recovery và revision mới | 2PASS |
| Full đầu, đủ52file qua4nhóm | **489PASS/1FAIL/0SKIP**, 484,53giây wall |
| Downgrade sau sửa thông báo | 1PASS |
| Chạy lại nguyên nhóm3 sau sửa | **86PASS**, 323,78giây wall |
| Tập kết quả cuối đủ4nhóm | **490PASS/0FAIL/0SKIP**, 30ID mới/0ID mất so với652 |

Lỗi full là `test_knowledge_regressions_639::test_downgrade_cannot_mark_success_and_block_next_upgrade`:
migration mới chặn downgrade đúng nhưng thiếu cụm thông báo bảo toàn evidence mà
hợp đồng cũ yêu cầu. Đã sửa thông báo; không đổi assertion hoặc cho phép xóa dữ liệu.
Báo cáo lần đầu giữ riêng `initial-3.*`; số490 là hợp của các nhóm đã kiểm chứng,
không phải một process chạy lại toàn suite sau đó. Tổng thời gian test của các
nhóm cuối1161,47giây. Node IDs và phạm vi có trong [validation.json](validation.json).

Lệnh chốt: `python storage/context654/full.py`,
`python storage/context654/recheck.py`, `python storage/context654/lint.py`,
`python storage/context654/finish.py`. Full đầu exit1; recheck/lint/finish cuối exit0.
Ruff check/format29file PASS; format từng có1file chưa chuẩn sau sửa thông báo,
đã format lại. Source BE sửa/thêm UTF8/noBOM/LF PASS. OpenAPI79path/105operation,
75path cũ giữ contract route; request/response bổ sung trường tương thích.
14DB thử xác nhận0còn; Qdrant quan sát0collection v1. Redis thử dọn đúng khóa sở hữu.
Tài liệu19tệp UTF8/noBOM/LF,82liên kết local PASS; tiếng Việt đã đọc lại.

## Kiểm tra byte legacy chưa đạt

**FAIL**, không được ghi thành475file giữ nguyên byte. Seal đầu phiên có475file
`backend/app`: 413khớp hash, 62khác hash. Với48file, đổi LF hiện tại về CRLF tái tạo
đúng hash đầu phiên; 14file còn lại chưa có bản nội dung trước để giải thích khác
biệt byte. Cả62file hiện khớp nội dung Git index khi chuẩn hóa CRLF/LF và không
có diff Git nội dung. Chưa đủ bằng chứng quy nguồn thay đổi byte cho một tác nhân.

Không ghi/restore/reformat những file legacy này để tránh ghi đè ngoài phạm vi.
Đối chiếu này không làm kết quả Pytest490 thành FAIL nhưng ngăn kết luận bảo toàn
toàn bộ byte legacy. Danh sách và trạng thái riêng nằm trong validation.json.

## Giới hạn và bàn giao

- NOT RUN model thật/corpus thật hoặc nghiệm thu độ đúng chính tả/ngữ nghĩa/RAG.
  Fixture chứng minh luồng, quyền, pin, idempotency và lưu trữ, không chứng minh
  model phát hiện đủ ý thiếu. Review chưa phải cổng publication bắt buộc.
- Chưa áp migration0013 lên DB phục vụ hoặc restart BE/worker. Chưa làm UI.
- Blob ghi dở có thể mồ côi khi transaction thất bại; chưa thêm GC.
- Các hình653 được giữ như ảnh lịch sử, có nhãn và liên kết quy trình29 hiện tại.
