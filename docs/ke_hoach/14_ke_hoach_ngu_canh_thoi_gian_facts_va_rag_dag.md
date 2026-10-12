# Kế hoạch chuẩn hóa ngữ cảnh thời gian trong Facts và RAG DAG

Trạng thái: Đang triển khai; các đợt #386–#387 đã có code, regression và kiểm thử runtime nhóm số liệu chính, chưa nghiệm thu toàn bộ kế hoạch. Cập nhật ngày 12/10/2026.

### Tiến độ thực tế phiên #386

### Cập nhật triển khai phiên #387

- Docker/PostgreSQL đã chạy lại. Migration cộng thêm `20261012_fact_temporal_context` đã áp dụng: sáu cột nullable và index truy vấn theo snapshot/entity/attribute/year. Không reset/drop hoặc tự gán năm cho facts legacy.
- Đã có API và UI **Ngữ cảnh** tại chi tiết nguồn/Studio: tạo revision mới từ Markdown hiện có, nâng artifact cũ mà không OCR lại; sửa metadata hoặc năm/phương thức/đơn vị một fact, giữ evidence gốc, ghi actor/reason/time, kiểm hash và chặn sửa từ revision cũ. Bắt buộc duyệt; approval chỉ cập nhật bản nguồn, không đổi serving index. Test PostgreSQL dùng transaction rollback chứng minh các ràng buộc này.
- Đã xử lý nối bảng GFM xuyên trang khi có đủ chứng cứ: cuối trang là bảng, trang tiếp ngay bắt đầu bằng body cùng schema, STT liên tiếp và định danh có mã; giữ trang của ô và trang header riêng. Không nối theo số cột đơn thuần. Identity ưu tiên ô tên gần cột mã, không lấy nhóm lặp lại hoặc STT làm ngành. Bảng không đủ chứng cứ vẫn không được suy diễn.
- Có đường đọc bảng canonical của **đúng source revision thuộc snapshot** cho legacy index không có fact manifest. Chỉ đọc, kiểm hash/scope/status, không ghi ngược/không vượt facts materialized đã duyệt. DB lỗi là TABLE_EVIDENCE_UNAVAILABLE, không missing giả. Các conflict được đánh giá trên tuple được hỏi, không loại toàn bộ nguồn vì bảng khác có issue.
- Numeric mapping giữ đầu vào thuần số và nhãn lấy từ nguồn; IELTS6.0→9.0 được kiểm trên dữ liệu thật. Không gán năm2026 cho bảng không ghi năm chỉ vì tên văn bản. Câu số liệu rõ ràng bỏ LLM rewrite, vẫn giữ invariant số cho các câu cần rewrite.
- Ruff full và frontend Biome/build/tsc đạt; final BE suite **950 passed/11 lỗi baseline/2 skipped**. Runtime với cấu hình trợ lý/DB thật: RAG lặp hai lượt và DAG trả CNTT2024=16,5,2025=21,5;2026 missing; IELTS6.0=9.0. SSE2026 chỉ gửi no-answer và kết thúc insufficient_context. Không phải browser/auth E2E và không phải chứng minh mọi prose query an toàn.
- Chưa hoàn tất toàn bộ kế hoạch: parser geometry/spans tổng quát, facts văn xuôi/kỳ thời gian, verifier mọi claim và phương thức/phủ định/multiturn nâng cao, cache số liệu tối ưu, bulk draft backfill/worker rollout và full browser E2E. Không tự nâng/xuất bản hai nguồn đang dùng. vLLM chat đã có HTTP404 trong lượt thử rewrite trước khi bỏ gọi model cho exact facts; chưa chỉnh provider hay xác nhận đường chat model đó khỏe.

Người dùng không cần reset DB/upload lại để thử các ca đã đạt. Chạy dev bằng code mới; nâng nguồn cũ qua Ngữ cảnh → tạo bản duyệt → đối chiếu/duyệt → nạp vector/staging → xuất bản khi muốn materialize tập facts mới. Bản đang phục vụ được giữ nguyên đến bước publish có chủ đích.

### Ghi nhận lịch sử đợt đầu #386

