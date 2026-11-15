# Kế hoạch mở rộng QNU: soạn thảo, học liệu và hỗ trợ công việc

Ngày: 15/11/2026. Trạng thái: **KẾ HOẠCH ĐỀ XUẤT — chưa triển khai chức năng**.

## 1. Mục tiêu và phạm vi

Phát triển QNU thành nền tảng tri thức và hỗ trợ công việc cho nhà trường. Ba loại trợ lý phục vụ ba nhu cầu: hỏi đáp có nguồn; soạn thảo theo mẫu; tạo câu hỏi từ học liệu. Người dùng làm việc bằng hội thoại, mẫu công việc và vùng kết quả có thể chỉnh sửa; không cần cấu hình prompt, token, metadata hoặc provider.

Kế hoạch này giữ đầy đủ các hướng đã trao đổi: kho tri thức; công cụ tài liệu; báo cáo và chất lượng; học liệu và học tập; quy trình công việc; kết nối dữ liệu. Hai trợ lý mới là ưu tiên triển khai trong lộ trình đó.

Agent là khả năng thực hiện một công việc qua nhiều bước ngay trong Trợ lý AI. Người dùng giao việc bằng hội thoại, theo dõi tiến độ và mở lại kết quả đã lưu. P2 thí điểm agent soạn thảo nội bộ, P3 dùng lại cơ chế điều phối để tạo câu hỏi. Hướng dẫn tuyển sinh công khai theo từng bước là một phần mở rộng sau hai đợt thí điểm.

Chỉ lập kế hoạch và ghi tài liệu trong phiên này. Không sửa BE/FE, migration, cấu hình mô hình; không restart, reindex, deploy, push hoặc chạy benchmark 100 câu.

## 2. Căn cứ hiện trạng và giới hạn khảo sát

Đã đọc PROJECT_CONTEXT, Git status/diff stat, schema trợ lý và các hợp đồng tác vụ/công khai, danh sách domain, sidebar V2 và quy định UI/kiểm chứng. Đây là khảo sát có phạm vi để lập kế hoạch, chưa phải audit toàn hệ thống hoặc xác nhận runtime.

| Bằng chứng | Ý nghĩa đối với kế hoạch |
|---|---|
| `backendV1/qnu/domains/assistants/schemas.py`: `AssistantConfig` có collection bắt buộc, persona, provider và chính sách RAG; chưa có trường loại trợ lý | Cần bổ sung loại trợ lý và cấu hình nghiệp vụ; không thể chỉ đổi persona để có sản phẩm soạn thảo/tạo đề đầy đủ |
| Các domain `knowledge`, `ocr`, `rag`, `modelops`, `operations`, `conversations`, `evaluation`, `lifecycle`, `publications` đã có | Ưu tiên tái sử dụng dịch vụ; không xây lại worker, bộ bóc tách hoặc cổng gọi model |
| `operations/schemas.py` có các loại job hiện hành, chưa có job soạn thảo/tạo câu hỏi riêng | Cần bổ sung loại job, trạng thái và hành động tương ứng khi triển khai |
| `frontendV2/src/layouts/app-sidebar.tsx` đang có Tổng quan, Kho tri thức, Trợ lý AI, Hội thoại, Tác vụ, Nhà cung cấp, Cài đặt | Mở rộng từng bước, tránh thêm nhiều menu cho cùng một hành vi |
| Diff hiện tại có công việc kênh công khai, SSO, đóng gói và các thay đổi chưa commit | Không sửa chồng phần đang làm; phải đọc lại diff khi bắt đầu từng giai đoạn |
| Báo cáo phiên 970 ghi Q41 chưa ổn định; phiên 971 chưa nghiệm thu deploy/SSO production | Đây là trạng thái báo cáo lịch sử, chưa chạy lại trong phiên này. Không coi RAG hoặc production đã đạt toàn bộ |

Tệp tham chiếu: [ngữ cảnh](../memory/PROJECT_CONTEXT.md), [kiểm chứng G3](../nhat_ky/2026-11-14_phien_970_kiem_chung_doc_lap_g3.md), [kênh công khai](../nhat_ky/2026-11-15_phien_971_kenh_chatbot_cong_khai.md).

## 3. Các quyết định thiết kế đề xuất

1. Ba loại trợ lý: `knowledge_qa`, `document_drafting`, `question_authoring`. Tên kỹ thuật chỉ nằm trong contract; UI dùng tiếng Việt.
2. Giữ hành vi trợ lý cũ mặc định là hỏi đáp. Không đổi binding, history, context window hoặc cấu hình model hiện có chỉ vì thêm tính năng.
3. Model giải quyết qua ModelOps, dùng mặc định toàn hệ thống. Không thêm mặc định model riêng từng đơn vị; không hardcode Qwen/model ID trong nghiệp vụ. Kiểm chứng live bằng model hệ thống đã được phép dùng, ghi rõ model/cấu hình tại lúc chạy.
4. Workspace vẫn là biên giới quyền. Mọi API tài liệu, sản phẩm, job, export và nguồn dẫn chứng phải kiểm quyền ở server; ẩn nút FE không thay thế kiểm quyền.
5. Phân biệt tài liệu nguồn, bản nháp AI, phiên bản người dùng sửa, sản phẩm đã duyệt và tài liệu đã xuất bản vào kho. Không tự nhúng bản nháp hoặc đáp án vào kho phục vụ công khai.
6. Soạn thảo có thể bắt đầu chỉ từ mẫu và thông tin người dùng; tài liệu tham khảo là tùy chọn. Tạo câu hỏi dựa trên học liệu bắt buộc chọn phạm vi nguồn hợp lệ.
7. MVP dùng nguồn đã được xử lý và đủ quyền trong kho; nguồn chưa phát hành chỉ được dùng trong tác vụ nội bộ nếu có contract cho phép rõ ràng. Đính kèm trực tiếp ở giai đoạn sau phải đi qua ingestion hiện có, có trạng thái nguồn riêng, không tự công khai.
8. Người dùng duyệt và áp dụng thay đổi. AI không tự ký, gửi văn bản, phát hành đề, phê duyệt sản phẩm hoặc sửa dữ liệu hệ thống khác.
9. “Công cụ tài liệu” và “Trợ lý soạn thảo” dùng chung nghiệp vụ: một điểm vào bằng mẫu, một điểm vào bằng hội thoại. Không tạo hai pipeline tương đương.
10. Hai loại trợ lý mới mặc định nội bộ có đăng nhập. Kênh chatbot ẩn danh hiện có tiếp tục phục vụ hỏi đáp; API công khai phải chặn loại chưa hỗ trợ, kể cả khi gọi trực tiếp.
11. Agent dùng danh sách công cụ do BE cho phép theo loại trợ lý và theo kênh. Model diễn giải yêu cầu và đề xuất bước tiếp theo. BE kiểm tra tham số, quyền và trạng thái trước khi gọi công cụ. Cả hội thoại và biểu mẫu dùng cùng dịch vụ nghiệp vụ.

