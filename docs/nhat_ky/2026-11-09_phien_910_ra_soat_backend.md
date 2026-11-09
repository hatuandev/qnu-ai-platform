# Phiên910 — Rà backend trước khi thiết kế FE mới

## Phạm vi và kết luận

Người dùng yêu cầu đánh giá backend V1 có sạch và dư thừa không trước khi làm FE mới. Đây là rà cấu trúc, tham chiếu code và hợp đồng API. Không sửa/xóa source, không đổi DB/config, không gọi model, không restart dịch vụ. Giữ các tài liệu phiên909 chưa commit.

Backend có nền modular monolith, ports/adapters, dependency injection, worker, quyền workspace và nguồn có phiên bản rõ. Phần cần dọn tập trung vào điều phối tài liệu quá lớn, nhiều cách gọi cùng nghiệp vụ, các tùy chọn tương thích cũ và khung chưa triển khai. Chưa có căn cứ cần viết lại backend hoặc xóa hàng loạt module.

Thống kê hiện tại: `backendV1/qnu` có393file Python,53.864dòng gồm comment/docstring/dòng trống. OpenAPI sinh được163path/205operation, không trùng operationId; số lượng này không tự chứng minh dư thừa. Ruff mặc định toàn `backendV1/qnu` đạt. So AST body nguyên dạng cho hàm>=15dòng chỉ tìm thấy một cặp guard trùng trong hai luồng OCR; phép kiểm này không phát hiện mọi trùng lặp ngữ nghĩa.

## Sáu điểm nên xử lý

### P2-1 — Luồng tự động chưa là mặc định của hợp đồng chuẩn bị

- `knowledge/preparation/schemas.py:13`: bỏ `mode` thì request chọn `source`.
- FE hiện tại chủ động gửi `mode: "auto"` tại `frontendV1/src/features/knowledge/preparation-dialog.tsx:169`.
- `knowledge/preparation/service.py:780` ánh xạ source/ai/auto sang ba cấu hình compiler; API compiler trực tiếp còn có ba cờ source_first/ai_supplement/selective_supplement tại `compilation/schemas.py:20`.
- Hệ quả có thể xác định từ code: FE mới chỉ gửi yêu cầu chuẩn bị tối giản sẽ không nhận chính sách tự động giống FE hiện tại. Đây chưa phải lỗi của FE đang gửi auto đúng.
- Đề xuất: chốt một endpoint/chính sách mặc định cho luồng người dùng; BE tự chọn extractor, nguồn và AI supplement. Giữ API từng bước cho quản trị/nâng cao/tương thích, mô tả rõ. Không đổi default âm thầm khi caller cũ chưa chuyển.

### P2-2 — Các service điều phối đã quá lớn và phụ thuộc hai chiều

- `compilation/service.py`818dòng, `request_run`149–532 dài384dòng: quyền, idempotency, snapshot, chọn chế độ, ngân sách, chia phần, tạo run/artifact/segment và dispatch cùng một hàm.
- `compilation/execution.py`1255dòng; `compilation/review/parts.py`1214; `review/execution.py`1139; `compilation/segments.py`1122.
- `preparation/service.py`945dòng; `rag/answer/service.py:96` có hàm answer316dòng. Số dòng là tín hiệu bảo trì, không tự chứng minh hành vi sai.
- OCR: `automatic.py:16` nhập helper private từ execution; execution lại gọi automatic và mineru_execution; `image_ocr.py:71`, `mineru_execution.py:59` nhập lại helper execution. Publication/index/replacement cũng có đường nhập vòng qua `decisions.py:329`, `index/snapshots.py:109`, `index/sync.py:16` và `lifecycle/replacement.py:149`.
- Đề xuất: tách planner thuần, persistence/artifact và điều phối thực thi; đặt helper OCR dùng chung ngoài execution. Giữ transaction, lease, idempotency và kiểm quyền như cũ. Phân tích import AST có cả import local/TYPE_CHECKING, không coi mọi vòng cú pháp là lỗi khởi động; OpenAPI thực import vẫn sinh được.

### P2-3 — Composition OCR còn mang Nemotron vào runtime và tạo MinerU bên trong domain

- `api/wiring.py:55` vẫn tạo `ManagedOcrEngine(NemotronOcrEngine())`.
- `modelops/resilience/execution.py:256` đặt name nemotron; `:269` tự nhập/tạo MineruOcrEngine cho extract_document.
- MinerU đang có nhánh thực riêng ở `ocr/automatic.py:149` và `ocr/execution.py:611`; không được kết luận rằng hệ thống vẫn dùng Nemotron để đọc mọi PDF.
- Đề xuất: đưa page/document adapter vào composition root và tiêm qua port, đặt tên manager trung lập. Nếu chốt sản phẩm chỉ dùng MinerU thì ngừng hỗ trợ tạo mới provider Nemotron sau khi kiểm DB/provider còn dùng; giữ decoder/schema đọc artifact cũ. Không xóa theo tên file một cách cơ học.

### P2-4 — Cấu hình không còn tác dụng vẫn trông như cấu hình đang hoạt động