- Đã triển khai contract JSONB temporal context/evidence cho facts, tách metadata ngày/năm ban hành/chủ đề/tên file, khôi phục header năm khi có bằng chứng cấu trúc, bảo toàn hàng định danh thuần số.
- RAG dùng quyết định chung cho các thuộc tính số liệu theo năm được hỗ trợ; dựng bảng từ facts đúng ngữ cảnh, đánh dấu thiếu từng năm/thuộc tính, không gọi model để thay số liệu năm khác. DAG chuyển tiếp quyết định và không cho output template nâng missing thành answered. Câu hỏi thời gian dạng prose và quy đổi IELTS chưa được bao phủ toàn bộ bởi gate mới.
- Cache namespace v3-temporal và bỏ qua cache với câu có năm; rewrite kiểm bất biến số và bỏ quy tắc đổi ngày thành ngành. Đây chưa phải toàn bộ invariant về phủ định/phương thức/ngữ cảnh nhiều lượt.
- Studio và Dữ liệu số có cột năm/phương thức; Dữ liệu số có bộ lọc. Ngữ cảnh hiện dùng JSONB sẵn có, chưa tạo migration cột/index truy vấn, editor xác nhận riêng có audit hay chạy bulk backfill.
- Chưa hoàn tất parser span/geometry cho mọi bảng, bảng nối trang, facts văn xuôi, kỳ/khoảng thời gian, xác minh claims prose, preview/cold-warm/SSE E2E, worker rollout và draft backfill. Chưa tự restart, reparse hoặc publish dữ liệu người dùng.
- Ruff và build frontend đạt; 37 tests trọng tâm cuối đạt. Một lần full suite ghi nhận 940 pass/12 fail/2 skip (11 lỗi baseline và lỗi hotline mới đã sửa, được kiểm lại ở suite trọng tâm). Sau đó PostgreSQL không kết nối được, Docker daemon không hoạt động kể cả kiểm ngoài sandbox, nên chưa chạy lại final full/integration/E2E.

Tiếp tục B/C/E phần review/editor/schema/structural evidence và F khi dịch vụ được mở lại. Không coi các phần chưa hoàn tất là đã nghiệm thu chỉ vì guard năm đơn đạt test.

## 1 Mục tiêu và phạm vi

Ngăn trợ lý lấy số liệu của năm này để trả lời cho năm khác hoặc trộn phương thức xét tuyển. Ngày ban hành thuộc metadata bản nguồn; năm áp dụng và các điều kiện của từng số liệu phải được lưu cùng fact. RAG và DAG cùng sử dụng một quyết định về khả năng trả lời, không xem việc có trích dẫn hoặc có con số trong tài liệu là đủ căn cứ.

Kế hoạch áp dụng cho DOCX, PDF có lớp chữ, PDF scan và các nguồn bảng tính khi được đưa vào Kho tri thức. Giữ luồng DOCX qua Docling, PDF chữ qua native parser và trang scan qua OCR phân giải từ ModelOps. Kho tài liệu vẫn chỉ giữ tệp và metadata danh mục, không được ghi ngược kết quả bóc tách.

Không bao gồm đổi embedding model, triển khai BM25, thay toàn bộ kiến trúc DAG, sửa qnu-sso hoặc reset DB. Các ví dụ ngành/năm chỉ dùng làm ca kiểm thử, không gán cứng vào runtime.

## 2 Các vấn đề cần giải quyết

Kiểm thử phiên #383 cho thấy điểm CNTT năm 2025 là 21,5 bị trả thành điểm chính thức năm 2026. Rewrite giữ nguyên năm trong ca đó, nhưng tầng sinh đáp án và guard vẫn cho qua vì con số có trong nguồn. Một ca khác rewrite đổi “ngày” thành “ngành”. Có câu trả lời nói thiếu dữ liệu nhưng vẫn mang trạng thái answered.

Hai nguồn được kiểm tra còn dùng artifact layout-v4, không có structured artifact mới được lưu bền vững. Worker khởi động trước cập nhật #382. Đây là vấn đề phiên bản vận hành cần xử lý khi triển khai; khởi động lại worker không tự sửa lỗi quan hệ năm của câu trả lời.

Nền tảng #382 đã có facts dự thảo, evidence, hash và kiểm tra trước xuất bản, nhưng chưa đủ cho bảng nhiều tầng, định danh hàng thuần số như bảng quy đổi IELTS, ngày ban hành có nhiều ứng viên và xác minh từng khẳng định theo năm/phương thức. Các phần mới phải mở rộng nền tảng này, không tạo pipeline song song.

## 3 Quy định về nơi lưu ngữ cảnh

