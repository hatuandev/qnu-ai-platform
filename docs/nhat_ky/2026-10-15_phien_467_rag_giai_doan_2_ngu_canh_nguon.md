# Phiên 467 — Giai đoạn 2: nguồn, metadata và ngữ cảnh bảng

Ngày 2026-10-15. Người dùng duyệt triển khai giai đoạn 2 sau baseline phiên 466.

## Phạm vi và quyết định

Chỉ cải thiện bóc tách/biểu diễn nguồn; không sửa retrieval, classifier, ModelOps,
ngân sách context/output hoặc kết luận answered/partial. Không reset/migrate DB,
không bóc tách lại revision thật, tạo chỉ mục hoặc xuất bản. Không chỉnh docs/tai_lieu.
Áp dụng Clean Code, Backend, Ingestion và RAG: thay đổi cục bộ, thuật toán cấu trúc,
raw span bất biến, model/provider đọc từ DB và lỗi kiểm thử phải được công bố.

### 1. OCR bổ sung có giới hạn

- Phát hiện dòng số hiệu không có chữ số hoặc dòng ngày hành chính chỉ còn năm.
  Chỉ render phần trên trang đầu, chặn tại bảng đầu tiên; không OCR lại bảng native đúng.
- Chỉ chép dòng số/ngày hoàn chỉnh và duy nhất từ OCR; không chép đoạn văn ngoài hai trường.
  Mâu thuẫn với trường native giữ nguyên nguồn; thiếu/lỗi/crop rỗng có audit riêng.
- Chuẩn hóa khoảng trắng quanh dấu `/` trong số hiệu và biên chữ–số ở dòng ngày;
  không sửa chữ/số/dấu tiếng Việt hoặc đảo ngày tháng. Lưu nguyên `ocr_text` để đối soát.
  So sánh mâu thuẫn bằng dòng ngày hành chính độc lập, không lấy ngày văn bản viện dẫn.
- Kết quả là đề xuất cần duyệt với `METADATA_OCR_REVIEW`, kể cả OCR thành công;
  không dùng kết quả OCR để tự xác nhận năm áp dụng của mọi hàng.
- Session OCR riêng để ghi log không vô tình commit transaction nguồn đang xử lý.
  Runtime tôn trọng engine chọn hoặc cấu hình OCR ModelOps hiện hữu.
- User chỉ cho phép kiểm chứng ảnh đầu trang qua PaddleOCR nội bộ 100.105.13.53.
  Diagnostic có allowlist host, dùng riêng nhánh PaddleOCR, không fallback cloud.

### 2. Nhãn cột thận trọng

Tận dụng bằng chứng khớp của catalog hiện hữu; không thêm từ điển vá câu hỏi.
Nhãn ghép mô tả phương thức không được coi là mã phương thức; từ “điểm” đơn lẻ
không đủ gán `cutoff_score`. Header đủ rõ đã có vẫn giữ mã cũ. Header mơ hồ lưu
nguyên nhãn và `attribute_context.status=unknown`, không đoán thành điểm trúng tuyển.

### 3. Liên kết ngữ cảnh nguồn

- Sidecar `source-context-v1` liên kết hàng với đoạn dẫn, header và phần điều kiện/chú giải
  sau bảng. Chuỗi bảng qua trang cần header trùng, trang liền kề, STT tiếp diễn,
  không có đoạn độc lập xen giữa. Không gộp chỉ vì số cột bằng nhau.
- Hỗ trợ phần sau bảng bắt đầu bằng nhãn ngắn kết thúc dấu hai chấm **hoặc** danh sách
  đánh số từ 1; giữ phần tiếp ở trang sau, dừng ở heading/caption mới/phần ký tên.
  Đây là `context_only`, không chứng minh mọi điều kiện áp dụng cho mọi ngành.
- Projection `header: cell` cho hàng có/không có STT, giữ dấu “–”, đường dẫn header nhiều tầng.
  Không nhồi toàn bộ ghi chú vào từng vector; lưu tham chiếu exact source-unit.