## 4. Trải nghiệm và tổ chức giao diện

### 4.1. Điểm vào

- Trợ lý AI: chọn loại khi tạo, cấu hình bằng các lựa chọn nghiệp vụ đơn giản; loại hỏi đáp giữ luồng đang dùng.
- Trang trợ lý soạn thảo: chọn mẫu hoặc bắt đầu bản nháp; hội thoại ở một bên, tài liệu có thể sửa ở bên còn lại.
- Trang trợ lý học liệu: chọn phạm vi và yêu cầu, xem phân bổ câu hỏi, duyệt kết quả theo từng câu.
- Khu vực “Sản phẩm của tôi” bên trong trợ lý và liên kết từ Tổng quan: bản thảo, bộ câu hỏi, đề thi gần đây. Chỉ tách thành menu “Không gian làm việc” khi cần quản lý xuyên nhiều trợ lý.
- Tác vụ tiếp tục là nơi xem công việc nền; báo cáo ban đầu nằm trong trợ lý/Tổng quan theo quyền, không cần ngay một dashboard lớn.
- Hội thoại hiển thị thông tin còn thiếu, bước đang chạy và liên kết mở bản nháp hoặc bộ câu hỏi. Việc chọn mẫu, xác nhận phân bổ hoặc áp dụng phần sửa dùng nút sẵn có của màn làm việc, trong menu Trợ lý AI hiện hành.

### 4.2. Quy tắc UI

Tái dùng PageHeader, semantic tokens, ViewModeToggle và primitives hiện có. Một hành động chính theo trạng thái; thao tác phụ trong một menu ⋯. Không bọc nhiều lớp hộp, không hiển thị ID/job/token cho người dùng thường. Desktop có vùng hội thoại và kết quả; màn nhỏ chuyển tab. Hỗ trợ bàn phím, trạng thái tải/rỗng/lỗi và khôi phục thao tác.

Không giả phần trăm trong lúc model đang sinh mà chưa đo được tiến độ. Nếu biết số nhóm: hiển thị “Đã xử lý 3/8 mục”; nếu chưa biết: hiển thị bước đang thực hiện. Tổng tiến độ không về 0 khi đổi bước, chỉ 100% khi kết quả đã lưu hoàn tất. Đóng bảng tác vụ không đồng nghĩa dừng job.

### 4.3. Ba luồng chuẩn

**Soạn thảo:** giao việc qua hội thoại hoặc chọn mẫu → bổ sung thông tin → tạo bản nháp → sửa thủ công hoặc áp dụng đề xuất → xem trước → xuất Word.

**Câu hỏi:** giao việc qua hội thoại hoặc biểu mẫu → xác nhận học liệu, phạm vi và phân bổ → tạo theo nhóm → kiểm tra nguồn và đáp án → giảng viên sửa và duyệt → lưu bộ câu hỏi.

**Đề thi:** chọn ngân hàng đã duyệt → đặt ma trận/điểm → kiểm tra đủ câu → ghép đề → kiểm tra → xuất bản đề và đáp án riêng. Không gọi model để cộng điểm hoặc đảo mã đáp án.

## 5. Thứ tự triển khai và sản phẩm bàn giao

| Giai đoạn | Phụ thuộc | Bàn giao chính | Quy mô tương đối |
|---|---|---|---|
| P0 — Chốt hợp đồng, mẫu và bộ nghiệm thu | Không | ADR ngắn, sơ đồ dữ liệu/quyền, mẫu chuẩn, ca kiểm tra | Nhỏ |
| P1 — Nền tảng sản phẩm AI | P0 | Loại trợ lý, lưu bản nháp/phiên bản, job nền, quyền, trace | Lớn |
| P2 — Trợ lý soạn thảo MVP | P1 | Agent soạn thảo nội bộ, 3 mẫu, sửa từng phần, xuất Word | Lớn |
| P3 — Trợ lý tạo câu hỏi MVP | P1 và pilot P2 | Dùng lại điều phối agent để tạo và duyệt câu hỏi từ một học phần | Lớn |
| P4 — Ngân hàng câu hỏi và ghép đề | P3 đạt pilot | Ngân hàng đã duyệt, ma trận, mã đề, xuất tách đáp án | Vừa–lớn |
| P5 — Công cụ tài liệu, học tập và hướng dẫn công khai | P2/P3 ổn; kênh công khai qua kiểm chứng riêng | Tóm tắt, so sánh, trích mốc, ôn tập và checklist tuyển sinh có nguồn | Theo từng công cụ |
| P6 — Quy trình và kết nối | Có nghiệp vụ được chọn + nền tảng quyền ổn | Một quy trình thực tế, sau đó kết nối tương ứng | Ước lượng sau khảo sát |
| R — Báo cáo và chất lượng | Khởi đầu P1 | Số liệu cơ bản → phản hồi → phân tích sử dụng/chất lượng | Xuyên suốt |