| Nơi lưu | Dữ liệu chính | Quy tắc |
| --- | --- | --- |
| Metadata của KnowledgeSourceRevision | Ngày ban hành, năm ban hành, năm chủ đề, hiệu lực/phạm vi của văn bản, bằng chứng và trạng thái xác nhận | Không thay thế năm áp dụng của fact |
| Fact dự thảo thuộc revision | Thực thể, thuộc tính, giá trị, năm/kỳ áp dụng, phương thức, đơn vị, điều kiện và bằng chứng | Ngữ cảnh của từng số liệu nằm cùng fact |
| KnowledgeFact trong PostgreSQL | Bản materialize của fact đã đủ điều kiện, gắn source revision/fact set/index revision | Chỉ snapshot đã xuất bản mới phục vụ chatbot |
| Qdrant payload | Source/index IDs, trang/mục, references tới facts và thời gian nội dung đã xác định | Bản sao phục vụ lọc, không phải nguồn sự thật của số liệu |
| Snapshot trong MinIO | Tệp và artifacts dùng đối chiếu | Không phụ thuộc tệp Kho tài liệu còn hay đã bị xóa |

Metadata gốc của snapshot giữ bất biến. Metadata bóc tách, hiệu đính và quyết định xác nhận thuộc bản nguồn Knowledge, có nguồn gốc riêng; không ghi đè để mất dấu metadata người dùng nhập.

## 4 Phân biệt các loại thời gian

| Loại thông tin | Ví dụ | Cách sử dụng |
| --- | --- | --- |
| Ngày ban hành | 15/12/2025 | Ngày của chính văn bản hiện tại |
| Năm ban hành | 2025 | Suy ra từ ngày ban hành đầy đủ hoặc ứng viên năm được xác nhận |
| Năm chủ đề | Tuyển sinh 2026 | Chủ đề văn bản, không phải năm của mọi bảng bên trong |
| Năm áp dụng của fact | Điểm chuẩn 2023 hoặc 2024 | Điều kiện bắt buộc khi hỏi số liệu theo năm |
| Năm học hoặc kỳ | 2025–2026, học kỳ 1 | Lưu dạng kỳ/khoảng có kiểu, không ép thành một năm |
| Thời gian hiệu lực | Từ ngày X, áp dụng từ khóa K48 | Phạm vi áp dụng quy định; khóa K48 không tự chuyển thành năm |
| Ngày của văn bản viện dẫn | Thông tư ban hành năm 2021 | Gắn với văn bản được viện dẫn, không chọn làm ngày văn bản hiện tại |
| Thời gian sự kiện | Đăng ký 02–14/7/2026 | Lưu vào fact sự kiện với mốc bắt đầu/kết thúc |
| Năm gợi ý từ tên file | 2026 trong tên tệp | Ứng viên để kiểm tra, không tự trở thành năm ban hành hoặc năm fact |

Không thu gom tất cả năm thành một danh sách rồi gán cho tất cả chunks/facts. Cần xác định năm thuộc tiêu đề, bảng, nhóm cột, hàng, đoạn hay đối tượng được viện dẫn nào.

## 5 Nhận diện ngày ban hành và đối chiếu tên file

### 5.1 Thu thập và phân loại ứng viên

1. Đọc trang đầu và các khối thể thức từ artifacts đã bóc tách. Không OCR lại chỉ để mở Studio hoặc đọc metadata.
2. Phân tích biểu thức ngày hợp lệ bằng cấu trúc ngày/tháng/năm, kiểm lịch thực tế và chuẩn hóa Unicode NFC. Giữ nguyên chuỗi gốc bên cạnh giá trị chuẩn hóa.
3. Gắn mỗi ứng viên với page/block/offset và bbox nếu parser có tọa độ thật. Thiếu bbox vẫn lưu evidence văn bản, không tạo tọa độ giả.
4. Phân loại vai trò dựa trên bố cục, thứ tự đọc và cấu trúc cú pháp: dòng thể thức, trích dẫn văn bản khác, thời hạn/sự kiện, hiệu lực. Không dùng vị trí cố định theo A4 hoặc lấy ngày đầu tiên trong 3.500 ký tự.
5. Phân tích tên file và tiêu đề để tạo ứng viên riêng. Tách năm chủ đề khỏi năm ban hành; không lấy năm lớn nhất hoặc năm hiện tại làm mặc định.

Quy tắc tổng quát phải được dùng trước. Với định dạng không đủ rõ, có thể dùng extraction có schema qua ModelOps để đề xuất vai trò và evidence; đầu ra model vẫn cần validation, không được tự nhận là dữ liệu đã xác nhận. Không mở rộng từ điển viết tay để vá từng tên ngành hoặc lỗi OCR.

### 5.2 Quyết định chọn giá trị

