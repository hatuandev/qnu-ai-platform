# Kế hoạch metadata năm và thời gian cho QNU V1

**Trạng thái** · Sẵn sàng bàn giao triển khai. Chưa thay đổi mã ứng dụng.

## 1. Mục tiêu và phạm vi

Sau khi người dùng tải lên và phát hành tài liệu, chatbot có thể lấy đúng số liệu theo năm và trả lời đúng lịch, hạn theo sự kiện. Luồng người dùng vẫn là **Tải tài liệu → Kiểm tra nội dung → Duyệt và phát hành**. Hệ thống tự lưu thông tin đủ căn cứ. Người dùng chỉ cần xem các trường hợp mâu thuẫn hoặc chưa rõ có ảnh hưởng đến việc sử dụng tài liệu.

Triển khai trên `backendV1/` và `frontendV2/`. Đi theo thứ tự **A. Năm và tiêu đề bảng → B. Lịch và hạn theo sự kiện → C. Tự lưu, lập chỉ mục và kiểm tra RAG**. Hoàn thành kiểm thử của từng chặng trước khi chuyển tiếp. Có thể dừng và bàn giao sau mỗi chặng.

Ưu tiên PDF và DOCX trong lượt nghiệm thu. Giữ tương thích với dữ liệu đã lưu và các định dạng hiện có. Giữ nguyên nguồn, JSON OCR, bản chỉnh sửa đã chọn, hàng/ô, tiêu đề, chú thích và tọa độ. Mọi dữ liệu nhận diện là dẫn xuất truy vết được về đúng revision và hash nguồn. Xem [nguyên tắc dự án](../../AGENTS.md) và [kế hoạch thời gian trước đây](14_ke_hoach_ngu_canh_thoi_gian_facts_va_rag_dag.md) để đối chiếu khái niệm. Dùng mã V1 hiện hành làm căn cứ triển khai.

## 2. Hiện trạng làm mốc

| Hiện trạng đã đối chiếu | Điểm vào mã |
| --- | --- |
| Biên dịch có nhánh LLM bổ sung. Nhánh chọn lọc hiện bỏ qua khối bảng. Quy tắc backend kiểm tra lại đề xuất. | [supplement.py](../../backendV1/qnu/domains/knowledge/compilation/supplement.py) · [plan.py](../../backendV1/qnu/domains/knowledge/preparation/plan.py) |
| Bản xem trước của cả hai PDF tuyển sinh nhận nhầm `1800` trong dòng điện thoại thành `data_year`. | [supplement.py](../../backendV1/qnu/domains/knowledge/compilation/supplement.py) · [automatic_metadata.py](../../backendV1/qnu/domains/knowledge/publication/automatic_metadata.py) |
| 24 bảng trong hai bản biên dịch đã lưu thiếu tiêu đề được đánh dấu. Phép thử ngoại tuyến tìm được cấu trúc tiêu đề ở 8 bảng bằng các bộ nhận diện sẵn có. Trong đó 3 bảng có ô gộp chỉ ghi năm, bên dưới là các cột chỉ tiêu, số nhập học hoặc điểm. Bộ gắn nhãn năm hiện vẫn bỏ qua các ô năm đứng riêng như vậy. | [table_dependencies.py](../../backendV1/qnu/domains/knowledge/index/table_dependencies.py) · [table_year.py](../../backendV1/qnu/domains/knowledge/compilation/table_year.py) |
| Có API xem trước metadata. FE V2 chưa gửi `automatic_metadata_sha256` khi tạo tài liệu hay thêm phiên bản. Metadata chỉ vào chỉ mục sau khi được lưu trên phiên bản đăng ký. | [publication/router.py](../../backendV1/qnu/domains/knowledge/publication/router.py) · [publication/service.py](../../backendV1/qnu/domains/knowledge/publication/service.py) · [publication-dialog.tsx](../../frontendV2/src/components/knowledge/publication-dialog.tsx) · [chunking.py](../../backendV1/qnu/domains/knowledge/index/chunking.py) |
| Trong chế độ tra cứu theo danh mục metadata, “điểm chuẩn năm 2025” và “điểm chuẩn 2025” có thể tạo phạm vi tìm kiếm khác nhau. | [query_scope.py](../../backendV1/qnu/domains/knowledge/index/query_scope.py) |

Các kết quả trên là mốc khảo sát. Cần đối chiếu từng câu trả lời và dẫn chứng trước khi quy nguyên nhân của các câu sai năm trong báo cáo E2E. [Báo cáo sự cố](../compilation-review-run-defects.md)

