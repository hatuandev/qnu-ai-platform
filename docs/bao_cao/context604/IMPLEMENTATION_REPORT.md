# Context604 — Phạm vi, chiều quan hệ và đối soát coverage

Ngày 23/10/2026. Bổ sung bảo vệ đợt 3–4; chưa nghiệm thu toàn bộ nội dung compiler thật, chưa triển khai UI hoặc tích hợp serving đợt 5. P10 ngoài phạm vi.

## Nguyên nhân và phương pháp

1. Binding v1 chứng minh tọa độ/hash của proof nhưng không chứng minh một giá trị scope diễn giải thực sự xuất hiện trong proof. Reviewer boolean có thể bỏ sót nguồn/năm. Policy v3 buộc mỗi scope.value là một đoạn nguyên văn liên tục trong proof đã chọn, tách scope nguyên tử; không suy authored draft/official từ trạng thái hệ thống. Entity phải cùng source với assertion. Section chỉ chứa một source revision và một profile data/effective tương thích; ngày publication có thể đi cùng dữ liệu nhưng giữ role riêng. Heading không được thêm năm ngoài temporal assertions.
2. Quan hệ có source_id/target_id nhưng trước đây không có phép kiểm riêng cho hướng. Quy ước SUBJECT → OBJECT được khai báo tường minh: supersedes mới → cũ; supports căn cứ → đối tượng; prerequisite điều kiện tiên quyết → đối tượng phụ thuộc; exception ngoại lệ → quy tắc chung. Lượt kiểm riêng nhận cặp endpoint không sắp theo chiều đề xuất, dựng lại chiều từ proof. Phải khớp đề xuất; ngày mới hơn không đủ chứng minh thay thế. Không tự đảo relation hoặc đánh dấu duyệt.
3. missed_evidence trộn thiếu dữ kiện với inventory hỗ trợ. Hai lượt phân loại độc lập cùng model phân biệt required_assertion/supporting_context/unrelated/unresolved. Phải đủ đúng ID; context phải gắn assertion cùng source. Bất đồng giữ unresolved. Chỉ required mới có tối đa một extraction/review nhắm đúng gói, không chạy lại toàn tài liệu. Lưu review gốc, hai ledger, repair và phần còn thiếu; không tạo scalar từ bước kế toán. Context đã đồng thuận có reverse dependency tới assertions/sections.
4. Các lượt thật bị chặn ID assertion/section không được cấp. Transport v3 dùng handle ngắn cho object đã tồn tại trong review/synthesis và enum reference hợp lệ cho mọi bước, rồi khôi phục ID bất biến ở server. Value/quote/reason không bị thay ID như chuỗi tùy ý. Extraction mới không ánh xạ local ID sang assertion cũ. Offered context khai báo deferred có ledger riêng; primary chưa dùng vẫn được giữ. Ngân sách đo đúng wire payload, schema enum và transport instruction, không chỉ base contract.
5. Classifier status proposed/verified được bọc rõ là server-derived navigation, không chứng minh authored draft/official hay hiệu lực pháp lý. Định nghĩa thời gian tách data/publication/effective/event/unknown: ngày phiên bản là event nếu nguồn không chứng minh publication. Không sửa metadata/canonical cũ.
6. Reviewer nhận nguyên văn các condition/exception đã chọn, không phải điều kiện mới. Thiếu qualifier thật vẫn chặn. Synthesis giữ toàn bộ assertion cùng nguồn trong một nhóm khi vừa ngân sách; nguồn lớn vẫn chia có coverage, không trim. So sánh ngày ban hành và năm dữ liệu phải dẫn đủ cả hai assertion vai trò.
7. Hai đầu quan hệ gửi bằng membership map endpoint_set, không theo mảng có thể bị hiểu là chiều đề xuất. Payload phải giống nhau dù đảo chiều đề xuất; witness tự dựng chiều từ raw proof. Probe model thật cho biểu diễn cuối bị provider ReadTimeout, chưa có semantic PASS. Không sửa artifact cũ thành ready.

## Phạm vi mã

- `compilation_runtime_schemas.py`: policy v3, coverage/direction contracts và định nghĩa vai trò thời gian.
- `services/compilation_semantics.py`: literal scope, source/year section và kiểm chiều độc lập.
- `services/compilation_coverage.py`: hai phân loại, repair có giới hạn, bảo toàn review gốc.
- `services/compilation_engine.py`: điều phối các bước trên trong 64 calls/600 giây hiện có.
- `services/compilation_transport.py`: handle/enum và giữ nguyên literal.
- `services/compilation_modelops.py`: config hash phân biệt transport/semantic policy mới.
- `services/compilation_validation.py`: kiểm lại machine verdict từ ledgers khi finish/read.
- `services/compilation_service.py`: v1/v2 vẫn đọc/reject/revoke được; chỉ policy hiện hành v3 được chấp thuận mới. Receipt quyết định cũ vẫn giữ lịch sử.

Schema proposal/binding v1 của Context602 không đổi. Không migration, không sửa nguồn/canonical, không parser/RAG/P10/FE, không model hoặc config vận hành. Bản dẫn xuất vẫn review_only/unpublished; approval không tạo facts, vector hoặc publication.

## Giới hạn thực tế

Literal anchor chỉ chứng minh trích nguyên văn, không chứng minh đầy đủ vai trò/applicability. Kiểm ngữ nghĩa vẫn dùng model, hai lượt cùng model có thể tương quan lỗi. Vì vậy cần đối chiếu nguồn độc lập và quyết định người dùng trước nội dung có hiệu lực; không coi machine_complete là chứng nhận production. Association context chỉ dùng phần hai lượt đồng thuận; phần còn lại candidate_only/effective=false. Bất đồng relevance vẫn giữ chặn, chưa có căn cứ bỏ một verdict thiếu nội dung chỉ vì lượt khác nói unrelated.

Section có phạm vi riêng; quan hệ xuyên nguồn/năm biểu diễn qua relations, không gộp tùy tiện vào prose chung. Graph vẫn chỉ khám phá trong bounded synthesis groups, chưa exhaustive. Repair, coverage, kiểm chiều và correction định dạng đều nằm trong budget cũ; vượt budget dừng rõ lỗi.

Live test tái dùng canonical artifact parser602 và kiểm hash ba DOCX; các source ready trong DB thử là fixture format-only, không phải chứng nhận fresh parsing hoặc full Quality Gate. Không có browser/chatbot E2E hoặc benchmark64 mới.

Tám file app khác snapshot đầu604, không xóa file app. Các kết quả thực chạy, lỗi còn lại và giới hạn: [VALIDATION_REPORT.md](./VALIDATION_REPORT.md). Vai trò24 proof cũ: [RECONCILIATION_24.md](./RECONCILIATION_24.md).