Đường triển khai ưu tiên: P0 → P1 → P2 → pilot soạn thảo → P3 → pilot câu hỏi → P4. P5 chia công cụ độc lập, không bắt hoàn thành mọi tiện ích trước khi làm P3. P6 không thuộc MVP. Đây không phải cam kết lịch; chốt khối lượng/ngày công sau P0 và sau mỗi pilot, không ước lượng toàn bộ chỉ từ số menu.

### P0 — Chốt phạm vi và điều kiện đầu vào

**Công việc:**

- Đọc lại AGENTS và diff; xác định phần đang thay đổi đồng thời, schema thật, worker và đường xuất tệp hiện có.
- Lập bảng chức năng tái sử dụng/phải bổ sung. Kiểm tra khả năng lưu kết quả hiện có trước khi thêm domain mới.
- Chọn ba mẫu Word thực tế: thông báo, kế hoạch, tờ trình. Chốt các mục bắt buộc, trường cho phép trống và font/bố cục theo mẫu cung cấp; không tự khẳng định chuẩn hành chính.
- Chọn một học phần, học liệu có quyền sử dụng, phạm vi ba chương và người duyệt chuyên môn.
- Chốt cấu trúc sản phẩm, trạng thái, quyền và việc giữ/xóa sản phẩm khi nguồn bị xóa.
- Chốt công cụ cho P2, tham số đầu vào, quyền gọi và nơi hiển thị kết quả. Xác định bước nào cần người dùng bổ sung thông tin, bước nào cần xác nhận ghi dữ liệu và giới hạn số lần gọi trong một yêu cầu.
- Chốt bộ đo nhỏ ở mục 9; ghi snapshot nguồn, model, cấu hình và rubric trước khi chạy.

**Nghiệm thu:** có mẫu, nguồn và tiêu chí duyệt cụ thể; tách rõ việc chưa xác định. Chưa có mẫu thật có thể dựng prototype nhưng không nghiệm thu xuất Word đúng mẫu.

### P1 — Nền tảng sản phẩm và tác vụ dùng chung

**Backend:**

- Thêm loại trợ lý với mặc định tương thích; validate cấu hình theo loại. Không đổi `collection_id` thành tùy chọn trên mọi loại một cách thiếu kiểm soát.
- Thêm lưu sản phẩm và revision bất biến; bản nháp hiện hành dùng optimistic concurrency để tránh ghi đè giữa hai tab hoặc AI và người dùng.
- Snapshot nguồn gồm collection/document/revision/hash và tham chiếu vị trí; snapshot mẫu và model thực tế. Không lấy văn bản trả lời cũ làm chứng cứ mới.
- Job có idempotency, checkpoint theo phần, hủy, tiếp tục phần lỗi khi đủ điều kiện và giới hạn đồng thời qua hệ thống hiện có.
- Lưu trạng thái tác vụ theo bước để agent có thể chờ người dùng bổ sung rồi tiếp tục đúng bản nháp và nguồn đã chọn. Tái dùng định danh job, quyền workspace và cơ chế theo dõi hiện có.
- Worker trả kết quả muộn không được ghi đè revision mới hoặc hồi sinh sản phẩm đã xóa. Nguồn/model thay đổi thì không âm thầm nối tiếp job cũ.
- Tích hợp vòng đời xóa cứng: xác nhận phạm vi ảnh hưởng, chặn job ghi lại, dọn export/storage theo chính sách, báo đúng trạng thái đang xóa. Không thêm chức năng lưu trữ bắt buộc.

**Frontend:** chọn loại trợ lý; trang sản phẩm; tải/mở lại bản nháp; lịch sử phiên bản; tác vụ nền; trạng thái chưa lưu/xung đột/lỗi. Người dùng thấy tên nghiệp vụ, không thấy schema kỹ thuật.

**Nghiệm thu:** mở lại giữ đúng nội dung; hai tab không ghi đè âm thầm; gửi lặp không tạo hai job; dừng/xóa không bị ghi lại; sai quyền bị chặn cả API/export; trợ lý hỏi đáp và kênh công khai cũ không đổi hành vi.

### P2 — Trợ lý soạn thảo văn bản

**Phạm vi MVP:** thông báo, kế hoạch, tờ trình; tạo từ mẫu, hỏi bổ sung, chỉnh tay, AI sửa phần chọn, xuất DOCX. Chưa có gửi văn bản/chữ ký số/cộng tác thời gian thực/trình thiết kế mẫu kéo thả.

**Backend:**

- Mẫu có version, trường nhập có kiểu, đề mục bắt buộc và quy tắc render. Tách dữ kiện do người dùng khai báo, dữ kiện lấy từ nguồn và câu chữ AI đề xuất.
- Lập dàn ý rồi sinh theo mục nếu tài liệu dài. Thiếu thông tin hỏi gộp một lần khi có thể; giữ placeholder rõ ràng thay vì bịa số/người ký/căn cứ.
- Sửa phần chọn tạo đề xuất diff dựa trên revision cụ thể; người dùng áp dụng mới thành revision. Sửa tay làm kết quả kiểm chứng cũ mất hiệu lực ở phần liên quan.
- DOCX được dựng từ mô hình nội dung có cấu trúc và template version. Markdown/HTML là dạng hiển thị/xuất phụ, không phải nhiều bản nội dung độc lập.
- Kiểm tra thông tin cần điền, số liệu/nguồn, cấu trúc và chính tả theo phạm vi. Cho tải bản nháp có cảnh báo thiếu trường; không gắn trạng thái hoàn tất khi mục bắt buộc còn thiếu.

