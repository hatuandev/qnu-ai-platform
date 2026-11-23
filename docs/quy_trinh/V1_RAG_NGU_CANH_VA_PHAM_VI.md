# V1 — Ngữ cảnh chunk và phạm vi có bằng chứng

> **TÀI LIỆU LỊCH SỬ (từ 2026-11-13):** frontendV1, `test-v1-e2e.ps1` và bộ `scripts/v1_e2e_*` đã được gỡ khỏi repo. Các lệnh dưới đây không còn chạy được; giữ để truy vết.

Triển khai phiên 790 cho `backendV1`/`frontendV1`. Không tự sửa corpus hoặc chuyển index đang phục vụ khi cập nhật mã. Prompt trả lời: `qnu.rag.answer/v14`.

## 1. Nguồn và metadata

Khai báo metadata ở bước đăng ký bản biên soạn, trước duyệt/xuất bản. Dùng trình sửa metadata hiện có trên giao diện.

- `data_year`: năm của dữ kiện; `issued_year`: năm ban hành. Khoảng hiệu lực có hai đầu ngày. Không đổi các vai trò này cho nhau.
- `program`, `intake`, `data_year` phải gắn đoạn/hàng/ô cụ thể. Không sao chép năm hoặc ngành từ tên tài liệu cho mọi hàng.
- Trích dẫn phải thuộc **chính target**, không chỉ cùng OCR run. Với target hàng/ô, quote toàn bảng chỉ hợp lệ nếu xuất hiện trong các ô được target chọn.
- Giá trị không biết để trống. Metadata đã đăng ký được ghim vào hash phiên bản và phải có xác nhận ở cổng duyệt hiện có. Thay metadata cần bản mới; không sửa ngầm bản xuất bản.

Đây là kiểm chứng liên kết nguồn và sự hiện diện của giá trị, chưa chứng minh mọi gán vai trò đều đúng về ngữ nghĩa. Người duyệt vẫn phải đối chiếu đối tượng, điều kiện và phạm vi.

## 2. Tạo index có ngữ cảnh

Trong **Chỉ mục & Tìm kiếm**, bật **Gắn ngữ cảnh có nguồn cho chỉ mục mới**, rồi dùng thao tác tạo index hiện có. Chỉ bật sau khi metadata đã được đối chiếu. Generation mới sẽ thay generation đang hoạt động khi worker hoàn tất và xác minh publication snapshot như quy trình cũ. Nên kiểm chứng trước trong collection thử; phiên 790 không tạo generation mới cho bộ 3 PDF đang phục vụ.

Hợp đồng API bổ sung:

```json
{"provider_id": null, "contextual_search": true}
```

Gửi đến endpoint `POST .../collections/{collection_id}/indexing-runs` với idempotency key mới. Mặc định `false` giữ recipe cũ và hash idempotency cũ.

Recipe `qnu.search-context/v1` thêm tiêu đề, heading, từng target metadata và định nghĩa viết tắt có nguồn vào text dùng cho embedding, tìm từ khóa và rerank. `structure.search_context` giữ body gốc, SHA-256, prefix và glossary. Tất cả nằm trong manifest generation. Body gốc vẫn là bản dẫn xuất cũ; OCR/cell/citation gốc không bị thay.

Bộ sinh câu trả lời dùng bản đọc từ body gốc và nguồn canonical như trước. Prefix/glossary không trở thành bằng chứng mới, không được nhân đôi vào prompt. Ngân sách được kiểm trên UTF-8 bytes thực; dự phòng ngữ cảnh tối đa 2 KB hoặc 1/4 cap chunk, lấy mức nhỏ hơn. Đơn vị bảng có rowspan vẫn được giữ nguyên; nếu không vừa thì báo lỗi rõ ràng.

Chunk mới giữ `structure.context.heading_path` với cấp, tiêu đề và mã dẫn chứng từng nút nguồn. Markdown dùng cấp đã được bóc tách. Word dùng cấp đề mục từ Docling. PDF dùng tín hiệu đề mục nhận diện được từ nguồn. `source_scope` giữ tên sheet Excel hoặc số slide PowerPoint. Bảng ở sheet và slide độc lập giữ nhãn cột của chính bảng. Trường cũ `heading` vẫn là tiêu đề gần nhất. Đường dẫn mới nằm trong metadata của chunk.

Khi bật `contextual_search`, row card cũng có `search_context.original_text` và `original_sha256`. Prefix của row card rỗng vì chính nội dung thẻ đã có thông tin nguồn. Chuỗi gửi embedding và dẫn chứng theo ô của thẻ giữ nguyên.

Khi đóng gói câu trả lời, `context_max_bytes` giới hạn tổng dữ liệu dẫn chứng chuyển cho model. Nếu vượt ngân sách, hệ thống chỉ loại các đoạn mở rộng tùy chọn. Khi các đoạn truy xuất chính và điều khoản bắt buộc còn lại vẫn không vừa, API trả HTTP 422 với mã `answer_context_budget_exceeded` trước khi gọi model sinh câu trả lời.