- Dòng ngày đầy đủ của văn bản hiện tại là nguồn tự động ưu tiên. Ngày trong phần căn cứ không được cạnh tranh như ngày ban hành của nguồn.
- Metadata do người dùng xác nhận có actor/time/evidence được giữ như quyết định hiệu đính. Nếu mâu thuẫn với nội dung, hiển thị conflict thay vì âm thầm ghi đè.
- “ngày … tháng … năm 2026”: lưu ứng viên năm với precision=year, ngày đầy đủ là null; chỉ dùng như năm ban hành đã xác nhận khi chính sách/evidence hoặc người duyệt đủ điều kiện. Không dựng ngày 01/01/2026.
- Tên file “Tuyển sinh 2026” và ngày ban hành 15/12/2025 không nhất thiết mâu thuẫn: năm chủ đề 2026, năm ban hành 2025.
- Tên file năm 2024 nhưng dòng ban hành năm 2025: giữ cả hai ứng viên, ưu tiên nội dung đã xác định đúng vai trò, đánh dấu tên file để kiểm tra.
- Không có ứng viên đủ rõ: metadata là unknown, không chặn mọi việc bóc tách. Chỉ chặn câu hỏi/claim cần ngày đó hoặc đưa trường này vào hàng chờ kiểm tra.
- Tài liệu đóng tập gồm quyết định, quy chế và phụ lục: tạo phạm vi tài liệu con/section khi đủ chứng cứ; ngày của quyết định và hiệu lực quy chế không bị nhập làm một. Nếu chưa xác định được ranh giới thì đánh dấu ambiguous.

### 5.3 Contract metadata đề xuất

Mỗi trường thời gian lưu value, precision, role, evidence, extraction method/version và trạng thái unknown/proposed/verified/conflict. Confidence chỉ lưu khi có điểm đo thật; trạng thái được duyệt không thay cho confidence.

Ngày ban hành chuẩn hóa dạng ISO date nếu đầy đủ. Năm ban hành có thể nullable, năm chủ đề có thể nhiều giá trị có phạm vi riêng. Giữ ứng viên không được chọn để cán bộ đối chiếu.

## 6 Fact phải chứa đầy đủ điều kiện của số liệu

### 6.1 Contract fact đề xuất

| Nhóm trường | Nội dung |
| --- | --- |
| Identity | Fact ID ổn định, entity ID/code/name, attribute ID/label |
| Value | Giá trị nguyên văn, giá trị chuẩn hóa có kiểu, đơn vị, khoảng/so sánh nếu có |
| Temporal context | Loại thời gian year/academic_year/date_range/period/unknown, giá trị, vai trò và evidence |
| Qualifiers | Phương thức xét tuyển, đối tượng, bậc đào tạo, cơ sở, ngành/chương trình và điều kiện khác chỉ khi nguồn cung cấp |
| Provenance | Source revision, fact set/version/hash, bảng/hàng/cột, đường dẫn header, trang, raw excerpt/cells và references tới regions |
| Review | Proposed/verified/ambiguous/rejected, issues, actor/time/decision/comment |

Năm, phương thức và điều kiện là trường của fact, không chỉ là đoạn văn nằm trong attribute_name. Raw data giữ đầy đủ bằng chứng để tái kiểm tra. Các khóa nghiệp vụ tổng quát được định nghĩa qua schema/taxonomy quản lý, không gán cứng model, ngành hoặc năm.

Không nhận diện thực thể bằng quy tắc “ô có chữ đầu tiên” cho mọi bảng. Hàng có identity thuần số vẫn hợp lệ: IELTS6.0 là đầu vào của một quan hệ quy đổi, không phải hàng bị loại bỏ vì thiếu chữ.

### 6.2 Bảng nhiều tầng và ô gộp

1. Giữ grid, row_span/column_span, header/body, cell IDs và source spans từ parser. Dùng geometry và cấu trúc đã có để tạo cây tiêu đề.
2. Mỗi cột lá nhận header_path riêng, ví dụ “2024 → Điểm trúng tuyển → Xét học bạ”. Chỉ lan truyền năm bên trong span của ô cha.
3. Ghép identity của hàng với thuộc tính/ngữ cảnh của cột và giá trị ô. Chỉ tiêu, số nhập học, điểm THPT và điểm học bạ là các thuộc tính/quan hệ khác nhau.
4. Ô rỗng giữ null và không tạo giá trị0. Số0 thật vẫn là0. Dấu gạch hoặc ký hiệu đặc biệt giữ nguyên để phân giải theo chú thích có bằng chứng.
5. Với GFM Markdown đã mất span, chỉ khôi phục khi độ rộng và quan hệ header có đủ bằng chứng. Không forward-fill năm tùy ý qua các nhóm cột thiếu nhãn. Nếu không chắc, dùng parser artifact hoặc yêu cầu duyệt.
6. Bảng nối trang phải có dấu hiệu tương thích schema, thứ tự cột, vị trí/tiêu đề và identity hàng. Không nối hai bảng chỉ vì số cột giống nhau. Kế thừa năm chỉ sau khi xác nhận cùng logical table.
7. Caption, dòng trước bảng và chú thích có thể cung cấp năm/phương thức, nhưng phải có phạm vi rõ. Header trực tiếp mâu thuẫn caption là issue cần kiểm tra, không tự chọn một bên.