**Luồng agent đầu tiên.** Người dùng nhắn “Soạn thông báo tổ chức hội thảo”. Agent đề xuất mẫu, lấy nguồn được phép khi cần và hỏi gộp các trường còn thiếu như ngày, địa điểm và đơn vị phụ trách. Người dùng có thể bổ sung ngay trong hội thoại. Khi chọn **Tạo bản nháp**, BE dùng mẫu và nguồn đã ghim để chạy tác vụ nền, sau đó trả liên kết mở bản nháp. Đề xuất sửa hiện ở đúng đoạn. **Áp dụng** lưu thay đổi trên phiên bản đã xem. **Xuất Word** dựng tệp từ phiên bản người dùng chọn.

| Công cụ P2 | Phạm vi |
|---|---|
| Chọn mẫu | Đọc danh sách mẫu được phép và trả các trường cần điền |
| Tra cứu tài liệu | Lấy đoạn có căn cứ trong phạm vi được phép và giữ tham chiếu nguồn |
| Tạo bản nháp | Tạo job theo mẫu, dữ kiện đã xác nhận và nguồn đã chọn |
| Đề xuất sửa phần chọn | Trả bản xem trước gắn với đoạn và phiên bản hiện tại |
| Xuất Word | Tạo tệp từ phiên bản và mẫu đã chọn khi người dùng yêu cầu |

**Frontend:** biểu mẫu ngắn trước hội thoại; editor liền mạch; chọn đoạn để sửa; xem trước thay đổi; nguồn tham khảo ở panel gọn. Nút chính tùy trạng thái: tạo, áp dụng hoặc lưu. Xuất tệp trong toolbar/menu phù hợp.

**Nghiệm thu:** ba mẫu xuất đúng cấu trúc đã duyệt; tiếng Việt/bảng/ngắt trang không mất nội dung; sửa phần A không thay phần B; thiếu dữ kiện không tự điền; ghi nhận người sửa và phiên bản xuất. Cán bộ hoàn thành được thao tác mà không cần biết prompt/model.

### P3 — Trợ lý tạo câu hỏi từ học liệu

**Phạm vi MVP:** trắc nghiệm một đáp án và tự luận; một học phần; chọn chương/chủ đề; số lượng và mức độ đề xuất; đáp án/giải thích/hướng dẫn chấm; sửa/duyệt từng câu. Chưa xử lý tự động câu hỏi chỉ nằm trong hình/công thức không được bóc tách tin cậy.

**Backend:**

- Lập bản đồ chương/mục từ nguồn đã chọn; nếu mục lục chưa rõ, cho người dùng chọn phạm vi thủ công. Không suy toàn bộ phạm vi từ tên file.
- Tạo phân bổ số câu theo chương, loại và mục tiêu. Có thể gợi ý phân bổ, giảng viên xác nhận trước chạy; tổng số câu phải khớp yêu cầu.
- Dùng outline/section để phủ chương và lấy evidence tương ứng, không chỉ top-k của một truy vấn cho cả bộ đề. Nguồn thiếu thì báo phần thiếu, không bù bằng kiến thức ngoài.
- Sinh theo nhóm; giữ câu hoàn tất; đo/checkpoint theo đơn vị rõ ràng. Câu mới chứa nội dung, lựa chọn, đáp án, giải thích, chủ đề, mức độ đề xuất, evidence và trạng thái duyệt.
- Kiểm cấu trúc, đáp án thuộc lựa chọn, lựa chọn trùng, câu gần trùng trong batch/ngân hàng, mâu thuẫn nội dung và căn cứ cho đáp án. AI đánh giá ngữ nghĩa là hỗ trợ, không tự chứng nhận một đáp án duy nhất.
- Bài tập vận dụng có thể dùng tình huống/số giả định nhưng phải ghi rõ giả định; nguyên lý/cách giải phải có nguồn. Không trình bày dữ liệu giả định như dữ kiện thực của trường. Phép tính dùng chương trình khi có thể kiểm được.
- Kiểm tính đầy đủ bộ câu hỏi trước báo hoàn tất; mức độ khó là đề xuất, chưa phải thống kê thực nghiệm.
- Dùng lại điều phối hội thoại, kiểm tra quyền, job và liên kết kết quả từ P2. Agent hiểu yêu cầu như “Tạo 20 câu từ chương 1–3”, hiện phân bổ để giảng viên xác nhận rồi tạo theo nhóm. Kết quả mở ở màn duyệt từng câu. Thao tác duyệt thuộc giảng viên có quyền.

**Frontend:** chọn phạm vi và mục tiêu bằng biểu mẫu; xem phân bổ; danh sách câu hỏi và vùng chi tiết; mở nguồn; sửa nội dung/đáp án; duyệt/từ chối. Tạo lại một câu cần xem đề xuất trước thay, không ghi đè câu đã duyệt.

**Nghiệm thu:** đúng số câu và phạm vi hoặc báo thiếu rõ ràng; tất cả câu đưa vào ngân hàng đã được giảng viên duyệt; không rò đáp án tới người không có quyền; sửa câu/đáp án tạo revision và cần duyệt lại.

### P4 — Ngân hàng câu hỏi và ghép đề

- Ngân hàng lưu phiên bản câu đã duyệt, chủ đề, chương, loại, mức độ đề xuất, nguồn và lịch sử sử dụng.
- Ma trận đề quy định số câu/điểm theo chương và mức độ. Kiểm khả thi trước ghép; thiếu câu thì báo đúng ô ma trận, không tự nới phạm vi.
- Ghép đề bằng thuật toán có seed truy vết; ghim question revision để đề cũ không đổi khi câu hỏi được sửa.
- Chỉ đảo lựa chọn khi câu đủ điều kiện. Câu có quan hệ thứ tự hoặc lựa chọn kiểu “cả A và B” không đảo tùy tiện.
- Kiểm tổng điểm, ánh xạ đáp án sau đảo, câu lặp và cấu trúc từng mã đề. Đảo thứ tự không đủ để khẳng định các đề khác nhau tương đương độ khó.
- Xuất riêng đề học viên và đáp án/hướng dẫn chấm. Bản học viên không chứa đáp án trong nội dung ẩn, comment, tracked changes, metadata hoặc file đính kèm của DOCX.
- Không tự phát hành đề/đáp án qua chatbot công khai hoặc đưa vào chỉ mục RAG dùng chung.