- Fact chỉ gắn pointer khi hàng khớp duy nhất; hàng trùng ở bảng độc lập không lấy bản cuối.
  Không tạo trang vật lý giả khi canonical chưa có page marker.
- Pin hash graph/canonical trong chunk metadata/cache key; kiểm graph trước tái sử dụng cache,
  graph sai trả `SOURCE_UNIT_INVALID`. Không thay schema/digest manifest đã lưu;
  artifact v6 không có graph vẫn đọc và dùng công thức cache cũ.

### 4. Bảng Word có ô gộp

Docling có rowspan/colspan rõ ràng chuyển qua HTML normalizer hiện hữu, chỉ thay đúng
một occurrence của bảng gốc. Bảng lặp mơ hồ không thay tùy tiện, có warning để đối soát.
Kiểm thử DOCX thật bằng python-docx/Docling giữ đường dẫn 2024/A, 2024/B và 2025/A;
năm ban hành 2026 không được gán sang các ô này.

## Tệp thay đổi

- `backend/app/modules/knowledge/facts.py`: bằng chứng nhận diện cột từ catalog hiện hữu.
- `services/header_rescue.py`, `source_extraction.py`, `source_pages.py`: OCR đầu trang,
  giữ provenance trong page manifest; extractor lên `layout-v10-source-context`.
- `services/source_links.py`, `source_artifact.py`: graph/hash/fact pointer, artifact v7.
- `normalization/retrieval_units.py`, `services/chunk_set_service.py`: projection/cache/validation.
- `parsers/docling_office_parser.py`: giữ cấu trúc ô gộp qua HTML.
- `backend/tests/test_source_context_stage2.py`: hành vi nguồn/graph/Word/OCR lỗi và thành công.
- `backend/tests/test_rag_floor_stage1_466.py`: bỏ đúng một strict-xfail đã sửa ở nhãn cột;
  giữ ba ca lỗi classifier/status còn mở, không sửa assertion để che lỗi.
- `backend/scripts/audit_source_context_stage2.py`: chẩn đoán chỉ đọc và tính toán in-memory;
  OCR opt-in một ảnh với host cho phép, không lưu revision/vector/publish.
- Cập nhật runbook 02, memory, WORK_LOG, mục lục và snapshot 467.

## Kiểm chứng

- Red run đầu: **7 failed/2 passed**, tái hiện thiếu graph/OCR và gán nhầm loại cột.
- Focus đợt 1: **87 passed/40,79s**.
- Focus liên module: **136 passed, 3 xfailed/46,41s**.
- Sau bổ sung hàng không STT/hàng trùng/crop rỗng: **17 passed/4,78s** cho suite mới.
- Lượt OCR thật lộ thêm spacing và false conflict với ngày văn bản viện dẫn: hai red run
  mỗi lượt **1 failed** đúng nguyên nhân; final focus **141 passed, 3 xfailed/46,97s**,
  trong đó suite giai đoạn 2 có 19 ca. Không dùng mock OCR làm chứng cứ nghiệm thu live.
- Ruff toàn Backend đạt, chỉ có cảnh báo quyền đọc artifact cũ; không cài dependency.
  `uv run` bị quyền cache nên dùng cùng Python venv chạy Ruff/Pytest.
- Full Backend: **1.400 passed, 11 failed, 16 skipped, 3 xfailed/189,50s**.
  XML `backend/storage/pytest467_full.xml`. Đối chiếu tên test với
  `backend/storage/pytest432_handoff_full.log`: đúng cùng 11 ID, **không có ID lỗi mới**.
  Gồm consulting export (2), publishing/canary/GC/direct upload (6), reconciliation (1),
  auth role cookie (1), universal tools (1). Không khẳng định toàn suite xanh.
  Đây là full trước bổ sung guard crop/spacing/strict issue-date; có lượt handoff cuối bên dưới.
- **Full handoff sau toàn bộ sửa runtime: 1.403 passed, 11 failed, 16 skipped,
  3 xfailed/182,83s**, XML `backend/storage/pytest467_handoff.xml`. Vẫn cùng 11 ID lỗi nền,
  không lỗi mới trong các phần thay đổi. Không bỏ test lỗi hoặc sửa assertion cho xanh.