Ví dụ đối chiếu ảnh người dùng, ngành Quản lý Giáo dục mã7140114:

| Năm fact | Thuộc tính | Phương thức | Giá trị |
| --- | --- | --- | --- |
| 2023 | Chỉ tiêu | Không ghi riêng trong ô | 50 |
| 2023 | Số trúng tuyển nhập học | Không ghi riêng trong ô | 27 |
| 2023 | Điểm trúng tuyển | Thi tốt nghiệp THPT | 15 |
| 2023 | Điểm trúng tuyển | Xét học bạ | 18 |
| 2024 | Chỉ tiêu | Không ghi riêng trong ô | 47 |
| 2024 | Số trúng tuyển nhập học | Không ghi riêng trong ô | 50 |
| 2024 | Điểm trúng tuyển | Thi tốt nghiệp THPT | 22,5 |
| 2024 | Điểm trúng tuyển | Xét học bạ | 18 |

Không gán phương thức THPT cho chỉ tiêu chỉ vì cột điểm THPT ở bên cạnh. Không chuyển các facts này sang2026 dù chúng nằm trong tài liệu tuyển sinh2026.

### 6.3 Ngữ cảnh trong phần văn xuôi

Phân đoạn theo heading/paragraph, phân tích vai trò của năm và phạm vi quan hệ. Ví dụ “năm2024 đạt X, năm2025 đạt Y” tạo hai facts có evidence riêng; “từ2024 đến2026” giữ interval, không biến thành ba giá trị độc lập nếu nguồn không nói vậy.

Ngày của văn bản viện dẫn không áp cho nội dung hiện tại. Quy tắc có hiệu lực từ ngày X không mặc nhiên có ngày hết hiệu lực. Chỉ tính toán/tổng hợp số liệu khi câu hỏi yêu cầu, đơn vị và phạm vi tương thích, kèm công thức và evidence đầu vào.

## 7 Lưu trữ phiên bản và migration an toàn

Draft fact set tiếp tục thuộc source artifact/revision, tạo trước review. Một tập facts đã kiểm tra được reuse khi thay embedding. KnowledgeFact phục vụ tra cứu là bản materialize gắn index revision; không sửa facts của chỉ mục đang hoạt động tại chỗ.

Đề xuất migration cộng thêm các trường truy vấn nullable cho entity_code, attribute_code, applicability_year, temporal_type, admission_method và unit; qualifiers/evidence chi tiết giữ JSONB có schema version. Với năm học/khoảng, dùng temporal context có kiểu, không ép applicability_year thành năm bắt đầu. Kiểm inventory trước khi chốt tên trường để tận dụng fields hiện có.

Tạo index theo collection/index revision, entity, attribute, year và method dựa trên truy vấn thực tế; không tạo tất cả tổ hợp index. Identity chống trùng gồm fact set, đối tượng, thuộc tính, temporal context và qualifiers. Conflict trong cùng ngữ cảnh phải được giải quyết bằng evidence/review, không chọn bản có năm ban hành mới hơn một cách máy móc.

Dữ liệu legacy không biết năm là null, không backfill bằng năm tên file hoặc ngày upload. Migration không reset/drop dữ liệu. Backfill xử lý theo lô ở draft revision, có báo cáo và khả năng chạy lại an toàn. Sửa metadata ảnh hưởng RAG/filter cũng phải nâng version và đồng bộ payload/cache, không chỉ thay UI.

## 8 RAG và DAG dùng chung quyết định khả năng trả lời

### 8.1 Phân tích câu hỏi

Tạo constraints có kiểu: entity, attribute, temporal context, method, qualifiers và provenance của từng constraint. Năm người dùng nói rõ có ưu tiên hơn lịch sử. “Ngành này”, “năm đó” chỉ resolve khi lịch sử có một đối tượng phù hợp; nếu mơ hồ hỏi lại.

Không dùng năm hiện tại làm năm mặc định. “Mới nhất” nghĩa là kỳ áp dụng mới nhất có evidence phù hợp trong snapshot đã xuất bản, không phải ngày upload mới nhất hoặc fact thuộc văn bản mới nhất. Câu hỏi thiếu phương thức được hỏi lại hoặc trình bày các phương thức có nhãn rõ, không lấy một số duy nhất tùy ý.

