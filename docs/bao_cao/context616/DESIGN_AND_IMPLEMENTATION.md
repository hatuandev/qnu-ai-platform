# Context616 — Ràng buộc dữ kiện compiler với nguồn

## Nguyên nhân đã tái hiện

Context614 có thể xác nhận nhầm tên chỉ số dù con số xuất hiện trong nguồn. Guard615 đã chặn kết luận đó, nhưng model vẫn phải tự viết các nhãn và liên kết mà guard yêu cầu. Các lượt thật tiếp theo tìm thấy thêm bốn vấn đề:

- Header canonical chưa xác định làm mất đường từ ô tới cột, dù DOCX gốc còn đủ bằng chứng để kiểm tra riêng.
- Một reviewer đánh giá dữ kiện theo giả thuyết trong câu hỏi, thay vì kiểm tra đúng nội dung assertion. Trường nguồn chưa ghi giá trị vì thế có thể bị đánh trượt dù assertion chỉ báo sự thiếu đó.
- Menu chọn tên đối tượng loại số đơn nhưng còn cho chọn phân số/số ghép. Trùng literal không chứng minh vai trò đối tượng.
- Bước tổng hợp nhận trạng thái header cũ nhưng thiếu một phần chứng cứ native mà bước kiểm tra bảng đã sử dụng. Hàng header rỗng còn có thể bị hiểu nhầm thành một dữ kiện cần bổ sung.

Đây là lỗi đóng gói và phân công kiểm chứng trong compiler. Không có bằng chứng từ các ca này để quy lỗi cho retrieval chatbot hoặc kết luận context 32K không đủ.

## Luồng xử lý

1. Đọc lại ba nguồn đã đóng băng; kiểm hash DOCX, canonical và artifact. Không sửa canonical, parser, header lưu trữ hoặc revision nguồn.
2. Đối chiếu toàn bộ grid native với bảng canonical duy nhất. Typography, hàng đầu, hình dạng hay các ô số chỉ là điều kiện tạo ứng viên. Hai lượt kiểm tra độc lập phải xác nhận vai trò từ candidate và ít nhất hai dòng dữ liệu hoàn chỉnh; bất đồng giữ unresolved.
3. Model chọn vị trí cột định danh, cột giá trị, đoạn dẫn nhập và bằng chứng năm. Server kiểm phạm vi và chép nguyên văn từng record. Đoạn dẫn nhập là frame của bảng, không phải chỉ số dùng chung cho mọi ô.
4. Với văn xuôi, model chọn các span có offset và proof. Tách lựa chọn cụm từ khỏi biểu thức số; không cho dùng một lượng thuần số làm tên đối tượng. Server tạo entity/assertion từ literal đã chọn, không dùng nhãn do model tự viết.
5. Kiểm chứng tính đúng của từng assertion bằng toàn bộ bằng chứng được đưa ra, không cung cấp câu hỏi dẫn hướng. Kết quả invalid, not_checked, unresolved hoặc contradicted vẫn chặn.
6. Kiểm tra độ đầy đủ riêng với câu hỏi và primary scope. Không bắt nguồn cung cấp một giá trị vốn chưa được định nghĩa; cũng không coi khoảng trắng của layout là một dữ kiện. Điều kiện/phạm vi/ngoại lệ cần thiết còn thiếu vẫn là coverage debt và vẫn chặn.
7. Model chọn nhóm assertion và heading nguyên văn; server kết xuất nội dung section. Review tổng hợp nhận cả candidate, hai dòng mẫu, định dạng native, locator và đoạn dẫn nhập. Trạng thái parser không thay cho một kết luận ngữ nghĩa mới; bằng chứng native và các witness trước đó cũng không tự cấp xác nhận.
8. Đọc lại bundle phải kiểm hash, scope, record materialization, primary coverage, assertion coverage, review ledger và kết quả tổng hợp. Không chỉ tin `machine_complete` đã lưu.