- `platform/config.py:74`,`:94`,`:98`: COMPILER_MAX_OUTPUT_TOKENS, RAG_MAX_OUTPUT_TOKENS, CONVERSATION_REWRITE_MAX_OUTPUT_TOKENS chỉ còn khai báo trong runtime qnu; comment cũng xác nhận compatibility.
- QDRANT_COLLECTION/VECTOR_SIZE tại`:41`–42 tương tự không thấy consumer trong qnu; chỉ mục hiện tạo tên/kích thước theo run/model.
- `scripts/v1_e2e_session.py` vẫn gán COMPILER_MAX_OUTPUT_TOKENS/RAG_MAX_OUTPUT_TOKENS/VECTOR_SIZE. Không được hiểu các giá trị đó là trần đang áp cho request.
- Đề xuất: loại khỏi template/help/runner chủ động mới, có thông báo ngừng dùng cho môi trường cũ nếu cần; tập trung mức inference ở ModelOps. Không xóa giới hạn vật lý, giới hạn caller hay số liệu usage.

### P2-5 — Endpoint đặt quota cũ còn nhận body nhưng không áp dụng các giá trị

- `modelops/usage/router.py:41` đánh deprecated cho PUT quota; `_body` bị bỏ qua.
- `usage/service.py:107` chỉ khởi tạo kỳ sử dụng, gán limit=None và blocked=False. Đây phù hợp quyết định bỏ quota tháng, nhưng API còn trông giống thao tác cấu hình.
- FE cũ còn endpoint/quota panel, integration fixtures còn dùng endpoint này.
- Đề xuất: FE mới chỉ đọc thống kê sử dụng. Công bố ngừng endpoint cấu hình, chuyển caller/tests trước rồi mới gỡ. Giữ reservation/settlement chống ghi nhận trùng và kiểm toán, không xóa usage vì bỏ quota.

### P3-6 — Stub và khung ngoài phạm vi còn nằm trong cây sản phẩm

- `adapters/providers/gemini.py:10`, `paddleocr.py:10`: constructor chỉ ném NotImplementedError. Tìm tham chiếu trong checkout chỉ thấy định nghĩa, không thấy wiring/caller.
- Các khung `document_types`, `node_catalog`, `tools`, `workflows` có README Phase0/ngoài MVP và __init__; một số thư mục knowledge/chunks/facts/glossary, rag/search cũng mới là khung.
- Đề xuất: xóa stub chưa dùng hoặc đưa mô tả sang backlog sau khi xác minh không có extension ngoài checkout; không trình bày như tính năng đã hỗ trợ. Lợi ích chính là giảm hiểu nhầm, dung lượng tiết kiệm nhỏ.

Một lệch kiến trúc nhỏ: `knowledge/index/router.py:116`–140 tự query IndexRun sau authorize. Có kiểm quyền; không kết luận lỗi bảo mật. Khi chỉnh module này nên chuyển query vào service cùng các thao tác khác, không cần làm refactor toàn repo riêng.

## Những phần phải giữ

- Nguồn gốc, canonical OCR, revision/hash, cell/header/note/bbox và artifact dẫn xuất.
- Tách đăng ký tài liệu, duyệt/xuất bản và readiness phục vụ. Có thể gộp UX, vẫn cần kiểm quyền/chuyển trạng thái ở BE.
- Generation chỉ mục, outbox sync, cơ chế thay bản sau khi ready, quyền và kiểm nguồn hiện hành.
- Usage reservation, idempotency, audit, trạng thái uncertain/cancel và chính sách retry đúng tầng.
- Projection/prompt/parser phiên bản cũ nếu còn dữ liệu ghim vào chúng. Từ legacy không chứng minh mã chết.

## Thứ tự trước FE mới

1. Đóng bản đồ capability và hợp đồng luồng chính: chuẩn bị tự động → kết quả → người dùng duyệt → publish → readiness/chat; phân biệt API quản trị và API chính.
2. Dọn cấu hình vô hiệu/stub, chốt composition OCR; chuyển caller trước khi retire endpoint cũ.
3. Tách các khối điều phối lớn theo ranh giới planner/persistence/executor; ưu tiên vùng cần sửa cho luồng chính, không dựng framework mới.
4. Kiểm API tối thiểu của FE mới và regression quyền/snapshot/cancel/idempotency/publication/index-sync. Giữ FE V1 đối chiếu trong lúc chuyển.
5. Tiếp tục nghiệm thu chất lượng RAG độc lập. F13 của phiên908 vẫn là lỗi chưa xử lý; dọn cấu trúc không tự làm câu đó đúng.

## Bằng chứng kiểm tra trong phiên

- `python -m ruff check backendV1/qnu --output-format concise`: PASS,exit0.
- Python AST đọc393file: parse đạt, thống kê file/hàm/duplicate/import; chỉ đọc, không có DB/model/network.
- Import app và `app.openapi()` không chạy lifespan: PASS,163path/205operation/0trùng operationId/1deprecated PUTquota; không mở API/worker.
- Lần in tag đầu gặp UnicodeEncodeError do console cp1252; chạy lại với PYTHONIOENCODING=utf-8 đạt. Đây là lỗi công cụ in kết quả, không phải lỗi OpenAPI.
- Dùng rg xác minh caller của stub/cấu hình và đọc các service/router nêu trên. Các lần tìm wildcard đường dẫn Windows không hợp lệ được đổi sang thư mục thật, không suy không có mã từ exit lỗi.
- Không chạy full Pytest, benchmark model hoặc kiểm tải trong task rà mã này. Không báo PASS toàn hệ thống. Bài đo/unit/API của908 là lịch sử, không thay kết quả mới.