## 3. Hợp đồng dữ liệu cần giữ

| Thông tin | Phạm vi gắn nhãn | Quy tắc |
| --- | --- | --- |
| Năm dữ liệu | Đoạn, hàng, cột hoặc ô của số liệu | Giữ các năm song song khi nguồn có nhiều năm. Không dùng năm trong tên tệp, ngày ký, năm hiện tại hay văn bản được dẫn làm năm của số liệu. |
| Ngày và năm ban hành | Đúng văn bản hoặc văn bản con trong tập hợp nhiều nguồn | Giữ đúng độ chính xác của nguồn. Có năm thì lưu năm, không dựng ngày 01/01. Một ngày được nhắc trong căn cứ pháp lý thuộc văn bản được trích dẫn. |
| Hiệu lực | Đúng văn bản, mục hoặc điều khoản | Tái dùng `effective_from` và `effective_until` khi chứng minh được vai trò và phạm vi. Chỉ có một đầu mốc thì giữ đầu mốc còn lại chưa xác định. |
| Lịch và hạn | Từng sự kiện, đợt, đối tượng hoặc giai đoạn | Lưu được một ngày, một khoảng, một hạn chót hoặc một thời hạn tương đối. Một mục có thể chứa nhiều sự kiện. |

Mọi giá trị dùng để tra cứu cần có loại, độ chính xác, phạm vi, vị trí bằng chứng và nguồn đã ghim. Ví dụ “20/07” giữ ngày/tháng nếu chưa chứng minh năm. Có thể bổ sung năm khi tiêu đề lịch trực tiếp quy định cùng năm cho các dòng đang xét và bằng chứng xác nhận được liên kết đó. Giữ trạng thái chưa xác định, mâu thuẫn và đã kiểm chứng một cách phân biệt. Chỉ dùng giá trị đã kiểm chứng làm bộ lọc.

## 4. Chặng A — Sửa nhận diện năm và tiêu đề bảng

1. Tạo ca tái hiện cho số `1800` trong dòng liên hệ. Sửa nhận diện vai trò dựa trên toàn cụm nguồn và các dấu hiệu cấu trúc, ví dụ trường thông tin liên hệ, cụm số điện thoại hoặc mã hồ sơ. Không thêm ngoại lệ riêng cho số `1800`, một ngành hay một tên tệp. Dùng cùng một nguyên tắc xác minh cho trích xuất bằng quy tắc và đề xuất từ model. Trích đoạn ngắn của LLM không được bỏ qua dấu hiệu loại trừ trong câu nguồn.
2. Ưu tiên tiêu đề native. Khi thiếu, thử dùng các bộ nhận diện `typed_header` và `multitier_header` đã có. Chỉ dùng ô năm đứng riêng khi cấu trúc xác nhận nó là tiêu đề quản lý các cột con, có hàng dữ liệu và có căn cứ mô tả vai trò số liệu. Tôn trọng `row_span`, `col_span`, thứ tự cột và chú thích. Kiểm tra tiêu đề cha/con khi có nhiều năm hoặc mâu thuẫn. Chỉ nối tiêu đề giữa các trang khi quan hệ nối bảng có bằng chứng.
3. Dùng cùng kết quả xác định cấu trúc ở bước đề xuất và kiểm chứng `validate_annotations`. Giữ bằng chứng tới ô năm và các nhãn con xác định phạm vi. Tạo dẫn xuất hoặc bằng chứng cấu trúc phù hợp với mô hình hiện có. Không sửa trực tiếp OCR gốc hoặc âm thầm gắn năm cho toàn bảng. LLM chỉ cần tham gia giải nghĩa tiêu đề hoặc chú thích khi bước cấu trúc để lại ứng viên có thể kiểm chứng.

**Điều kiện qua chặng** · Tái hiện đúng trường hợp hotline rồi chứng minh lỗi đã hết. Trích được ba bảng có tiêu đề năm đã quan sát hoặc nêu từng bảng còn thiếu bằng chứng. Kiểm thử ô gộp ngang/dọc, năm riêng từng cột, năm trong chính hàng, bảng thiếu tiêu đề, tiêu đề cha/con mâu thuẫn, ngày ký gần bảng và vị trí ô nguồn khi trích dẫn.

## 5. Chặng B — Nhận diện lịch và hạn theo sự kiện