### 8.2 Chọn evidence trước khi sinh đáp án

Tra PostgreSQL facts trong active snapshot với đúng entity/attribute/year/method. Facts verified đủ điều kiện được dựng đáp án số liệu bằng template có kiểu; LLM chỉ diễn đạt phần không làm thay đổi giá trị/ngữ cảnh. Nếu không có SQL fact, kiểm table/paragraph evidence tương thích đã review; thiếu fact không chứng minh tài liệu không có thông tin.

Không có evidence đầy đủ thì trả missing/ambiguous. Không đưa facts khác năm làm đáp án thay thế. Nếu người dùng muốn tham khảo lịch sử, tách chúng thành mục có nhãn năm rõ ràng.

Qdrant hỗ trợ tìm đoạn liên quan và filtering bằng metadata đã được chứng minh; chunk chứa nhiều facts/năm vẫn cần chọn fact cụ thể. Không lấy năm trong query làm evidence cho năm của con số, không dùng embedding similarity hoặc reranker score thay cho kiểm tra ngữ cảnh.

### 8.3 Contract trả lời dùng chung

Backend tạo AnswerDecision gồm supported/missing/ambiguous/conflict, requested constraints, matched fact/evidence IDs, claim bindings và phần điều kiện còn thiếu. Lỗi hạ tầng là error riêng, không chuyển thành “không có dữ liệu”.

AskResponse và DAG node dùng cùng decision; tương thích trạng thái UI hiện có nhưng thêm reason/coverage. So sánh nhiều năm có thể trả bảng một phần với từng hàng supported/missing, không vì thiếu một năm mà bịa đủ bảng hoặc loại bỏ các năm đã có.

Ví dụ CNTT2026: “Trong kho tài liệu đã xuất bản, mình chưa tìm thấy căn cứ về điểm chuẩn chính thức ngành CNTT năm2026.” Không nói trường chưa công bố nếu kho hiện tại không chứng minh điều đó. Điểm2025=21,5 chỉ được nêu riêng nếu có nhu cầu và evidence.

### 8.4 Kiểm tra từng claim và streaming

Trước khi gửi, đối chiếu tuple thực thể/thuộc tính/thời gian/phương thức/đơn vị/giá trị với evidence thuộc đúng revision. Trích dẫn phải chứng minh claim đó, không chỉ cùng tên nguồn. Kiểm số xuất hiện trong text chỉ là kiểm phụ, không phải gate chính.

DAG không được sinh lại giá trị hay nâng missing thành answered sau gate. Không dựa vào một danh sách câu từ chối để xác định decision.

Với SSE, dựng đáp án số liệu đã kiểm tra trước rồi stream. Đáp án prose do model sinh phải giữ trong buffer hoặc chỉ stream phần đã xác minh; không gửi khẳng định sai trước rồi mới đổi trạng thái done. Khi error/missing, UI phải hiển thị trạng thái đúng và không gắn citation sai cho một đáp án tưởng như đã đạt.

## 9 Rewrite cache và hiệu năng

- Rewrite giữ bất biến năm/interval/identity/method/negation/query intent. Câu gốc và constraints là nguồn kiểm chứng; không cho model tự đổi “ngày” thành “ngành” hoặc2026thành2025. Không đạt invariant thì dùng original query, lưu lý do.
- Cache key thêm phiên bản grounding contract/extractor/taxonomy, constraints đã chuẩn hóa, tenant/workspace, source snapshot/index epoch và model policy. Cached answer được kiểm claim bindings; legacy cache không reuse qua contract mới.
- Chỉ cache answered có claim/evidence hợp lệ. Missing có thể dùng TTL ngắn theo chính sách và phải mất hiệu lực khi nguồn xuất bản thay đổi. Không xóa toàn Redis hoặc cache kho khác.
- Exact facts dùng truy vấn có index và renderer, không thêm model judge cho mỗi fact rõ ràng. Model verifier chỉ hỗ trợ prose/ambiguity và phân giải động qua ModelOps.
- Theo dõi latency query/rewrite/retrieval/verification, cache hit và số lần model gọi. Đo p50/p95 với cả cache nóng và lạnh; không coi cache hit là fresh inference.

## 10 Studio và Dữ liệu số

Studio hiển thị ba phần riêng: thông tin ban hành/chủ đề của nguồn, facts dự thảo có ngữ cảnh và evidence đối chiếu ảnh/Markdown. Mỗi ngày/năm có nguồn phát hiện, precision, trạng thái và thao tác sửa/xác nhận.