- Không FE build vì không thay Frontend. Không chạy lại 20/82/Ragas trong giai đoạn này.

## Đối soát PDF thật và ranh giới nghiệm thu

Diagnostic native trên chính PDF đã xuất bản khớp SHA-256. Có 93 source-units;
hai hàng QLGD/SP Toán giữ nguyên, projection có đủ bốn phương thức và liên kết phần
điều kiện/chú giải trang 7–8. Không chứa phần “Nơi nhận” hoặc ký tên trong liên kết ghi chú.
Fingerprint trước/sau cho cấu hình, snapshot, collection metadata, source/facts/chunks,
inventory đều không đổi. JSON: `backend/storage/rag_stage2_467/final_inspection.json`.

PDF Inspector subprocess không thành công trong các lượt diagnostic (kể cả nâng quyền);
chưa kết luận nguyên nhân và native parser giữ chứng cứ gốc.
Kết quả này không thay thế nghiệm thu layout trên mọi loại tài liệu. Lượt diagnostic native
không yêu cầu OCR nên trạng thái artifact in-memory `auto_ready` **không phải** kết luận
đầu trang đã khôi phục đủ; pipeline thật khi thực hiện rescue sẽ yêu cầu duyệt.

Lượt OCR theo chuỗi mặc định ban đầu bị auto-review chặn trước khi chạy; không gửi ảnh
cloud. Sau đó người dùng chỉ duyệt PaddleOCR nội bộ. Bốn lượt cùng crop qua nhánh
PaddleOCR tường minh (hai incomplete, một conflict, một proposed) trong quá trình red/green,
không fallback cloud; ghi log OCR bình thường, không giữ toàn DB read-only.

Nguyên nhân live: `Số: 121 /TB-HDTS`, `ngày 09 tháng7 năm 2026` không hợp whitespace
grammar; sau chuẩn hóa lại lộ ngày 15/02/2026 trong đoạn căn cứ bị hiểu nhầm là ngày ban hành.
Đã sửa bằng biên chữ–số/dấu `/` và parser ngày độc lập, không từ điển sửa dấu.

Final `backend/storage/rag_stage2_467/paddle_verified.json` dùng chính binary checksum và
native canonical đã pin, không lặp lại PDF parser: **proposed**, hai dòng số 121/ngày
09/07/2026 được bổ sung trong bộ nhớ; toàn bộ native text vẫn là suffix không đổi;
95 units (thêm hai trường), bảng/notes còn nguyên. Audit raw OCR giữ `HDTS`, không tự
đổi thành `HĐTS`; người duyệt phải đối chiếu số hiệu đầy đủ. Review **required** với
`METADATA_OCR_REVIEW`. Response thật `engine=paddleocr_vl`, `fallback_triggered=false`.
Fingerprint config/publication/source/facts/chunks/metadata/inventory trước/sau bằng nhau,
đồng thời kiểm đọc riêng sau full suite cũng xác nhận không thay đổi.

Không gửi toàn PDF hoặc ảnh sang Gemini/Mistral/OpenRouter; quyền hẹp chỉ áp dụng
diagnostic này, không đổi cấu hình combo OCR sẵn có của app.

## Áp dụng và công việc còn lại

Khởi động lại BE/worker để nhận code mới. Nguồn đã xuất bản không tự bị sửa/backfill.
Khi áp dụng, chọn nguồn cần sửa → Bóc tách lại → đối chiếu số/ngày/header/ghi chú →
duyệt → tạo chỉ mục staging → thử RAG → xuất bản. Không reset toàn DB/kho.

Giai đoạn sau vẫn phải sửa candidate selection theo entity/metric, luồng thực sự chạy
sau reset, budget phù hợp context window và trạng thái no-answer/partial. Chưa cam kết
hai câu live hoặc 82 câu đã đúng chỉ nhờ cải thiện nguồn. Bài học: phải thử trên cấu trúc
thật (ghi chú không có nhãn, ô gộp, hàng không STT), không chỉ fixture thuận lợi.

Không commit/push/deploy/restart app, không sửa ModelOps hoặc dữ liệu đang phục vụ.