**Nghiệm thu:** ma trận và tổng điểm chính xác; đề ghim đúng revision; mọi mã đề có đáp án tương ứng; kiểm quyền tải tệp và không rò đáp án cả ở nội dung file.

### P5 — Công cụ tài liệu và học tập

Phát triển từng công cụ sau khi có người dùng thực tế; dùng lại sản phẩm, nguồn, editor và job P1.

| Công cụ | Đầu ra | Điều kiện chất lượng |
|---|---|---|
| Tóm tắt tài liệu | Bản tóm tắt theo mục tiêu và dung lượng | Có nguồn cho ý chính; không mất điều kiện/ngoại lệ trọng yếu |
| So sánh phiên bản | Bảng mục cũ/mới/thay đổi/vị trí | Ghim cả hai phiên bản; phân biệt đổi chữ và đổi ý; không tự diễn giải hiệu lực pháp lý |
| Trích mốc thời gian | Danh sách sự kiện/thời gian/nguồn | Phân biệt ngày ban hành, hiệu lực, hạn đăng ký và thời gian sự kiện |
| Giải thích học liệu | Giải thích có dẫn nguồn, bài luyện tập | Chỉ dùng học liệu được phép; không mở ngân hàng đề kín |
| Ôn tập | Bộ luyện tập đã được phép công bố | Tách khỏi đề chưa sử dụng; phản hồi học tập không mặc định là điểm chính thức |

**Hướng dẫn tuyển sinh công khai.** Thí điểm trên kênh hỏi đáp công khai sau P2/P3 và khi kênh vượt qua kiểm chứng riêng. Agent hỏi diện xét tuyển hoặc năm khi cần, tra cứu trong kho đã phát hành của trợ lý và hiển thị checklist giấy tờ, mốc thời gian kèm dẫn chứng. Danh sách công cụ công khai chỉ gồm thao tác đọc và trình bày kết quả trong phiên. Dùng hạn mức của kênh hiện có. Thí điểm bắt đầu với một diện xét tuyển có nguồn kiểm tra được.

### P6 — Quy trình công việc và kết nối

Chọn một luồng đầu tiên: dự thảo → người phụ trách góp ý → tác giả sửa → người có quyền duyệt. Hoặc câu hỏi → phản biện → ngân hàng đã duyệt. “Duyệt sản phẩm” khác “phát hành nguồn vào kho” và khác ký ban hành văn bản.

Tái khảo sát API inbox/quy trình hiện có trước xây mới; không tự đưa lại menu Hộp thư duyệt đã bị bỏ. Bổ sung người nhận, trách nhiệm, quyền, thông báo, lịch sử và trạng thái trả lại. Chưa cần canvas workflow hoặc agent tự quyết định mọi bước.

Kết nối chỉ thêm khi có nghiệp vụ: quản lý văn bản để nhận mẫu/chuyển dự thảo; LMS để nhận học liệu/xuất bộ câu hỏi; hệ thống đào tạo để tra dữ liệu được phép. Ưu tiên đọc trước; ghi cần preview, xác nhận đúng actor+tham số, thời hạn, idempotency và audit. Thống kê số liệu dùng truy vấn có cấu trúc, không cộng bằng model trên các đoạn RAG.

### R — Báo cáo và chất lượng xuyên suốt

- P1: lưu loại tác vụ, kết quả, thời gian chờ/xử lý, model/config version, token đo được/ước tính riêng, lỗi theo công đoạn, số lần retry/repair và số phần hoàn tất.
- P2: số bản nháp, tỷ lệ xuất thành công, phản hồi người dùng, phần cần sửa. Không coi số lượt sử dụng là chất lượng.
- P3/P4: số câu được duyệt/từ chối, lý do, mức phủ chương, lỗi đáp án, trùng câu, bộ đề đạt ma trận.
- Agent: theo dõi loại bước, thời lượng và kết quả công cụ, các lượt chờ bổ sung, số job dừng/lỗi và lần dùng lại checkpoint. Dùng các mã trạng thái và số liệu tổng hợp cho báo cáo.
- Hỏi đáp: tiếp tục theo dõi câu chưa trả lời được, lỗi provider, lỗi kiểm chứng nguồn và phản hồi; không gộp tất cả thành “không có dữ liệu”.
- Dashboard tổng hợp theo quyền, bộ lọc thời gian/loại trợ lý. Không log toàn văn đề, đáp án, corpus, prompt riêng hoặc thông tin cá nhân vào telemetry mặc định. Chi phí tiền chỉ hiển thị khi có đơn giá tin cậy; model nội bộ chưa có đơn giá thì hiển thị token và thời gian.

## 6. Phương án kỹ thuật BE/FE

### 6.1. Tái sử dụng và ranh giới module

| Thành phần | Hướng xử lý |
|---|---|
| `assistants`, `conversations` | Bổ sung loại và dispatch theo hợp đồng nghiệp vụ; không ép toàn bộ đầu ra vào answer RAG |
| `knowledge`, `ocr`, `rag` | Tái sử dụng nguồn/provenance/truy xuất; bổ sung chọn section cho câu hỏi; không thay parser chỉ vì thêm chức năng |
| `modelops` | Dùng gateway/capacity/quota/resilience hiện có; không thêm retry lồng ở từng công cụ |
| `operations`, `lifecycle` | Mở job catalog, cancellation/checkpoint và xóa cho sản phẩm mới |
| Lưu sản phẩm | Đề xuất domain nhỏ `authoring` nếu khảo sát P0 xác nhận hiện tại chưa đáp ứng; chứa sản phẩm/revision/mẫu/xuất tệp, không chứa toàn bộ RAG |
| Câu hỏi/đề | Đề xuất domain `assessments` khi P3/P4 cần; dùng lưu sản phẩm chung, chỉ tách dữ liệu có nghiệp vụ câu hỏi/đề |
| `publications` | Giữ contract public QA; chặn loại chưa hỗ trợ tại server |
| FE `src/api/` | Domain types/requests/queries tương ứng; giữ re-export tương thích; không gọi endpoint rải trong UI |