Tab Dữ liệu số hiển thị ngành/mã, thuộc tính, năm hoặc kỳ áp dụng, phương thức, giá trị/đơn vị, nguồn/trang và trạng thái. Cho lọc năm và phương thức; đồng thời phân biệt rõ đang xem facts dự thảo hay đang phục vụ chatbot. Ngữ cảnh không bị giấu hoàn toàn trong JSON chi tiết.

Cán bộ sửa fact/metadata tạo revision hoặc fact set mới có audit actor/time/reason. Evidence không đủ thì không cho xác nhận kiểu “100% đúng” chỉ từ confidence. Sau hiệu đính phải invalidation các dẫn xuất liên quan; không thay serving pointer đến khi staging và kiểm tra hoàn tất.

Tái sử dụng primitives/admin helpers có sẵn. Không khôi phục tab Cấu hình lớn đã bỏ hoặc xây màn hình monolithic mới chỉ để thêm ngữ cảnh thời gian.

## 11 Các hạng mục triển khai và điều kiện hoàn thành

Các hạng mục là thứ tự phụ thuộc, không phải bắt buộc tách thành sáu phiên chat.

| Hạng mục | Công việc | Điều kiện hoàn thành |
| --- | --- | --- |
| A Contract và regression | Inventory schema/artifact/runtime; chốt temporal/fact/AnswerDecision; viết ca lỗi2026→2025 trước sửa | Regression fail đúng nguyên nhân; không hardcode năm/ngành |
| B Metadata thời gian | Candidate extraction, vai trò ngày, filename hints, conflict/precision/evidence; tích hợp Studio | Không lấy ngày viện dẫn, không tự điền ngày trống, giữ nguồn gốc |
| C Facts có ngữ cảnh | Header tree/spans, bảng nối trang, văn xuôi, identity thuần số; migration nullable/index và review |2023/2024/2025, THPT/học bạ/IELTS tách đúng; không đoán missing |
| D Common answerability | Query constraints, facts-first, claim gate, common RAG/DAG response, verified SSE | Missing2026 bị chặn trước khi gửi; các năm có dữ liệu vẫn trả đúng |
| E Rewrite cache và UI | Constraint invariants, contract version cache, evidence UI/filter/edit/audit | Multi-turn/cached/streamed không mất năm; UI không hiểu nhầm confidence |
| F Rollout và E2E | Restart worker có kiểm phiên bản; nâng artifact ở draft; preview/test/bảo toàn serving và publish có đối soát | Đạt matrix dưới đây và có evidence từng bước; không reset DB |

Phạm vi code dự kiến khi được duyệt: Knowledge models/schemas/services/source_artifact/source_ingestion/table reconstruction/facts/vector generation; RAG query analysis/facts/service/citation guard/cache; DAG rewrite/knowledge/guard/output; Studio/facts tab/API types. Tách service/hàm có trách nhiệm riêng, router mỏng, không tạo file quái vật. Kế hoạch này chưa sửa các tệp đó.

## 12 Nâng cấp dữ liệu đã có mà không xóa tải lại

1. Kiểm job đang chạy; restart worker theo quy trình graceful để nhận code/version mới, không kill ngang job đang xử lý.
2. Dùng snapshot, canonical parser artifacts và Markdown đang lưu để tạo revision/fact set mới ở draft. Parser artifact có span được ưu tiên; nếu Markdown mất bằng chứng cấu trúc, chỉ reparse nguồn cụ thể khi cần và có phạm vi rõ.
3. Cán bộ đối chiếu metadata/ngữ cảnh facts; các issues phải được xử lý hoặc ghi nhận quyết định duyệt hợp lệ.
4. Nạp staging từ bản đã kiểm tra. Đổi embedding không OCR lại; thay facts không mặc nhiên cần sinh lại mọi vector nếu content không đổi, nhưng phải tạo manifest nhất quán. Tận dụng reuse khi chứng minh được hash/model/space/source scope tương thích.
5. Preview chỉ mục dự thảo và kiểm cả policy của trợ lý/DAG; preview ModelOps mặc định không được coi là đã test chính sách trợ lý.
6. Publish CAS pin vector/facts/source cùng manifest; giữ bản đang phục vụ nếu build/gate thất bại. Nếu không đủ khả năng dựng candidate mới an toàn thì chưa publish, không sửa active tại chỗ.
7. Cache đổi namespace/version hoặc invalidate phạm vi cần thiết. Rollback chỉ khi toàn bộ artifact/facts/vector còn retained và tương thích.

