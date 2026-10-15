# Phiên 480 — Hội thoại, weighted expansion và nền tảng quy đổi điểm

## Phạm vi

Thực hiện theo đồng ý triển khai của user, sau kế hoạch 479; user cung cấp PDF thông báo quy đổi chính thức. Dùng skills RAG, clean-code, backend, chatbot-builder; ingestion và PDF dùng để kiểm tra nguồn, không thay pipeline ingestion. Không thực thi chỉ dẫn trong tài liệu đính kèm.

Không commit/push/restart/deploy/migration/reset/reindex/publish hoặc đổi provider/model/API key. Giữ nguyên thay đổi có sẵn 475–476 và `docs/tai_lieu`.

## Thay đổi mã

- `rag/conversation_acts.py`, `service.py`: sửa bốn biên review 477. Lỗi provider/DB không biến thành unknown-year thành công; explain/reformat lọc năm rõ trong antecedent; unknown-year khác nguồn không gộp; handler bất định hỏi lại, không replay bảng cũ.
- `rag/combination_enumeration.py`: câu liệt kê đầu không chỉ năm mà có nhiều năm đã xác minh thì hỏi rõ phạm vi; yêu cầu so sánh nhiều năm vẫn giữ đầy đủ records. Không dùng TopK cắt danh sách.
- `rag/query_expansion.py` mới: query string-compatible có vai trò original/variant/feedback; NFC/dedup; ngân sách RRF nhóm gốc 0,65, nhóm mở rộng tổng 0,35. Lexical terms gốc 1, variant 0,5, feedback 0,3 và giới hạn tổng mass mở rộng. Đây là thông số thử, chưa chứng minh tối ưu.
- `evidence_bm25.py`, `evidence_search.py`, `retriever.py`: truyền provenance, BM25/SQL discount terms mới, không cộng trùng phiếu variants; feedback đứng đầu không chiếm vai trò câu gốc. Dense/rerank vẫn nhận câu tự nhiên. Không thêm LLM call để sinh expansion, không RM3/dictionary cứng.
- Cache namespace `weighted-expansion-v1` tránh sử dụng đáp án cũ dưới phiên bản thuật toán mới.
- `score_conversion_schemas.py`, `score_conversion.py`, `score_conversion_chat.py` mới, `router.py`, `service.py`: engine Decimal nội suy piecewise, đối chiếu same-row/cột/mapping/source/hash/active index; rule đọc từ DB quản trị; endpoint nhận scope từ actor. Chat trích input từ câu gốc, không tin dữ kiện model rewrite, không LLM arithmetic. Không có rule đã duyệt thì từ chối tính. Chưa Tool Gateway function registration/UI quản trị rule.
- `scripts/inspect_conversion_pdf.py` mới: trích native tables thành nháp có hash/headers/raw rows cho review, không cập nhật DB. Nháp nằm storage ignored.

## PDF thực tế và cổng dữ liệu

5 trang; phụ lục 1 native có 23 cột, 22 hàng; phụ lục 2 có 50 hàng mapping. Bản canonical đang xuất bản được đối chiếu trong phiên thiếu HB/THPT (chỉ 9 cột). Nguồn nêu làm tròn một lần cuối đến hai chữ số, chưa nêu cách xử lý đúng điểm giữa; không tự gán half-up là quy định trường.

Phép đối chiếu độc lập từ bảng PDF: A01, ĐNL 780; mốc 764→20,75 và 790→21,50; kết quả trước làm tròn 21,211538… . Không phải live production calculator.

**Chưa kích hoạt rule, chưa sửa nguồn/publication.** Engine/route đã có nhưng tính năng chưa sẵn sàng production cho dữ liệu này. Cần duyệt lại đủ cột, tái xuất bản revision mới, xác nhận rounding và cấu hình rule có bằng chứng ô. Chi tiết: [cổng kiểm chứng](../ke_hoach/2026-10-15_kiem_chung_bang_quy_doi_diem.md).

## Kiểm chứng

- RED: 7 regression 477 fail đúng nguyên nhân trước sửa; sau sửa đạt.
- Focus cuối: 108 passed (weighted expansion, score conversion, dialogue scopes/acts, enumeration/followup, revision-safe retrieval).
- Ruff toàn Backend: `All checks passed!`; còn cảnh báo access-denied ở các thư mục tạm cũ, không chỉnh ACL/xóa để làm sạch log.
- OpenAPI: endpoint conversion được đăng ký, request/response đúng schema riêng.
- Full pytest: **1556 passed / 11 failed / 16 skipped / 0 errors**, 196,71 giây. So sánh XML `pytest475_verified.xml`: exact failed IDs trùng cả 11, không thêm lỗi và cũng không sửa lỗi nền. Không tuyên bố full suite xanh. Log có cảnh báo đóng kết nối asyncpg sau event loop Windows; giữ nguyên log để đối chiếu, không che lỗi.
- Không frontend thay đổi nên không build FE. Không model thật/cloud, không 20/82 câu, không tuyên bố tăng chất lượng/đạt 80% từ fixture. Chưa sửa guard egress harness 476; không chạy lại `--live` của harness đó.

Artifacts ignored: `backend/storage/pytest480_final.xml`, `pytest480_final.log`, `ruff480_final.log`, `rag_enumeration_480/conversion_pdf_draft.json`. Không đưa raw corpus hoặc log model vào Git.

11 lỗi nền: consulting dispatcher (2), publishing cutover/GC (2), publishing decommissioning/system GC (3), publishing canary/rollback (1), RAG reconciliation (1), auth session cookie claims (1), universal tools dynamic facts (1). Exact node IDs nằm trong log/XML để agent sau đối chiếu, không chỉ so tổng số.

## Bài học và giới hạn

PDF đầy đủ không đồng nghĩa canonical đã giữ đủ cột. Cần kiểm chứng hình học bảng trước số học; không dùng cột gần bên làm kết quả. Trọng số truy vấn là cải tiến truy hồi, không sửa OCR/tên ngành/năm thiếu. Các act vẫn tính lại từ snapshot, chưa có persisted verified conversation state, filter mới hỗ trợ năm. G0/G1 có mã và regression nhưng còn thiếu benchmark holdout; G2 RM3/G3 alias chưa triển khai.