Tên domain/entity/route là đề xuất để chốt P0, không phải mô tả đã tồn tại. Router mỏng, service và adapter theo module hiện hành; không thêm framework/worker mới mặc định.

### 6.2. Dữ liệu tối thiểu cần thiết kế

- Product: loại, tên, owner, workspace, assistant, trạng thái, revision hiện hành.
- ProductRevision: nội dung có schema version, parent revision, người tạo/sửa, thời điểm, content hash, nguồn và mẫu được ghim, kiểm tra áp dụng cho đúng revision.
- TemplateVersion: mẫu gốc, schema trường, cấu trúc render và version; không cần UI designer trong MVP.
- GenerationRun: phần được yêu cầu, base revision, idempotency, trạng thái các nhóm, usage, lỗi, model/config snapshot; dùng hạ tầng job hiện có.
- QuestionRevision: stem/options/answer/explanation/rubric, evidence, topic, mức độ đề xuất, review status; trường cốt lõi có kiểu, metadata phụ JSON.
- ExamVersion: blueprint, danh sách question revision, thứ tự/seed, điểm, mapping đáp án và artifact export.
- ExportArtifact: product revision, template version, đối tượng nhận (người học/giảng viên), storage key, quyền và hash; không dùng URL public vĩnh viễn cho đề/đáp án.

JSON linh hoạt cho metadata mở rộng, không biến mọi dữ liệu thành JSON tự do: đáp án, trạng thái, quyền và phiên bản phải được validate. Không lưu Markdown, editor JSON và DOCX thành ba nguồn có thể sửa độc lập; chọn một mô hình nội dung chuẩn và render các định dạng dẫn xuất.

### 6.3. Nhóm API cần chốt ở P0

Tạo/đọc/cập nhật trợ lý theo loại; CRUD sản phẩm; lấy/lưu revision với expected revision; yêu cầu tạo/sửa theo phần; đọc/dừng/tiếp tục job; preview/apply đề xuất; lấy nguồn theo quyền; tạo/lấy export; duyệt câu hỏi; tạo/kiểm tra/ghép ma trận; báo cáo. Giữ prefix/router/workspace access hiện hành, cập nhật OpenAPI và FE client cùng batch.

Các thao tác bất đồng bộ trả job và polling/event theo cơ chế repo hỗ trợ. Apply/export ràng buộc revision, không lấy “latest” ở giữa job. Sửa sau duyệt tạo bản nháp mới; snapshot đã dùng trong đề cũ không thay đổi.

### 6.4. Điều phối agent và thực thi công cụ

- Bắt đầu bằng luồng điều phối do BE kiểm soát theo trạng thái. Model qua ModelOps nhận thông tin đã được chọn để hiểu yêu cầu, đề xuất công cụ hoặc hỏi tiếp. BE quyết định bước hợp lệ theo trạng thái, schema tham số và danh sách công cụ của trợ lý. Cách này cũng áp dụng nếu model sinh đề xuất công cụ qua JSON có cấu trúc.
- BE lấy actor, workspace và kênh từ phiên đã xác thực hoặc ngữ cảnh của kênh công khai. Kiểm tra quyền với từng tài nguyên, ghim revision và coi tài liệu/câu trả lời model là dữ liệu đầu vào. Mọi công cụ đều có phạm vi, điều kiện kết thúc và xử lý lỗi rõ ràng.
- Giới hạn số bước, số lần gọi model/công cụ, thời gian và ngân sách theo tác vụ qua cơ chế hiện hành. Khi chờ thông tin hoặc xác nhận, giải phóng worker và tiếp tục từ trạng thái đã lưu. Khi dừng, giữ bản nháp đã lưu và báo phần còn thiếu.
- Bước ghi dữ liệu hiển thị nội dung sẽ áp dụng. Yêu cầu xác nhận gắn với actor, thao tác, tham số, phiên bản và thời hạn. Nút **Tạo bản nháp**, **Áp dụng** hoặc **Xuất Word** có thể là chính thao tác xác nhận khi màn hình đã hiển thị đúng phạm vi. BE kiểm lại quyền và revision lúc thực hiện, chống chạy lặp và ghi audit.
- P6 mở thêm thao tác gửi văn bản hoặc cập nhật hồ sơ khi có tích hợp và quyền nghiệp vụ tương ứng. Áp dụng cơ chế xác nhận trên với đúng đích và nội dung thay đổi.

## 7. Nguồn, quyền và vòng đời

- Giảng viên được duyệt câu hỏi trong phạm vi được giao; không suy quyền từ việc biết URL, ID hoặc thuộc một workspace bất kỳ. Vai trò cụ thể ánh xạ membership/role hiện có, không tạo role mới trước khi khảo sát.
- Người học/khách công khai không được thấy kho đề kín, đáp án, provenance excerpt hạn chế hoặc export của giảng viên. Kiểm quyền cả trang, API, citation và tải tệp.
- Nguồn có phiên bản mới: sản phẩm cũ tiếp tục ghim phiên bản cũ, hiển thị cần xem lại khi liên quan; không tự sửa đề hoặc văn bản đã duyệt.
- Nguồn bị thu hồi quyền: không tiếp tục generation/export dựa trên nguồn nếu không đủ quyền; kiểm lại quyền lúc đọc kết quả và tải file, không chỉ lúc tạo job.
- Xóa nguồn: preview liệt kê sản phẩm phụ thuộc; chốt rõ artifact nào bị xóa và sản phẩm nào chỉ mất nguồn đối chiếu. Không giữ bản sao nội dung nguồn trái với phạm vi xóa; lưu dấu vết tối thiểu theo chính sách được chốt.
- Xóa sản phẩm: xóa cứng theo luồng được xác nhận, dừng/khóa ghi job liên quan và dọn artifact. Lịch sử revision không đồng nghĩa thêm chức năng lưu trữ tài liệu.
- Tài liệu và mẫu nhập là nội dung không tin cậy; không thực thi macro/lệnh/URL nhúng hoặc chỉ dẫn thay quyền. Quét giới hạn kích thước/định dạng bằng cơ chế upload hiện có.