1. Chốt hợp đồng tối thiểu cho hạn đăng ký/nộp hồ sơ, ngày thi và ngày công bố kết quả. Dùng loại sự kiện chuẩn phục vụ tra cứu và giữ nhãn gốc trên nguồn. Giữ phạm vi theo đợt, đối tượng, phương thức hoặc điều khoản nếu có căn cứ. Hỗ trợ nhiều sự kiện trên cùng một hàng hoặc đoạn. Giữ riêng các trường năm ban hành, năm dữ liệu và hiệu lực hiện có. Kiểm tra cấu trúc lưu và tương thích đọc trước khi thêm trường. Kiểu `attributes` hiện dùng giá trị vô hướng và không phù hợp để nhét danh sách sự kiện thành chuỗi.
2. Chuẩn hóa ngày/tháng/năm, khoảng mở hoặc đóng theo nghĩa nguồn và các thời hạn tương đối. Với “trong vòng 5 ngày làm việc kể từ ngày nhận thông báo”, lưu giá trị, đơn vị và sự kiện bắt đầu tính. Chỉ tính ra ngày cụ thể khi có ngày bắt đầu, quy tắc đếm và lịch áp dụng. Với nguồn thiếu năm hoặc giờ, giữ độ chính xác hiện có. Phân biệt lịch mới thay thế lịch cũ khi có căn cứ về hiệu lực/phạm vi thay thế. Nếu cùng phạm vi có hai lịch mâu thuẫn, giữ hai căn cứ và báo cần đối chiếu.
3. Backend trích các mốc rõ trước. Với ứng viên chưa phân loại được hoặc cần đối chiếu nhãn, gửi cho LLM một nhóm nhỏ gồm các đoạn, ô, tiêu đề và chú thích liên quan. Dùng cấu hình model mặc định qua ModelOps và ngân sách phù hợp. Tái dùng lượt bổ sung hiện có khi đáp ứng hợp đồng. Yêu cầu đầu ra có cấu trúc gồm loại, giá trị, phạm vi, ID và trích đoạn nguồn. Từ chối ID ngoài nhóm và mọi giá trị hoặc phạm vi thiếu căn cứ. Giữ trạng thái xử lý LLM chưa hoàn tất riêng với trường hợp nguồn thiếu dữ liệu.
4. Giữ kết quả theo phiên bản nguồn, phiên bản quy tắc/schema và cấu hình model đã ghim. Tận dụng cơ chế lưu kết quả từng phần và khóa idempotency hiện có. Chỉ xử lý lại phần bị ảnh hưởng khi nội dung, cấu hình hay quy tắc liên quan thay đổi. Tránh nhét cả tài liệu vào một lượt gọi hoặc thêm lượt gọi riêng cho từng ngày.

**Điều kiện qua chặng** · Kiểm thử hai đợt có hạn khác nhau, một đợt có ngày thi và ngày công bố, ngày thiếu năm, lịch qua năm, đợt được gia hạn, thời hạn tương đối và ngày chỉ xuất hiện trong căn cứ pháp lý. Dẫn chứng phải mở được tới đúng đoạn, ô hoặc chú thích. Chốt cách đọc phiên bản cũ trước khi nối xuất bản.

## 6. Chặng C — Tự lưu, lập chỉ mục và đo chất lượng RAG

1. Sau khi A và B đạt, nối API `registration-metadata/{run_id}` vào cả tạo tài liệu mới và thêm phiên bản trên FE V2. Gửi `automatic_metadata_sha256` cùng yêu cầu đăng ký. Giữ luồng tương thích của client cũ. Khi bản xem trước đã lỗi thời, tải lại đúng bản và báo người dùng nếu nội dung cần xem lại. Hộp duyệt chỉ hiển thị mục cần đối chiếu có ý nghĩa nghiệp vụ. Giữ nguyên quyền đăng ký, duyệt và phát hành.
2. Đưa metadata đã kiểm chứng vào đúng đoạn, hàng/cột và snapshot phát hành. Mở rộng phạm vi từ câu hỏi có căn cứ rõ như “điểm chuẩn 2025” và “hạn đăng ký đợt 2”. Giữ phạm vi khi mở rộng truy vấn, tìm kết hợp, xếp hạng và thêm ngữ cảnh bảng. Câu so sánh hai năm cần dẫn chứng riêng cho từng vế. Câu hỏi về lịch cần phân biệt đúng sự kiện, đợt và đối tượng. Khi kết quả trống, giữ phạm vi đã hỏi và trả lời thiếu căn cứ hoặc đề nghị làm rõ. Phân biệt tình trạng này với lỗi hạ tầng.
3. Kiểm thử đầu cuối trên kho cô lập. Dùng [PDF Thông tin TSĐH cập nhật](<../tai_lieu/tuyen_sinh/Thông tin TSĐH cập nhật.pdf>), [PDF Thông tin tuyển sinh 2025](<../tai_lieu/tuyen_sinh/Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed.pdf>) và DOCX ngắn cho các ca biên. Lập nhãn trước khi gọi model thật, gồm câu hỏi, đáp án, phạm vi và trang/ô nguồn. Đối chiếu trước/sau trên cùng revision, cấu hình và chính sách tìm kiếm. Kiểm tra thử luồng đăng ký lại, dữ liệu cũ và lần xử lý thất bại trong môi trường cô lập.

