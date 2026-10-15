# Triển khai RAG đúng phạm vi và đủ ý

## Kết quả chính

Bản sửa bổ sung ngữ cảnh ngành–mục con từ chính nguồn đã xuất bản, kiểm tra phạm vi của câu trích và giữ bằng chứng cho từng ý hỏi. Không sửa Word, DB nghiệp vụ, cấu hình trợ lý, model, timeout, vector hay publication; không đưa DAG trở lại chatbot.

Kiểm chứng trực tiếp đã thấy các cải thiện:

- Sư phạm Toán: trả 4 năm và các hướng việc làm thuộc Sư phạm Toán; không dùng đoạn Toán ứng dụng ở lượt thử này.
- Kỹ thuật phần mềm: trả 4,5 năm và các nhóm công việc, khởi nghiệp, nghiên cứu/học tiếp.
- Phương thức xét tuyển: đủ 5 phương thức của cẩm nang2025, giữ loại trừ sư phạm ở học bạ và ĐGNL ĐHQG TP.HCM.
- Mầm non: trả `(Toán, Văn, NK GDMN)` từ record của chính cẩm nang, không bị false-partial do tiền tố “ngành”.
- Khoa học vật liệu: trả `7440122`, 4 năm, Cử nhân từ cẩm nang; không dùng mã9440122 sau đại học trong lượt cuối.

Đây là kiểm chứng theo từng lượt và từng phiên bản, **không phải kết quả đạt đủ20/82 câu hay độ chính xác chung**. Hai kế hoạch chạy20 đều dừng khi gặp lỗi dịch vụ; nhánh tham khảo lịch sử gặp `EVIDENCE_TIMEOUT` tại `historical_verification` sau90giây. Không tăng timeout, đổi model hoặc biến lỗi này thành “không có dữ liệu”.

## Thay đổi thuật toán

### Ngữ cảnh bản ghi và mục con

`evidence_hierarchy.py` nhận diện mẫu bản ghi bằng các tiêu đề có lược đồ trường lặp lại: nhãn trước dấu hai chấm, cùng độ sâu và ít nhất hai nhãn chung giữa các bản ghi. Không dùng danh sách tên ngành hay từ điển đáp án.

Mục con lặp được giữ dưới tên bản ghi qua marker Trang/Page. Tiêu đề duy nhất chưa phân loại hoặc tiêu đề cấp cao hơn kết thúc phạm vi suy ra; nguồn không có mẫu rõ giữ trạng thái chưa phân loại. `record_label`, `record_path` và ID tiêu đề là ngữ cảnh truy xuất, không tự trở thành fact hoặc xác nhận năm dữ liệu.

Đây là lớp bổ sung khi đọc. Canonical text/span/hash, unit manifest và metadata đã pin không bị sửa; chưa thay đổi embeddings hay tự ghi ngược outline vào nguồn. Vì vậy phiên này không yêu cầu nạp lại vector. Khi muốn cải thiện chính embedding/index ở lần ingestion sau, cần một revision mới và đối soát riêng.

### Chọn và đóng gói bằng chứng

BM25 có thêm đường dẫn bản ghi trong phần context với trọng sốcontext hiện có. Chọn mục con trong bản ghi đích theo facet được hỏi, dùng tóm tắt ghép từ source để xếp hạng nhưng **chỉ trả các block gốc để trích dẫn**. Mục không có tín hiệu facet không được giữ ưu tiên; ngữ cảnh đúng bản ghi được đóng gói trước các đoạn liên quan chung. Không tăng context_limit/max_context_chars.

Tiêu đề tổng kết bôi đậm có thể dẫn tới danh sách đánh số liền kề để lấy đủ thành viên. Nhóm thuộc tính key/value ngay dưới tên bản ghi không bị hiểu thành yêu cầu liệt kê toàn bộ tín chỉ/bằng cấp khi người dùng chỉ hỏi thời gian và việc làm. Những danh sách chính sách chưa phân loại vẫn giữ kiểm tra bao phủ cũ.

### Phạm vi và đầy đủ câu trả lời