## 8. Hiệu năng, model và chi phí

- Không gửi lại toàn bộ giáo trình trong mỗi lần tạo câu hoặc mỗi lượt sửa. Dùng outline và evidence theo chương/mục; tránh retrieval vô hạn để bù sinh sai.
- Cache kết quả có khóa nguồn+revision+quyền+mẫu+model/config+schema; không dùng lại kết quả sau đổi nguồn hoặc quyền.
- Sinh nhóm đủ nhỏ theo capacity thực và context còn lại. Không gán trần token cố định từ FE khi người dùng không yêu cầu; vẫn tôn trọng giới hạn vật lý, ngân sách vận hành và quota.
- Khi lỗi token được xác định và phần có thể chia: chỉ chia phần lỗi theo cấu trúc, giữ phần xong và idempotency phần con. Không chia/retry vì mọi lỗi 502 hoặc timeout không rõ kết quả.
- Một nơi chịu trách nhiệm retry provider theo chính sách ModelOps/gateway; phân biệt retry hạ tầng với sửa đầu ra không đạt contract, tránh nhân số lần gọi giữa nhiều tầng.
- Sửa đoạn chỉ gửi phần chọn và ngữ cảnh cần thiết. Chỉ thêm bước model kiểm tra khi có tiêu chí rõ; không mặc định chạy hai model cho mọi sản phẩm.
- Đo thời gian chờ hàng đợi, thời gian inference, tổng token và tỷ lệ hoàn tất riêng. Chốt mục tiêu độ trễ từ phép đo pilot cùng server/model; chưa cam kết số giây không có bằng chứng.

## 9. Kế hoạch kiểm chứng có phạm vi

Không chạy lại bộ 100 câu G3 trong phạm vi kế hoạch này. Tách test ứng dụng với live inference; full suite nội bộ theo quy định repo không đồng nghĩa chạy bộ 100 câu hỏi model.

### 9.1. Bộ ca đề xuất trước pilot

| Nhóm | Quy mô khởi đầu | Điều cần chứng minh |
|---|---|---|
| Soạn thảo | 12 tình huống: 3 mẫu × đủ thông tin/thiếu thông tin/sửa phần/xung đột nguồn | Đúng mẫu, không bịa, sửa có kiểm soát, xuất lại đúng revision |
| Câu hỏi | 30 câu: 3 chương × 8 trắc nghiệm + 2 tự luận | Nguồn, đáp án, phân bổ, trùng câu, nội dung được giảng viên chấm |
| Đề thi | 3 blueprint nhỏ: đủ ngân hàng/thiếu câu/có yêu cầu đảo lựa chọn | Kiểm khả thi, tổng điểm, mapping đáp án và export an toàn |
| RAG hồi quy | 8 câu chọn trước: Q41 đang lỗi + 7 ca bảng/nguồn/ngoài phạm vi/follow-up đại diện | Không làm hỏng QA; giữ kết quả lỗi nền độc lập |
| Lỗi/quyền/job | Bộ test tự động ở API/worker/storage phù hợp | Đổi quyền, gửi lặp, hai tab, hủy, xóa, timeout, phần lỗi, restart worker |
| Điều phối agent | Gắn vào ca P2/P3 và kiểm API với model giả lập | Hỏi bổ sung rồi tiếp tục, chặn công cụ sai kênh/quyền, xác nhận hết hạn hoặc sai phiên bản, dừng khi đạt giới hạn |
| Hướng dẫn công khai | Kiểm chứng riêng khi làm P5 | Đúng diện/năm, checklist có nguồn, làm rõ khi thiếu dữ kiện, từ chối thao tác ghi hoặc truy cập nguồn nội bộ |

Số liệu trên là phạm vi đề xuất, chưa thực chạy. Chuẩn bị và kiểm contract offline trước; chỉ gọi model khi vào gate live đã được giao. Mỗi ca live một lượt đầu được giữ nguyên để chấm; chỉ lặp một tập nhỏ khi cần đo dao động, báo cả lần lỗi/repair, không chạy lại đến khi xanh.

### 9.2. Cổng nghiệm thu đề xuất

- **An toàn và dữ liệu:** không có rò đề/đáp án, vượt quyền, mất sửa tay, ghi đè revision hoặc hồi sinh sau xóa trong tập kiểm thử. Có lỗi loại này thì chặn pilot mở rộng.
- **Soạn thảo:** 12/12 ca không bịa trường bắt buộc và không mất nội dung ngoài phạm vi sửa; ba mẫu export đạt kiểm tra trực quan. Mục tiêu ≥10/12 ca được cán bộ đánh giá dùng được với sửa nhỏ; nếu chưa đạt, chỉ pilot giới hạn, không công bố chất lượng đạt.
- **Câu hỏi:** tất cả câu được lưu duyệt có nguồn và được giảng viên xác nhận đáp án; mục tiêu lần sinh đầu ≥24/30 câu dùng được với sửa nhỏ, không có lỗi kiến thức nghiêm trọng trong nhóm được chấp nhận. Báo riêng tỷ lệ câu phải viết lại và tỷ lệ được duyệt; không chỉ chấm tính hợp lệ JSON.
- **Đề:** mọi ca xác định đạt ma trận/tổng điểm/mapping đáp án; thiếu ngân hàng phải báo thiếu; bản học viên không chứa đáp án kể cả nội dung ẩn.
- **Độ bền:** fault injection không mất kết quả đã lưu; retry không trùng; trạng thái UI và server nhất quán. Chỉ số tiến độ phản ánh đơn vị thật.
- **Agent:** thao tác thiếu quyền, sai kênh hoặc sai xác nhận không được thực thi. Sau lượt bổ sung thông tin, tác vụ dùng đúng phạm vi nguồn và phiên bản đã chọn. Khi vượt giới hạn, UI báo trạng thái thực và cho mở lại kết quả đã lưu.
- **QA hiện hành:** so với baseline cùng nguồn/model; lỗi Q41 phải được ghi rõ, không tuyên bố G3 PASS từ test mới. Rủi ro này không chặn dựng editor nhưng chặn tuyên bố mọi tác vụ dùng bảng đã tin cậy.
- **Vận hành:** môi trường pilot có đăng nhập/quyền thật; không dùng bypass dev cho production; có tắt riêng từng tính năng mới và theo dõi lỗi.