### Ma trận nghiệm thu tối thiểu

| Ca thử | Kết quả cần đạt |
| --- | --- |
| Hỏi điểm chuẩn một năm, có và không có chữ “năm” | Cùng phạm vi năm khi ý định rõ. Dẫn đúng ô điểm. |
| So sánh 2024 và 2025, cùng ngành và phương thức | Mỗi số có đúng cột và tiêu đề năm tương ứng. |
| Tài liệu ban hành năm sau, bảng chứa số liệu năm trước | Phân biệt đúng hai vai trò. Nhánh hỏi ngày ban hành dùng chính văn bản nguồn. |
| Tra cứu hiệu lực và thời hạn đăng ký trong cùng tài liệu | Chọn đúng loại mốc và phạm vi. |
| Hỏi hạn đợt 2 khi đợt 1 và ngày thi cùng xuất hiện | Chọn đúng dòng đợt 2 và đúng sự kiện. |
| Hỏi hạn tương đối khi thiếu ngày bắt đầu | Trả lại thời hạn và điều kiện gốc. Không đưa ngày tự tính. |
| Năm hoặc hạn sai, mâu thuẫn hoặc không có bằng chứng | Không tạo nhãn đã kiểm chứng. Chatbot báo thiếu căn cứ hoặc cần làm rõ. |
| Đăng ký tài liệu mới và thêm phiên bản mới trên FE V2 | Metadata tự lưu trên đúng phiên bản. Chỉ bản đã phát hành mới được tra cứu. |
| Tài liệu cũ thiếu metadata | Vẫn đọc được. Câu trả lời không suy năm từ tên tệp hoặc mở rộng sang năm khác. |

### Đo và bàn giao

- Dùng nhóm câu hỏi trọng tâm đã chốt. Không chạy lại bộ 100 câu. Báo số đúng giá trị, đúng loại mốc, đúng phạm vi và đúng dẫn chứng. Báo riêng ca chưa đủ căn cứ, ca sai và lỗi provider.
- So sánh cùng đầu vào số nhóm gửi LLM, lượt gọi, token đầu vào/đầu ra và thời gian xử lý metadata. Phân biệt số provider báo với số hệ thống ước tính. Dùng Qwen mặc định đã cấu hình nếu còn khả dụng và môi trường kiểm thử được phép. Ghi tên cấu hình đã chạy, số lượt thử và kết quả từng lượt. Không gán mức tiết kiệm trước khi đo.
- Theo [bảng kiểm chứng](../../.agents/rules/verification.md), chạy regression trọng tâm sau từng chặng. Cuối batch ổn định, chạy Ruff có phạm vi, kiểm tra API/migration nếu có, một lượt full Pytest cô lập và Biome/build trên FE nếu đã sửa FE. Full Pytest là kiểm chứng ứng dụng riêng với bộ 100 câu hỏi. Ghi chính xác PASS/FAIL/NOT RUN. Live model, chỉ mục và trình duyệt cần bằng chứng riêng.
- Giữ bản phát hành và index đang phục vụ. Tạo bản thử trong kho cô lập. Kế hoạch chuyển đổi dữ liệu đã phát hành và reindex diện rộng là công việc riêng sau khi có số đo và xác nhận phạm vi.

## 7. Lệnh giao việc cho IDE

> Đọc AGENTS.md và kế hoạch này. Bắt đầu từ chặng A. Kiểm tra code/diff hiện tại và tái hiện lỗi hotline cùng bảng tiêu đề năm trước khi sửa. Tái dùng bộ nhận diện bảng và đường lưu provenance hiện có. Kiểm chứng chặng A, ghi kết quả thực và file liên quan, sau đó tiếp tục B rồi C nếu chặng trước đạt. Dùng nguồn đã lưu và môi trường cô lập, bảo toàn sửa đổi chưa commit. Không chạy lại bộ 100 câu. Khi bàn giao, nêu chặng đã xong, lệnh kiểm chứng và việc còn lại để IDE khác tiếp tục.
