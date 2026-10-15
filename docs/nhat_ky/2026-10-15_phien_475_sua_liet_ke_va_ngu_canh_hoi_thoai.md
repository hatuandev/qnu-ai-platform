# Phiên 475 — Sửa liệt kê tổ hợp và ngữ cảnh hội thoại

## Mục tiêu

Sửa hai lỗi phiên474: câu liệt kê ngành theo tổ hợp chỉ trả7 mục; câu tiếp nối “sao ít thế” mất chủ đề trước truy hồi. Dùng skills RAG, Backend và clean-code. Người dùng chỉ cho phép model nội bộ nhận tài liệu trong kiểm chứng. Không đổi model/config, reset/migration, OCR/reparse/reindex/publish, restart/deploy hoặc stage/commit/push.

## Phương pháp và tệp thay đổi

- `backend/app/modules/rag/service.py`: resolver trước retrieval; ghi câu hỏi thật trong metadata. Enumeration ở nhánh fact_hybrid trước cache/TopK, namespace cache mới; evidence-policy opt-in giữ pipeline riêng.
- `conversation_resolution.py`: hợp đồng independent/followup/recheck/clarify trên ba câu hỏi user trước, không dùng assistant prose làm evidence. Recheck chạy lại nguyên câu được chọn, không sinh lý do suy đoán vì sao danh sách ngắn. ID sai, số mới/đổi năm bị mất thì hỏi lại; chủ đề độc lập không kế thừa chủ đề cũ.
- `combination_enumeration.py`: đọc nguồn published trong snapshot pin, batch16; reviewed facts keyset500, không dùng TopK làm danh sách đầy đủ. Model phân loại ý định và chọn default scope, không chọn tên ngành/viết số liệu. Nguồn model bỏ qua vẫn được duyệt với năm unknown; không tự gán năm qua tên file/ngày ký. Năm xác nhận cần verified years hoặc heading ancestor cùng nguồn của các records. Filter năm tại record/cột; raw render, có nguồn và chú thích số bản ghi khác số ngành duy nhất. Proof sai từ chối, không hạ xuống danh sách thiếu.
- `combination_records.py`: dùng column roles/subject aliases đã có; cụm môn liên tiếp theo vị trí/dấu nối, tránh nhận “sinh” trong “tuyển sinh” thành môn thứ tư. Chỉ cùng tuple mới khớp, giữ mã chương trình đầy đủ. Năm ô/cột lịch sử thắng năm văn bản; bảng song song không mượn tổ hợp của entity khác. Unknown years không gộp chéo nguồn. Không thêm từ điển ngành/đáp án/model.
- `evidence_facts.py`: exhaustive phân trang thay ranked subset, tách entity trong hàng song song, giữ entity_code DB. Default evidence ranking/ngân sách không đổi.
- `tests/test_enumeration_and_followup.py`:21ca hồi quy về42records, tuple AND, code suffix, scope/proof/tenant, lỗi DB/model, năm mới/cột lịch sử,503facts qua hai trang, recheck và tích hợp trước retrieval/bypass cache/TopK/free generation.
- `tests/test_revision_safe_qdrant_and_retrieval.py`: positive-control sparse/neighbors đổi thành câu giải thích có ngành cụ thể để tiếp tục kiểm tra nhánh hybrid; enumeration có integration riêng, không mock helper ép danh sách thiếu thành pass.
- `scripts/audit_rag_floor_stage1.py`: tùy chọn conversation dùng chung cho followup; default không đổi.
- `scripts/audit_enumeration_context.py`: đọc primary từ DB, xác minh endpoint nội bộ rồi chặn mọi adapter khác trước khi xây dựng; facade/service/model outputs thật. Có chat/usage/key-health/gap bình thường, không phải toàn DB read-only.
- `scripts/verify_enumeration_report.py`: đọc DB, kiểm tra raw span/hash và reviewed identity/value; oracle riêng đếm mục cẩm nang từ canonical, không gọi runtime parser/model.
- `.gitignore`: ignore `backend/storage/rag_enumeration_*/` vì reports chứa prompt/tài liệu. Giữ nguyên mọi report, artifact và `docs/tai_lieu`.

## Kiểm chứng, bao gồm các lượt chưa đạt

- Regression mới trước nối resolver cho thấy truy hồi nhận nguyên “sao ít thế”. Sau sửa bộ trọng tâm ban đầu84pass; bộ mới cuối21ca nằm trong full gate.
- `internal_first.json`: initial96records nhưng year proof yếu; followup thành câu giải thích rồi model suy đoán lý do; explicit2025 bị nhận thêm môn Sinh nên no-answer. Không coi các lượt đó đạt.
- `internal_verified.json`: guard năm siết đúng nhưng model bỏ3/5nguồn, khiến từ chối toàn câu. Server bổ sung nguồn bỏ qua với unknown, không nới proof gán năm giả.
- `internal_final.json`: initial/followup124records, explicit2025 có34,2037no-answer; là lượt trung gian trước bổ sung biên cột lịch sử/mã facts.
- **`internal_verified_final.json`**: mã runtime cuối,4ca dùng primary `qwen3.5-9b` phân giải động từ DB, không fallback. Initial124records~3.74s; followup124records~4.12s; explicit2025 có34~3.24s;2037insufficient_context~5.05s. Không suy p95/accuracy82 từ4mẫu.
- Oracle độc lập **34/34mục** cẩm nang2025, không thiếu/thừa;33mã cơ sở nhưng34mã chương trình đầy đủ gồm biến thể. **113raw citations** đúng span/hash, **180reviewed citations** đúng identity/value DB qua3lượt answered; không lỗi. Đây là tổng citations qua các lượt, không phải số nguồn riêng. Oracle đầu dùng blank paragraphs sai vì canonical ghép nhiều mục trong một paragraph; đổi sang ranh giới mục đánh số rồi đối chiếu set, không sửa đáp án để khớp oracle.
- Protected fingerprints config/publication/target source+facts+chunks/collection metadata/inventory đều unchanged, `blocked_destinations=[]`. Không có adapter ngoài endpoint nội bộ được tạo; fallback production không đổi.
- Full trung gian `pytest475_final.xml`:1480pass/12fail/16skip, thêm1test hybrid cũ vô tình đi enumeration vào AsyncMock DB thiếu corpus. Đã sửa intent positive-control và có integration enumeration riêng.
- **Full cuối `pytest475_verified.xml`/`.log`:1485passed/11failed/16skipped/0errors,193.04s**. Exact failure IDs so với baseline473 được đối chiếu, không lỗi mới. Ruff toàn Backend đạt (cảnh báo ACL ở artifact cũ, không chmod/xóa để giấu); script verifier mới cũng Ruff đạt. Không sửa FE nên không chạy Vite build.

## Giới hạn và bàn giao

124là bản ghi nhiều nguồn/năm, không phải124ngành duy nhất; nguồn thiếu year context vẫn unknown khi không hỏi năm và bị loại khi hỏi năm cụ thể. Coverage là toàn records thuộc các dạng cấu trúc đã nhận diện trong pinned snapshot, không chứng minh mọi layout đều parse đủ. Intent/scope model vẫn có thể từ chối thừa. Chưa UI/HTTP/20/82, chưa nâng cấp mọi enumeration của evidence opt-in branch; không tuyên bố toàn RAG ổn định80%. Cần BE/worker nhận code mới; không cần reset DB/nạp lại vector.

Bài học: LLM không được cắt số lượng records; tuple/năm phải gắn cấu trúc ô nguồn. Phản hồi về độ đầy đủ cần kiểm tra lại, không phải tự suy đoán lý do đáp án cũ ngắn.