Các ngưỡng chất lượng là đề xuất để chốt P0, không phải chứng nhận bảo đảm cho mọi tài liệu. Người duyệt chuyên môn quyết định chất lượng cuối cùng; model tự chấm không thay người duyệt.

### 9.3. Kiểm tra kỹ thuật mỗi batch

Theo [bảng kiểm chứng repo](../../.agents/rules/verification.md): Ruff/regression backend; DB test cô lập và migration/contract nếu thay schema; full suite một lần sau batch BE ổn; Biome/build frontend và kiểm tra tương tác/ảnh ở desktop/mobile. Không giả định FE có runner test riêng khi repo chưa có. Export DOCX phải render/xem trang, kiểm tiếng Việt, bảng, header/footer/ngắt trang và kiểm nội dung ẩn của bản học viên. Không chạy test trên DB ứng dụng.

## 10. Triển khai, tương thích và rollback

- P0 chốt contract; P1 migration additive, trợ lý cũ default QA; API chặn tổ hợp loại/cấu hình không hợp lệ. Không di chuyển/xóa dữ liệu cũ để bật tính năng mới.
- Triển khai schema/API/worker hỗ trợ trước khi mở UI; đọc payload cũ theo version. Không bật job mới khi worker còn phiên bản chưa hiểu job.
- Từng tính năng có cờ bật riêng; mở thử trong phạm vi người dùng được chọn. Tắt tính năng ngừng tạo job mới nhưng vẫn cho người có quyền đọc/xuất sản phẩm đã lưu nếu an toàn.
- Rollback code không chạy migration phá dữ liệu. Giữ artifact và revision mới, có hướng xử lý job đang chạy; không giả vờ job đã thành công khi worker cũ không hỗ trợ.
- Pilot soạn thảo với nhóm cán bộ nhỏ, pilot câu hỏi với giảng viên một học phần; thu phản hồi và sửa trước khi nhân rộng.
- SSO, quyền và vận hành production đang làm là luồng song song cần nghiệm thu trước mở người dùng thật. Kế hoạch này không tự cho phép deploy hoặc công khai trợ lý mới.

## 11. Danh sách thực hiện để giao từng đợt

| Mã | Công việc | Bằng chứng bàn giao |
|---|---|---|
| A01 | Khảo sát tái sử dụng, hợp đồng agent và quyền P0 | ADR, danh sách công cụ P2, quyền, tham số và bước xác nhận |
| A02 | Chuẩn bị mẫu/học liệu/rubric | 3 mẫu, một học phần, bộ ca và người duyệt |
| A03 | Loại trợ lý và tương thích QA | Schema/API/migration + test trường hợp cũ và sai loại |
| A04 | Product/revision/nguồn/job | Test lưu, conflict, idempotency, hủy/xóa và quyền |
| A05 | FE tạo trợ lý và vùng sản phẩm | API thật, deep link, responsive, trạng thái trung thực |
| A06 | Điều phối agent soạn thảo và sinh/sửa dự thảo | Hỏi bổ sung, gọi đúng công cụ, mở bản nháp và áp dụng đúng revision |
| A07 | Template/render/export Word | File mẫu đã render kiểm tra và đối chiếu nội dung |
| A08 | Pilot soạn thảo + báo cáo cơ bản | Bảng chấm 12 ca, usage/latency/lỗi và kết luận giới hạn |
| A09 | Điều phối agent tạo câu hỏi, phạm vi và phân bổ | Xác nhận trước khi sinh, phủ chương, checkpoint nhóm, evidence và đáp án |
| A10 | Duyệt và bảo vệ câu hỏi | Kiểm quyền, sửa cần duyệt lại, bộ chấm 30 câu |
| A11 | Ngân hàng/ghép đề/export tách biệt | Ma trận, điểm, mã đề/đáp án, kiểm chống rò |
| A12 | Công cụ tài liệu mở rộng | Từng công cụ có pilot và nguồn truy vết riêng |
| A13 | Một quy trình/kết nối thực tế | Quyền, preview/approval, audit, thử lỗi và rollback |
| A14 | Hướng dẫn tuyển sinh công khai trong P5 | Checklist có dẫn chứng, hạn mức kênh và kiểm tra quyền công cụ |

Đợt đầu nên giao A01–A02. Sau khi chốt, triển khai A03–A07 thành lát cắt dùng được từ tạo trợ lý đến xuất Word; nghiệm thu A08 rồi mới mở A09–A11. Báo cáo R được bổ sung trong mỗi đợt. Chưa xây canvas quy trình, chấm thi tự động, sinh đề từ hình/công thức phức tạp hoặc tích hợp toàn bộ hệ thống trường trong MVP.

## 12. Trạng thái tại thời điểm lập kế hoạch

Đã lập kế hoạch và đối chiếu một số contract/file hiện tại. Chưa triển khai các giai đoạn, chưa chạy model hay test ứng dụng. Các kết quả kiểm chứng G3/công khai trong mục 2 là báo cáo lịch sử có giới hạn, không phải kết quả của phiên lập kế hoạch này.