## 3. Nhận diện câu hỏi và hỏi lại

Ở cấu hình nâng cao của trợ lý, chọn **Phạm vi câu hỏi → Nhận diện từ dữ liệu đã xuất bản**, lưu revision mới và tạo hội thoại mới. Cấu hình được ghim theo hội thoại. Chọn **Theo bộ lọc đã chọn** để giữ cách cũ.

API RAG policy / search có trường:

```json
{"scope_resolution": "catalog"}
```

Mặc định là `explicit`. Màn tìm thử cũng có checkbox riêng, không tự thay policy trợ lý.

- Catalog chỉ đọc chunk thuộc workspace đã kiểm quyền, collection, document scope và publication hiện hành; kiểm hash structure với manifest trước khi dùng. Không `SELECT DISTINCT` trên toàn kho rồi đưa vào prompt.
- Ghép nhãn chính xác có chuẩn hóa Unicode/case/whitespace. Nhãn dài nhất tại cùng vị trí thắng nhãn ngắn nằm bên trong; vẫn nhận được khi người dùng nêu riêng cả hai.
- Năm phải có nhãn năm/year, không suy mọi số 4 chữ số là năm. Nếu có cả năm dữ liệu và năm ban hành thì hỏi vai trò, trừ khi câu hỏi nói rõ. Chưa tự diễn giải khoảng năm, ngày hiệu lực hoặc mã khóa thành năm.
- Giữ các phạm vi dưới dạng OR của các bộ AND. Không tự tạo cặp ngành/năm mới khi nhiều chiều đều có nhiều lựa chọn; yêu cầu người hỏi tách rõ từng ý.
- Khi nhiều ngành/khóa/năm dữ liệu còn khả dĩ mà câu hỏi không phải yêu cầu liệt kê/so sánh rõ ràng, trả `409 answer_scope_clarification_required` với câu yêu cầu làm rõ. Hiện dùng thông báo lỗi có nội dung trên UI; chưa có form hội thoại nhiều lựa chọn riêng.
- Bộ lọc cố định được giữ. Không có kết quả trả `no_match`, không xóa filter để tìm lại. Context hàng xóm và dependency bảng cũng phải thuộc các phạm vi đã giải quyết.
- Trace có phiên bản planner, filter thực tế, hash catalog và số alias được mở rộng. Prompt nhận `metadata_filter.any_of` khi bật catalog để giữ từng bộ phạm vi.

Bộ nhận diện hiện bảo thủ, không phải bộ hiểu mọi biến thể ngôn ngữ: tên chưa có trong catalog, lỗi chính tả hoặc mã chưa được định nghĩa cần làm rõ/chọn bộ lọc trên UI. Không tuyên bố tự thích nghi chính xác với mọi văn bản.

## 4. Glossary tự động có nguồn

Khi tạo recipe mới, quét các block canonical đã có citation trong bản biên soạn. Chỉ nhận dạng cặp rõ `Tên đầy đủ (VIẾTTẮT)` có initials khớp. Mỗi entry giữ quote/citation; publication/version và manifest ghim phạm vi của entry. Không tự dịch mã khóa ra năm; không có từ điển ngành hay đáp án benchmark trong mã.

Mở rộng query bằng định nghĩa không mâu thuẫn trong scope hiện hành; giữ query gốc. Nhiều nghĩa thì hỏi lại. Nguồn đã rút xuất bản không được đóng góp glossary. Hiện giới hạn 32 định nghĩa mỗi tài liệu; vượt ngưỡng báo `index_glossary_too_large`, không cắt âm thầm.

## 5. Kiểm chứng trước khi áp dụng rộng

Các test mới `test_contextual_scope_790.py` dùng corpus tổng hợp khác bộ tuyển sinh để kiểm metadata sai block/hàng, nhãn chồng nhau, năm khác vai trò, scope OR, alias đa nghĩa, catalog bị sửa, quyền truy cập và withdrawal. API chạy PostgreSQL/Qdrant thật với provider loopback giả, không chứng minh chất lượng model thật.

Giữ snapshot/gold/revision/provider/prompt/recipe cố định khi so sánh benchmark. Ghi first-attempt cho từng câu, không retry để chọn kết quả xanh. Đánh giá riêng recall của nguồn đúng phạm vi, thiếu evidence, câu trả lời, citation và độ trễ. Artifact chức năng `storage/context790/functional-comparison.json` có `quality_claim: false`; không diễn giải thành tăng recall semantic.

Late chunking cần model/adapter cung cấp token embedding cùng offset và kiểm riêng ngân sách. Phiên này chưa triển khai kỹ thuật đó, chưa tự reindex hay chạy lại 53 câu với model thật.