- Planner có `education_level` và `requested_topics` tùy chọn, giữ tương thích hợp đồng cũ. Các mục này là nhãn ngữ nghĩa, không phải danh sách giá trị cố định.
- Câu trích thuộc bản ghi khác bị chặn trước khi gọi verifier khi đã xác định được bản ghi đích. Một reference đúng ngành không cứu được primary body sai ngành.
- Verifier/audit được yêu cầu kiểm tra primary body, trình độ, thuộc tính và từng facet trong **public claim text**, không chỉ nhìn citation đính kèm. Thiếu một facet đã khai báo vẫn partial; metadata không rõ không được coi là chứng minh tương thích.
- Trích dẫn được gắn thêm tiêu đề bản ghi có raw span thật, cùng immutable source, không chỉ dùng nhãn suy ra.
- Fact dùng ngữ cảnh trang của hàng/header, không mượn section đoạn cuối tài liệu. Có nhiều section hoặc không tìm được vị trí thì `location_ambiguous=true`; không tự sửa fact đã duyệt.
- Proposal chọn passage nhiều nguồn được tách thành claim extractive theo từng source rồi bind/verify riêng. Guard cấm mượn năm/điều kiện giữa nguồn vẫn giữ.
- Bôi đậm không làm mất giá trị: mã ngành dạng `**MÃ NGÀNH: ...**`, field có nhãn/giá trị, tổng có số vẫn được chọn để kiểm chứng. Tiêu đề thuần chữ/năm vẫn là context.
- Row-scope chỉ chuẩn hóa tiền tố một từ của tên đầy đủ trong câu hỏi thuộc tính cá nhân; không chuẩn hóa câu so sánh, nhóm hoặc khớp tên một phần.

### Tham khảo năm cũ và lỗi model

Nhánh lịch sử giữ quy tắc năm449: ưu tiên năm hỏi; năm trước kiểm chứng riêng; chỉ trả partial/HISTORICAL_REFERENCE_ONLY có nhãn, không đổi requested year hay citations. Bổ sung lọc phạm vi bản ghi khi tìm năm và diagnostics cho các điểm dừng: không đủ điều kiện, không tìm năm trước, không có evidence, claim không bind được, chưa kiểm chứng đầy đủ, hoặc reference đã xác minh. Giữ deadline chung và lỗi RFC7807 thực.

Hai probe ban đầu gặp502 do model ghi nhãn `requirement` quá200ký tự. Sửa phản hồi JSON để chỉ rõ loại lỗi/giới hạn cho lần repair vốn có; nhãn mô tả điều kiện được cho phép tối đa1000ký tự trong cả hai hợp đồng. **Không cắt quote, không nới phép kiểm chứng, không thêm vòng retry**, không thay max_tokens. Lỗi lặp vẫn là EVIDENCE_MODEL_CONTRACT_INVALID.

## Các lượt kiểm chứng trực tiếp

| Artifact | Thực hiện | Kết quả và giới hạn |
| :--- | :--- | :--- |
| admissions_eval452_probe6.json | Kế hoạch6; đã thử2 | 2001supported,2002HTTP502 contract; dừng, không suy ra các câu chưa chạy. |
| admissions_eval452_camnang20.json | Kế hoạch20; đã thử2 | 2001missing,2002HTTP502 contract ở bản trung gian. |
| admissions_eval452_release20.json | Kế hoạch20; đã thử6 | 2001/2004/2005supported;2002/2003missing;2006HTTP504. 13canonical citations DB khớp. Không là acceptance20. |
| admissions_eval452_final6.json | Kế hoạch6; đã thử5 | 2002/2102supported;2105/2108partial trước sửa scalar/row-scope cuối;2112HTTP504 historical_verification;2113chưa thử.18canonical+1factcitation DB khớp. |
| admissions_eval452_scalar2.json | Bản cuối,2câu | 2105/2108HTTP200supported; đã đọc đúng nội dung,7canonicalcitations DB khớp; runtime/config/publication trước–sau không đổi. |

Mỗi artifact giữ fingerprint riêng; không gộp các phiên bản trung gian thành thống kê accuracy. Bản cuối của scalar2 có runtimefingerprint `d973eb60f052a7e171b6d8c3d2dfd1144171b9362279c76063789d07b97c9742`. Snapshot không đổi `6180f8f51b791da886a2`,21nguồn; đúng DOCXhash e6ddb2c… với1257 retrievablepoints/parityđạt.

## Kiểm thử và bước tiếp theo

Nhóm regression RAG đạt160ca, gồm21ca mới cho cấu trúc, nhầm bản ghi, năm/nguồn, đủfacet, danh sách/thuộc tính, giá trị bôi đậm, row-scope, lỗi model và trace lịch sử. Fullsuite cuối: **1329pass,11fail,15skip,0errors**,195,57giây; tên11fail trùng baseline449, không có lỗi RAG mới. Ruff toàn Backend đạt với cảnh báo ACL ở một số thư mục testtemp cũ. Không có thay đổi FE nên không chạy Vite.

Khi luồng inference phản hồi ổn định, chạy lại20câu trên một fingerprint, đối soát câu trả lời lẫn citations rồi mới full82. Chưa nghiệm thu latency, toàn bộ13lỗi của báo cáo451 hoặc tham khảo2025cho2026. Những bản ghi/heading không nhận diện được vẫn cần kiểm chứng ngữ nghĩa; không tự ép chúng vào một ngành. Cần giữ kiểm thử âm chống sai ngành, sai trình độ và dùng năm cũ như năm hiện tại.