Nếu candidate có item sai ngữ nghĩa hoặc lỗi cơ học, compiler được tạo lại **đúng gói đó tối đa một lần**. Candidate mới được bind và kiểm chứng lại từ đầu; reviewer không nhận critique của tác giả. Chỉ thay candidate hiệu lực khi review và coverage mới đều complete, đồng thời không lặp lại nội dung ngữ nghĩa của assertion đã thất bại. So sánh bỏ qua ID và thứ tự các tập proof/scope: đổi ID, đảo proof hoặc một verdict mới tốt hơn không phải sửa thành công. Candidate cũ và kết quả bị từ chối/unchanged vẫn nằm trong ledger. Sửa tiếp không đạt hoặc vượt budget thì giữ blocker; không đổi verdict cũ thành supported.

Đóng gói tách theo nhiệm vụ: chọn chủ đề giữ context gốc và thông tin locator của đoạn dẫn nhập; kiểm chứng dữ kiện/tổng hợp còn nhận hai dòng mẫu cùng định dạng native. Gói chỉ chọn record không lặp hướng dẫn tạo claim văn xuôi. Menu heading chỉ lấy nhãn có liên kết với assertion đang tổng hợp; toàn bộ raw evidence của nhóm vẫn giữ cho kiểm chứng. Đây là giảm metadata/hướng dẫn không dùng đến, không cắt nội dung nguồn.

## Các ranh giới giữ nguyên

- Policy compiler mới là `qnu-compilation-review/v5`; đọc bundle v1–v4 theo policy cũ. Không chuyển checkpoint cũ thành kết quả review mới.
- Protocol của span, bảng native, field selection, review và coverage tham gia configuration hash. Receipt dùng lại trong fixture nghiệm thu phải khớp request đã hoàn tất và chỉ dùng một lần; đó không phải tính năng tự di trú checkpoint của app.
- `source_unspecified` là tên trên wire của trạng thái nguồn chưa ghi rõ; nội bộ vẫn giữ unknown/null và bằng chứng về giới hạn. Không chuyển thành 0 hoặc fact chắc chắn.
- Hai luồng primary/context khác nhau; đưa một proof làm context không làm nó biến mất khỏi catalog. Header/frame chỉ được hạch toán vào coverage khi có assertion thực sự liên kết tới row tương ứng.
- Quan hệ cần phát biểu nguồn chứng minh endpoint, hướng và phạm vi. Cùng con số, tên, năm hoặc chủ đề không đủ để tạo quan hệ.
- Planner đo schema, raw evidence, metadata, instruction, output reserve và correction envelope thực tế. Giảm nội dung hướng dẫn lặp; không tăng cap hoặc cắt nguồn để làm request vừa.
- Model được gọi qua ModelOps với route được phép. Thí nghiệm giữ GPT-OSS medium/output8192 bằng override trong process; không đổi defaults/provider DB.
- Compiler chỉ tạo bản nháp phục vụ review. Không duyệt người dùng, ghi facts có hiệu lực, reindex, xuất bản hoặc thay đổi Quality Gate ingestion.

## Phạm vi mã

Ba tệp mới trong lượt616 là `compilation_grounding.py`, `compilation_columns.py` và `compilation_candidate_repair.py`. Các thay đổi còn lại nằm ở runtime schemas và các service compiler: catalog, coverage, engine, metrics, modelops, review, structure, synthesis, transport, validation.

Regression616 kiểm literal/role, số ghép, unknown, hash, native grid trùng/sai, header data, caption trùng/sai locator, composite identity, sibling-year, field note, review scope, opaque proof handles, coverage ledger, synthesis proof closure và đọc lại bundle. Ba fixture cũ được điều chỉnh để chọn đúng source của ca kiểm thử, so policy hiện hành và cho phép đúng prefix Storage test616; không bỏ assertion hoặc bỏ kiểm tra quyền.

Kết quả thực chạy và giới hạn nghiệm thu được ghi riêng trong [REVIEW.md](REVIEW.md).