Không đổi hoặc xóa tệp ở Kho tài liệu; không yêu cầu người dùng upload lại chỉ để đổi cấu trúc facts.

## 13 Ma trận kiểm thử và tiêu chí nghiệm thu

| Nhóm | Ca kiểm thử | Kết quả bắt buộc |
| --- | --- | --- |
| Ngày ban hành | Trang đầu có dòng thể thức2025 và nhiều căn cứ2021/2024 | Chọn ngày văn bản hiện tại, giữ ngày viện dẫn riêng |
| Ngày không đầy đủ | “ngày … tháng … năm2026” | Ngày null, năm ứng viên có precision và trạng thái, không01/01 |
| Filename | Tên tuyển sinh2026, ngày ban hành2025 | Năm chủ đề2026, năm ban hành2025, không trộn |
| Nhiều nguồn | Metadata đã duyệt mâu thuẫn nội dung/tên file | Hiển thị conflict và audit, không âm thầm overwrite |
| Bảng2023/2024 | Ảnh Quản lý Giáo dục với THPT/học bạ | Đúng15/18và22,5/18, chỉ tiêu50/47, nhập học27/50 |
| Bảng nối trang | Trang sau chỉ có body, có/không đủ evidence cùng bảng | Kế thừa đúng nếu được chứng minh; không rõ thì ambiguous |
| Nội dung2024/2025 | CNTT2024=16,5;2025=21,5 | Cả hai facts có year riêng và ô nguồn riêng |
| Năm không có | CNTT2026 hoặc so sánh2024–2026 | Không gán21,5cho2026; bảng so sánh đánh dấu năm thiếu |
| Bảng thuần số | IELTS6.0→9.0 và7.0→10.0 | Không bỏ hàng6.0 và không lấy10.0thay9.0 |
| Thời gian khác | Năm học2025–2026, hiệu lực theo khóaK48, mốc sự kiện | Giữ kiểu/phạm vi, không biến thành một năm chung |
| Missing/null | Ô rỗng, số0, missing method, duplicate conflicts | Không điền0choô rỗng, không tự chọn method/conflict |
| Multi-turn | “ngành này”, “năm đó”, đổi năm trong câu tiếp | Resolve có căn cứ hoặc hỏi lại; năm mới trong câu hiện tại ưu tiên |
| Rewrite | Câu hỏi ngày, năm, phủ định và mã ngành | Giữ invariant hoặc dùng câu gốc |
| Cache | Đáp án cũ sai năm, cache nóng/lạnh, đổi source/policy | Cache không vượt guard/version; kết quả đúng như cold path |
| Streaming | Unsupported claim model sinh trước done | Không gửi số liệu sai rồi mới từ chối |
| Scope/lifecycle | Tenant khác, nguồn paused, draft chưapublish, bản cũ | Không truy cập/serving ngoài active snapshot |
| Resilience | DB/AI/Redis lỗi, build fail, race publish | Lỗi thật hoặc missing đúng nghĩa, giữ serving pointer, không fake success |

Kiểm thử high-risk viết regression trước; không chạy full suite sau mỗi sửa nhỏ. Sau batch tích hợp: Ruff và full BE suite, scoped Biome/build TypeScript cho FE, rồi browser E2E với file thật và câu hỏi có đáp án/thiếu đáp án. Báo riêng các lỗi baseline, không sửa test hoặc mock production để đạt pass giả.

Các ca số liệu nguy cơ cao trong matrix phải qua cả RAG và DAG, cold/warm cache và streaming. Lưu trace, matched evidence, phiên bản worker/artifact, câu hỏi/constraints, response và đánh giá thủ công. Bộ đánh giá mở rộng50câu/Ragas bổ sung sau matrix, không thay cho kiểm tra chính xác từng số liệu và năm.

Hoàn tất chỉ khi không có sai year/method/value trong tập nghiệm thu, missing-data decision đúng và không gây regression scope/publish. Không tuyên bố mọi câu hỏi tương lai đều không thể hallucinate.

## 14 Tài liệu liên quan

- [Kế hoạch tách Kho tài liệu và nạp tri thức](12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md) là nền tảng domain/versioning.
- [Kết quả test hai nguồn](../nhat_ky/2026-10-12_phien_383_test_rag_dag_hai_nguon_moi.md) ghi nhận lỗi thực tế và trace.
- [Đề xuất chống nhầm năm](../nhat_ky/2026-10-12_phien_384_de_xuat_chan_nham_nam_so_lieu_rag.md) là phân tích ban đầu; kế hoạch này bổ sung bảng2023/2024 và vị trí lưu ngữ cảnh trong từng fact.
