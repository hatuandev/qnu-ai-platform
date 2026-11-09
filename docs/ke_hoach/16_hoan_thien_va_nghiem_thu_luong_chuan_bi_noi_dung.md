# 16 — Hoàn thiện và nghiệm thu luồng chuẩn bị nội dung QNU V1

- Ngày lập: 2026-11-08. Trạng thái: **kế hoạch, chưa triển khai các hạng mục bổ sung hoặc chạy benchmark live trong phiên lập kế hoạch**.
- Kế thừa [KH #15](15_ke_hoach_trai_nghiem_nguoi_dung_qnu_v1.md) và [runbook pilot](../quy_trinh/46_pilot_qnu_v1_va_dong_pham_vi.md), không xây một pipeline song song.
- Mã tham chiếu: `f3f47284`, nhánh `feat/v1-user-workflow`. Working tree có thay đổi của công việc khác; phải ghi lại commit và hash diff thực tế trước mỗi đợt đo.
- Yêu cầu: người dùng tải tài liệu, xem/sửa chỗ cần chú ý và gửi duyệt; hệ thống tự xử lý kỹ thuật. Kiểm tra bằng các provider đã seed; mọi tác vụ Chat trong đợt nghiệm thu dùng Qwen đã được người dùng cấu hình qua llama.cpp.

## 1. Thế nào là luồng mới chạy ổn?

Không kết luận từ việc màn hình không báo lỗi hoặc model trả JSON hợp lệ. Phải có bằng chứng riêng cho năm lớp:

| Lớp | Cần chứng minh | Bằng chứng |
|---|---|---|
| Đọc nguồn | Đúng công cụ, không mất đoạn/bảng/chú thích, vị trí nguồn mở được | Manifest nguồn, đối chiếu trang/khối/ô và báo cáo thiếu |
| Chuẩn bị nội dung | Bản đầy đủ giữ nguồn; AI không thay số liệu, phạm vi hay điều kiện | So sánh canonical trước/sau, đề xuất AI và dẫn chứng riêng |
| Vận hành | Chuyển trang, mất kết nối, dừng hoặc giao job trùng không gây mất dữ liệu/gọi lặp | Test API/worker, checkpoint, audit và trace |
| Phục vụ hỏi đáp | Chỉ dùng bản đã xuất bản; trả lời đúng, đủ và có nguồn trong phạm vi | Benchmark Qwen thật, retrieval trace và chấm nội dung |
| Trải nghiệm | Cán bộ hoàn tất công việc mà không cần biết model/token/chỉ mục | Quan sát người thật, thời gian thao tác, số lần cần hỗ trợ |

Phân biệt ba kết luận: **gate mã nguồn đạt**, **nghiệm thu model thật đạt**, **pilot người dùng đạt**. Một kết luận không thay cho hai kết luận còn lại.

## 2. Model và môi trường phải dùng

### 2.1. Cấu hình đã đối chiếu chỉ đọc trong DB local

| Công việc | Provider/model hiện có | Quy định của đợt nghiệm thu |
|---|---|---|
| Bổ sung nội dung, metadata, chính tả, review, phân tích câu hỏi, trả lời | QNU AI Server / `qwen3.8-27b-q4` | Phân giải qua ModelOps, ghim danh tính cho từng lượt; không chuyển sang model khác |
| Embedding tài liệu và câu hỏi | QNU AI Server / `bge-m3` | Giữ cùng model/dimension giữa các biến thể; đo dimension thực |
| Xếp hạng lại | QNU AI Server / `bge-reranker-v2-m3` | Dùng khi cấu hình thử có rerank; kiểm đúng endpoint và cặp query/document |
| PDF scan/ảnh cần OCR | QNU MinerU GPU / `mineru` | Giữ API task/upload/poll/download hiện hành |
| Model đã seed nhưng không dùng để thay Qwen trong đợt này | 9router Luna / `cx/gpt-6-luna` | Không fallback hoặc dùng làm judge ngầm; thí nghiệm khác phải có báo cáo riêng |

DB local hiện có cả mặc định hệ thống và mặc định workspace SHL cho bốn capability Qwen/BGE-M3/BGE Reranker/MinerU. Seed chỉ chứng minh có cấu hình, chưa chứng minh inference đang hoạt động.

Qwen đang lưu `chat_template_kwargs.enable_thinking=false` cho `compiler`, `compiler_review`, `answer`, `ocr_review`; `wait_for_completion=true`. Metadata lưu ngày 05/11 ghi context `163840`, output `32768`; BGE-M3 và reranker ghi context `8192`. Đây là **metadata đã lưu**, không phải phép đo mới hay bằng chứng giới hạn thực của từng slot llama.cpp.

Không chạy lại seed để ghi đè cấu hình đã chỉnh. Không yêu cầu cán bộ nhập các thông số này. Model ID giữ theo gateway hiện hành; không đổi ID chỉ vì runtime bên dưới là llama.cpp.

### 2.2. Preflight riêng cho Qwen/llama.cpp — phải hoàn tất trước khi đo

1. Đọc ModelOps: model đang bật, quyền workspace, credential có thể dùng, endpoint chính xác, chính sách fallback/reasoning và thời điểm capacity. Chỉ xuất trường an toàn; không ghi key, header Authorization hoặc URL có bí mật.
2. Qua endpoint được phép, xác minh model đang phục vụ và phiên bản/build llama.cpp nếu server công bố. Có thể đọc `/props`, `/slots`, `/metrics` nếu gateway đã cho phép; không tự mở cổng nội bộ, bật endpoint hay gọi POST đổi cấu hình server.
3. Ghi context khả dụng của request/slot, số slot và tải hiện có. Không lấy tổng VRAM, hai GPU hoặc metadata context làm bằng chứng có thể chạy tùy ý nhiều request.
4. Gửi probe nhỏ qua **đúng adapter ModelOps**: Chat văn bản + JSON theo hợp đồng tác vụ, embedding số/vector hợp lệ, rerank index/score hợp lệ, OCR mẫu một trang. Probe không tính vào tập chấm chất lượng.
5. Đối chiếu payload reasoning và phản hồi trên bản llama.cpp thực tế. `verified=true` trong seed không đủ để kết luận bản triển khai hiện hành đã tắt reasoning. Không có trường reasoning trong response cũng không chứng minh token suy luận bằng 0; nếu không đo được phải ghi `unknown`.
6. Rà các đường gọi Chat phụ: planner/rewrite/metadata/validator có đi qua chính sách Qwen không. Không thêm tham số theo tên model một cách suy đoán; điều chỉnh hợp đồng ModelOps chỉ sau khi xác minh runtime hỗ trợ.
7. Phân biệt timeout kết nối, thời gian im lặng khi đọc, lease và thời gian toàn job. Không áp 300 giây làm trần tổng thời gian tài liệu. Heartbeat, nút dừng và trạng thái uncertain vẫn phải hoạt động.

Tài liệu llama.cpp hiện hành mô tả `chat_template_kwargs`, reasoning, `/slots` và thông tin timing; khả năng của build đang chạy cần xác minh riêng. [Nguồn chính thức](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

**Đầu ra:** `model-manifest.json` có model/endpoint fingerprint, config hash, build nếu biết, reasoning yêu cầu/quan sát, giới hạn và nguồn của từng giá trị, concurrency, prompt/parser version. Chưa có bằng chứng để `unknown`; không tự gán verified.

## 3. Những gì cần hoàn thiện trong sản phẩm

### A. Một chính sách chuẩn bị tự động

- Tái dùng `knowledge/preparation`, compiler, worker và ModelOps hiện có. Giao diện thường chỉ gửi ý định chuẩn bị tài liệu đang mở với đúng bản đã lưu.
- Giữ canonical đầy đủ từ nguồn; AI bổ sung thông tin phục vụ tìm kiếm/đối chiếu ở lớp riêng, có dẫn chứng. Không bắt AI viết lại toàn bộ tài liệu hoặc coi văn bản AI là nguồn gốc.
- Chính sách chọn phần cần AI theo cấu trúc, độ rõ ngữ cảnh và dấu hiệu đọc thiếu; không dùng từ khóa/tên ngành của câu test. Có trace giải thích phần nào được chọn hoặc bỏ qua.
- Đánh giá chính sách toàn bộ phần/bổ sung chọn lọc trước khi chốt; không mặc định thuật toán cũ tốt hơn. Chính sách được lưu phiên bản và ghim vào intent để có thể so sánh.
- DOCX đọc trực tiếp bằng Docling; PDF có text dùng PDF Inspector; PDF scan/ảnh dùng MinerU theo router hiện có. Preview Word/PDF không được trở thành nguồn nội dung thay cho đường đọc đã chọn.
- Metadata linh hoạt dạng JSON nhưng từng thông tin lọc cần kiểu/ý nghĩa và evidence: năm dữ liệu, năm ban hành, hiệu lực, ngành/đối tượng không nhập nhằng. Không suy toàn bộ từ trang đầu/tên file; giữ unknown/mâu thuẫn.
- Tái sử dụng kết quả chỉ khi fingerprint nguồn, revision, text version/hash, parser/policy/model tương ứng vẫn phù hợp. Đổi nguồn hoặc chính sách không được dùng cache cũ âm thầm.

### B. Kiểm tra chất lượng và xử lý phần lỗi

- Kiểm tra schema, nguồn/hash, liên kết đơn vị, độ bao phủ, bảng/ô gộp/chú thích, số liệu và đoạn trùng trước khi báo có bản nháp.
- Phân biệt `không tìm thấy lỗi`, `đã kiểm tra một phần`, `chưa kiểm tra` và `đã xác nhận bằng nguồn`. Không có cảnh báo AI không đồng nghĩa nội dung đúng hết.
- AI bổ sung tùy chọn lỗi: vẫn giữ canonical, báo đúng phần bổ sung chưa hoàn tất. Phần nguồn thiết yếu không đọc được: giữ blocker, không báo đủ nội dung.
- Token bị từ chối rõ trước sinh: chỉ điều chỉnh output một lần theo giới hạn hợp lệ provider trả. Token lỗi có thể chia: chia phần lỗi theo đoạn/mục/hàng bảng, giữ phần đã xong và khóa riêng cho phần con. Phản hồi bị cắt không cho biết số token chưa sinh.
- Không chia/gửi lại vì lỗi quota, quyền, đổi nguồn/model, mất kết nối không chắc kết quả. Không nhân retry giữa QNU và gateway.
- Dừng: ngừng nhận phần mới, giữ kết quả đã hoàn tất, yêu cầu hủy upstream nếu hỗ trợ. Không hứa upstream đã dừng nếu chưa xác nhận. Mất phản hồi sau dispatch phải để uncertain; không gửi lại để tránh tính/gọi trùng.

### C. Một màn kết quả và bàn giao duyệt

- Màn thường bỏ lựa chọn source/AI, provider, output và cấu hình kỹ thuật; các giá trị vẫn do chính sách quản trị giải quyết.
- Hiện nội dung và danh sách chỗ cần chú ý cùng một nơi; chọn vấn đề mở đúng đoạn/trang/ô nguồn, sửa và lưu dẫn xuất một lần, có bảo vệ xung đột phiên bản.
- Tiến độ theo công việc thực: bước hiện tại, số phần đã xong/đang chạy/lỗi, thời gian đã qua. Nếu chia thêm phần phải cập nhật mẫu số; không giả tiến độ phần trăm token/chất lượng.
- Có nút dừng; đổi trang/đóng popup không hủy tác vụ. Tải lại phải lấy trạng thái từ server, không phụ thuộc một Promise ở tab cũ.
- Nút “Gửi duyệt” đưa bản đã xác nhận vào hợp đồng đăng ký/submission hiện có qua preview/commit, quyền và idempotency. Không tự đăng ký/duyệt/xuất bản chỉ vì worker hoàn tất.
- Xuất bản kích hoạt đồng bộ chỉ mục hiện có. Chỉ báo sẵn sàng hỏi đáp khi binding/snapshot phiên bản mới thực sự phục vụ. Bản cũ được giữ hay bị thu hồi phải phản ánh đúng quyết định, không chỉ theo số gen lớn nhất.

## 4. Corpus kiểm tra đã tìm thấy trên máy

Chỉ ghi manifest/hash trong Git; không thêm lại các file nguồn vào Git. Khi chạy phải kiểm tra hash lại, dừng nếu khác. Số trang có text dưới đây chỉ là kiểm tra sơ bộ, không chứng minh lớp text đủ hoặc đúng.

| ID | File trong `docs/tai_lieu/tuyen_sinh/` | Kiểm tra đọc được ngày lập | Mục tiêu |
|---|---|---|---|
| D01 | `Phuong huong tuyen sinh 2024_DHQN_final.docx` | 4 bảng XML, 1 section | DOCX trực tiếp, vai trò năm, bảng |
| D02 | `tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).docx` | 10 bảng XML, 5 section | Ô gộp, cấu trúc khó, nguồn nhiều section |
| D03 | `Thông tin TSĐH cập nhật.pdf` | 14 trang, 14 trang có text | Phương thức tuyển sinh, bảng/ngưỡng/năm |
| D04 | `Quy chế tuyển sinh đại học 2026 - 363.pdf` | 32 trang, 0 trang có text | MinerU toàn tài liệu, nối trang, điều kiện/ngoại lệ |
| D05 | `TB điểm sàn 26.pdf` | 8 trang có text | Bộ F01–F19 và bảng điểm |
| D06 | `Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed.pdf` | 13 trang có text | Phân biệt mùa tuyển sinh/phương thức |
| D07 | `Báo cáo công tác Tư vấn tuyển sinh năm 2024_FINAL (1)_signed_signed-signed.pdf` | 7 trang có text | Báo cáo, thống kê, năm khảo sát |
| D08 | `tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).pdf` | 18 trang có text | Đối chiếu nội dung tương ứng D02 và tuyến PDF |

D02 và D08 phải nằm ở hai kho/biến thể riêng khi đo tuyến đọc, không cùng nạp để vô tình có hai bản trả lời một câu. Chỉ so các phần thật sự tương đương sau khi kiểm nguồn; không giả bản PDF khớp DOCX chỉ vì cùng tên.

### Bộ câu hỏi và nhãn

1. Tái dùng 53 câu hiện có trong `admissions-multi-docs.json`; F01–F19 đã nằm trong 53, không cộng lại. File đang ghi nhãn `draft_agent_read_pdf_not_human_approved`, nên chưa phải gold độc lập đã duyệt.
2. Bổ sung 24 câu phát triển: D01 4, D02 6, D03 6, D04 8; có câu liệt kê đầy đủ, bảng nhiều năm, footnote/ngoại lệ, mốc hiệu lực, hỏi nối tiếp và thông tin không có.
3. Khóa thêm 20 câu giữ lại để nghiệm thu, do người kiểm tra độc lập viết/duyệt sau khi chốt chính sách. Tránh trùng câu có sẵn trong tài liệu mẫu Q&A và tránh chỉ đổi vài từ của câu tuning.
4. Tổng mục tiêu **97 câu/biến thể**: 77 phát triển + 20 holdout. Có thể phải chỉnh scope/nhãn khi corpus kết hợp có thêm dữ kiện; một câu “không có dữ liệu” ở kho đơn không mặc nhiên negative ở kho nhiều tài liệu.
5. Mỗi câu có ID, phạm vi tài liệu/năm, đáp án hoặc hành vi kỳ vọng, nguồn gốc/trang/đoạn/ô, các ý phải đủ, số liệu/đơn vị/ngoại lệ, người và phiên bản duyệt. Tránh chấm đúng chỉ vì regex thấy một con số.
6. D08 dùng phần nhãn tương đương D02 như phép đo parser riêng; không đếm thêm vào 97 để phóng đại bộ câu hỏi độc lập.

## 5. Thứ tự thực hiện và cổng kiểm tra

| Gói | Công việc phải hoàn tất | Cổng chuyển bước |
|---|---|---|
| G0 — Đóng baseline | Ghi commit/diff; lưu manifest model/corpus; xác nhận build/reasoning/slot Qwen; rà runner và nhãn | Probe đúng capability, không lộ key; mọi unknown được ghi rõ; phạm vi thử độc lập đã chốt |
| G1 — Backend tự động | Chính sách chuẩn bị, reuse, canonical + AI riêng, kiểm tra chất lượng, checkpoint và dừng | Regression API/worker đạt; không mất nguồn hay đổi model; ranh giới quyền giữ nguyên |
| G2 — Giao diện | Một nút chuẩn bị, màn kết quả chung, sửa/lưu/gửi duyệt, nền và trạng thái lỗi | Test hành vi và trình duyệt đạt; không còn bắt người dùng chọn kỹ thuật |
| G3 — Vòng đời | Gửi sửa/duyệt/xuất bản, tự sync, bản cập nhật/thu hồi và dẫn chứng cũ | Chỉ phục vụ bản hợp lệ, không ready giả, không kích hoạt snapshot cũ |
| G4 — Model thật | Đọc đủ 8 nguồn; benchmark so sánh cùng Qwen; chấm 97 câu; kiểm bảng/OCR | Đủ record và nhãn; đạt các gate chất lượng §7; có báo cáo chẩn đoán từng câu lỗi |
| G5 — Tốc độ và độ bền | Đo concurrency/cache; đổi trang/mạng/ngắt worker/dừng trên kho thử | Không gọi trùng hay mất dữ liệu; đo đủ latency và tải; đạt mục tiêu §8 |
| G6 — Pilot và chốt | 3–5 người, T1–T6 của runbook 46, sửa trở ngại và lưu biên bản | Không còn blocker, đạt tiêu chí người dùng; quyết định triển khai tách riêng |

Mỗi gói bàn giao: diff, test thực chạy, artifact, PASS/FAIL/NOT RUN, lỗi còn lại và quyết định chuyển bước. Không báo “đã hoàn tất” chỉ vì code đã viết hoặc có một lần chạy xanh.

G1–G3 bắt đầu bằng đối chiếu phần KH15 đã có; chỉ triển khai khoảng trống, không viết lại chức năng đã đạt. Việc lập nhãn/chạy benchmark thuộc đội triển khai và người kiểm tra chuyên môn, không trở thành biểu mẫu kỹ thuật cho cán bộ sử dụng hằng ngày.

### Phạm vi mã dự kiến

- `backendV1/qnu/domains/knowledge/preparation/`: ý định/policy/ghim đầu vào/reuse/tiến độ/dừng.
- `backendV1/qnu/domains/knowledge/compilation/`: bản nguồn và bổ sung AI, kiểm tra/chia phần lỗi; không tạo compiler mới song song.
- `backendV1/qnu/domains/ocr/`: chỉ sửa khi test chứng minh đọc nguồn sai; giữ Docling/PDF Inspector/MinerU đúng nhiệm vụ.
- `backendV1/qnu/domains/modelops/`: chỉ sửa hợp đồng được xác minh với llama.cpp hoặc đường gọi bỏ qua chính sách, không đổi model mặc định âm thầm.
- `frontendV1/src/features/knowledge/`: hộp chuẩn bị, kết quả, nền và gửi duyệt; tái dùng màn sửa/nguồn và query keys hiện có.
- `frontendV1/e2e/`, `backendV1/tests/`, runner/báo cáo hiện có: mở rộng kiểm thử; không thay assertion để làm xanh.

## 6. Thiết kế phép so sánh công bằng

**A — baseline đóng băng:** luồng KH15 hiện tại với chế độ nguồn. **B — đề xuất:** chuẩn bị tự động, canonical giữ nguồn + AI bổ sung theo chính sách đã chốt. Có thể lấy biên soạn AI toàn phần làm tham chiếu phụ trên vài tài liệu; không bắt buộc chạy lại tất cả chỉ để tăng số lượt gọi.

Để đo riêng ảnh hưởng bước chuẩn bị, A/B dùng cùng kết quả đọc nguồn bất biến, cùng Qwen/embedding/rerank, prompt trả lời, cấu hình retrieval, query set, quyền và snapshot đầu vào. Index đầu ra có ID khác thì ánh xạ gold theo source spans đã kiểm chứng, không sao chép chunk ID giữa hai index.

Đo tuyến đọc/cold end-to-end riêng: upload → trích xuất → chuẩn bị → người xác nhận → xuất bản → sync → hỏi. Không trộn số đo reuse vào số cold, hoặc chỉ đo compiler rồi gọi là tổng thời gian tài liệu.

- Chạy smoke 6 câu đại diện trước để phát hiện hỏng hạ tầng/hợp đồng, lưu ở cohort riêng, không tính vào báo cáo 97 câu.
- Mỗi biến thể chạy 97 câu lần đầu: tổng **194 kết quả chính**. Câu độc lập mở hội thoại mới; chuỗi follow-up giữ đúng hội thoại được chỉ định. `retries=0`, không thêm recovery loop để đổi đáp án.
- Split do token là cơ chế sản phẩm cần quan sát, không xóa khỏi số đo first-pass. Báo riêng thành công không split, thành công sau split hợp lệ, lỗi và uncertain.
- Lỗi chất lượng độc lập: chấm và tiếp tục câu khác. Lỗi hệ thống/chính sách làm hỏng thí nghiệm: dừng, giữ record đã chạy, đánh dấu phần còn lại NOT RUN. Sau sửa tạo cohort mới có liên kết lỗi cũ, không ghi đè báo cáo.
- Qwen không tự làm giám khảo duy nhất cho câu trả lời của chính nó. Dùng kiểm tự động cho số liệu/citation và người đọc nguồn chấm correctness/completeness. Nếu chưa có người duyệt, báo kết quả kỹ thuật sơ bộ, chưa nghiệm thu ngữ nghĩa.
- Nếu cần chọn retrieval mode, chạy thí nghiệm riêng dense/hybrid/hybrid+rerank trên một snapshot. Hybrid và hybrid+rerank dùng cùng fusion candidates. Không đồng thời đổi K/model/chunk rồi gán mọi cải thiện cho luồng chuẩn bị.

### Rà runner trước khi tái sử dụng

`admissions-chat.ts` hiện có báo cáo first-attempt, nhưng còn ghi `semantic_review: NOT_RUN` và preflight so `chunk_max_bytes + query bytes` trực tiếp với token limit rerank. Cần đối chiếu/chỉnh phép dự toán theo hợp đồng token thực, không đồng nhất byte với token; lỗi này phải có regression, không chỉ bỏ guard. Runner 53 câu hiện có không bao phủ PreparationIntent mới, nên cần bổ sung đường E2E đi qua nút chuẩn bị/gửi duyệt/sync tự động.

API evaluation hiện nhận tối đa 20 query/lần; chia batch có ID ổn định và đối soát tổng 97. Không dùng Sheet “Kiểm thử” tối đa 3 câu làm bằng chứng đã chạy toàn benchmark.

## 7. Tiêu chí chất lượng nghiệm thu

Các ngưỡng sau là **mục tiêu đề xuất phải khóa trước G4**, chưa phải số đo. Đạt trung bình không được che lỗi sai số liệu/phạm vi quan trọng.

| Hạng mục | Điều kiện chấp nhận |
|---|---|
| Quyền, nguồn và phiên bản | 0 ca vượt quyền; 0 draft/withdrawn lọt phục vụ; 0 ready giả hoặc âm thầm đổi model |
| Bảo toàn từ canonical sang bản chuẩn bị | 100% đơn vị thiết yếu được giữ/ánh xạ; mọi loại bỏ/trùng có lý do; 0 số liệu/đơn vị/điều kiện bị AI sửa âm thầm |
| Đọc văn bản/bảng | Đối chiếu tập kiểm đã duyệt: 100% giá trị và điều kiện quan trọng; ≥99% ô mẫu đúng nội dung/vai trò hàng-cột; không mất ô rỗng, header/footnote và quan hệ nối trang |
| OCR tiếng Việt | Đối chiếu 8 trang mẫu đa dạng D04 và mọi vùng câu hỏi quan trọng; mục tiêu CER ≤1% trên bản chép đã duyệt; báo riêng lỗi dấu/ghép từ/số. Đây là số đo mẫu, không tuyên bố toàn bộ 32 trang chính xác 99% |
| Metadata | 100% giá trị dùng hard filter có evidence phù hợp; 0 nhầm năm dữ liệu với năm ban hành/hiệu lực; không có căn cứ thì unknown |
| Retrieval | Annotated Recall@20 ≥95% trên câu answerable có nhãn; báo từng nhóm nguồn, candidate/context recall riêng; câu liệt kê chấm độ phủ tập ý, không thay bằng Hit@K |
| Trả lời | Ít nhất 93/97 câu đúng và đủ theo rubric; từng nhóm có câu đạt ≥90%. Làm tròn số câu đạt lên theo mẫu số nhóm; báo cả phân số và % |
| Sai dữ kiện quan trọng | 0 lỗi bịa số/nhầm ngành, năm, đơn vị, điều kiện bắt buộc hoặc ngoại lệ trọng yếu; gặp một ca phải xử lý trước khi chốt |
| Dẫn chứng | 100% dẫn chứng mở được trong quyền hợp lệ; ≥98% mệnh đề có nguồn được dẫn hỗ trợ đúng; 100% mệnh đề quan trọng có nguồn đúng |
| Thiếu nguồn/mâu thuẫn | 100% ca ranh giới không bịa; trả lời phần có căn cứ và nêu thiếu gì, hoặc làm rõ/từ chối theo rubric. Không dùng “không có dữ liệu” để che lỗi provider |
| So sánh A/B | B đạt ngưỡng tuyệt đối, không giảm số câu đạt so A, không phát sinh lỗi quan trọng; công bố từng cặp tốt hơn/kém hơn, không suy ý nghĩa thống kê từ vài câu |
| Tính đầy đủ báo cáo | Mỗi query/strategy đúng một record, không missing/duplicate; 97/97 đã chấm mỗi biến thể; NOT RUN/uncertain/error không bị loại khỏi mẫu số |

Tám trang OCR mẫu nên phủ đầu/giữa/cuối, chữ nhỏ, dấu mờ, bảng và nối trang. Chạy xử lý đủ 32 trang; độ bao phủ trang và chất lượng chữ là hai phép kiểm khác nhau.

Với corpus Q&A đã chứa câu trả lời, tách điểm original/paraphrase và holdout độc lập để tránh kết luận chất lượng cao do khớp lại câu nguồn.

## 8. Tốc độ: đo trước, tối ưu có căn cứ

- DB/cấu hình local hiện đọc được: compiler concurrency 2, Chat admission 4. Không tự tăng; hiệu lực tổng còn phụ thuộc slot/load gateway llama.cpp. Nếu tổng vượt server thì xếp hàng có trạng thái, không đẩy thêm rồi hết thời gian chờ.
- Tách thời gian hàng đợi, Docling/PDF Inspector/MinerU, bổ sung AI, ghi bản, review nếu có, embedding, retrieval/rerank và sinh câu trả lời. Ghi prompt/completion/total/reasoning token đúng trường đo; thiếu thì null. Byte không phải token.
- Ghi TTFT chỉ khi nhận token đầu thật từ streaming; không streaming thì NOT MEASURED, không thay bằng lúc spinner xuất hiện. Thu timing/prompt-cache/throughput từ llama.cpp nếu endpoint cung cấp.
- Đo mức đồng thời 1 và 2 sau khi xác nhận slot cho phép; mức cao hơn chỉ thí nghiệm riêng có căn cứ. Ưu tiên để chat không phải chờ sau một đợt tài liệu dài.
- Mục tiêu UX local: nhận ý định và trả trạng thái nền p95 ≤2 giây; đổi tab xem nội dung đã có p95 ≤1 giây; bấm gửi hiện tin người dùng ≤200ms. Chậm phải chỉ ra stage, không fake progress.
- Mục tiêu so sánh: các stage có cùng công việc ở B không chậm hơn A quá 10% khi cùng chế độ cache. Tổng B có thêm AI/kiểm tra thì báo riêng phần tăng, không yêu cầu bằng đường A không gọi AI. So với baseline có AI toàn phần, đặt mục tiêu giảm ≥30% thời gian chuẩn bị có AI mà không giảm chất lượng; chỉ kết luận khi có baseline tương ứng.
- Đo lặp có kế hoạch cho hiệu năng (warmup riêng, ít nhất 10 mẫu cho stage nhỏ; p50/p95 kèm cỡ mẫu). Với tài liệu lớn chỉ vài lần chạy, báo thời gian từng lần/min-max, không quảng bá p95 đáng tin. Lặp đo tốc độ không được dùng chọn đáp án tốt nhất cho benchmark.
- Chốt SLO tuyệt đối cho từng loại/kích thước tài liệu sau G0 từ tốc độ server thực tế; khóa trước lượt nghiệm thu. Không hứa mọi file xong trong cùng 60/300 giây. Chưa có SLO đã khóa thì chưa chốt gate hiệu năng.

## 9. Ma trận kiểm tra độ bền và vòng đời

Mô phỏng hỏng provider/queue và lỗi token trên môi trường thử bằng adapter được kiểm soát; không tắt server Qwen/MinerU đang dùng chung để tạo lỗi. Unit/fake chứng minh hành vi, còn G4 mới chứng minh model thật.

| Ca | Kỳ vọng bắt buộc |
|---|---|
| Bấm chuẩn bị hai lần/giao job trùng | Một intent công việc, không có hai inference cho cùng phần |
| Đổi trang, đóng popup, tải lại | Worker tiếp tục, UI lấy lại đúng tiến độ và kết quả |
| Redis gián đoạn trước dispatch | Ý định đã lưu còn; reconcile tiếp tục đúng bước chưa gửi |
| Worker chết trước/sau khi gửi model | Phân biệt chưa gửi với uncertain; không tự gửi lại phần có thể đã chạy |
| Dừng khi có hai phần đang chạy | Không nhận phần mới; kết quả phần đã xong còn; trạng thái upstream trung thực |
| Người dùng sửa nguồn khi đang chuẩn bị | Lượt cũ giữ đúng hash đã ghim hoặc báo xung đột; không trộn hai phiên bản |
| Lỗi output/context xác định | Chỉ chia phần lỗi, lưu cây phần cha/con; không chạy lại phần đã xong |
| Hạ tầng/quota/quyền/model bị tắt | Báo đúng lỗi, không chia nhỏ/fallback ngầm/no-data giả |
| Gửi duyệt/lưu sửa/xuất bản trùng | Idempotent; kiểm quyền và version/hash/sequence ở server |
| Xuất bản xong nhưng sync lỗi/chưa xong | Giữ quyết định xuất bản; báo trạng thái phục vụ riêng; không ready giả |
| Bản cập nhật/thu hồi trong lúc build | Không switch vào snapshot đã lỗi thời hoặc phục vụ phần thu hồi |
| Dẫn chứng cũ sau thay bản/đổi quyền | Kiểm lại quyền/vòng đời khi mở, báo đúng lý do không khả dụng |

## 10. Bộ kiểm chứng mã nguồn và trình duyệt

Tái dùng test hiện có trước khi thêm test: `test_preparation_intents.py`, `test_compiler_supplement_879.py`, `test_publication_index_sync_878.py`, `test_assistant_readiness_p6.py`, test review submission và các contract/query isolation FE. Kiểm tra tên file thực trước khi đặt lệnh; bổ sung regression cho auto policy, ngắt/hủy, đơn vị byte/token và provenance.

Lệnh hiện có chạy từ root trong PowerShell, **sau khi mã triển khai ổn định**:

```powershell
.\make.ps1 check
.\make.ps1 test-be
.\make.ps1 test-fe
.\make.ps1 build
```

`check` chỉ kiểm phụ thuộc, không chứng minh chất lượng model. Backend phải đi qua harness tạo DB thử `qnu_v1_test_*`; không chạy Pytest vào DB ứng dụng. Lint chạy có phạm vi tệp sửa. Full backend/frontend gate chạy một lần sau batch; chỉ lặp khi có thay đổi/lỗi cần giải quyết. Bộ nền còn fail phải ghi exact test IDs và trạng thái tổng FAIL.

Playwright mới đi qua giao diện `3001` hoặc cổng của phiên thử được cấp, có API/worker thật và provider ModelOps thật trong G4. Không chạy `clear`, cleanup/init E2E hoặc tắt dev đang chạy để lấy môi trường. Workspace/kho nghiệm thu, queue/cache/storage/index namespace và người thử phải độc lập, có quyền cấp provider qua ModelOps; không sao chép credential ra report. Không dùng `test-v1-e2e.ps1` cũ như thể nó đã bao phủ luồng KH15.

Ma trận UI: 390/768/1280px, sáng/tối, editor/reviewer/admin/member; focus/phím, nút dừng, lưu xung đột, tải lại, lỗi/trống và mở dẫn chứng. Xem ảnh thực, không chỉ kiểm không có console error.

## 11. Báo cáo cần bàn giao và cách tìm đúng tầng lỗi

Artifact lưu ngoài Git tại `tmp/v1-user-workflow-eval/<cohort>/` hoặc nơi artifact cấu hình. Không chép corpus, key hay response riêng tư vào tài liệu công khai. Manifest chỉ ghi fingerprint và đường dẫn artifact được bảo vệ.

| Artifact | Nội dung |
|---|---|
| `model-manifest.json`, `corpus-manifest.json` | Danh tính runtime/config/nguồn/hash và unknown |
| `extraction-audit.json` | Khối/trang/ô cần có, tìm thấy, lỗi và đối chiếu |
| `preparation-audit.json` | Canonical retention, đề xuất AI, metadata, split/reuse và phần chưa hoàn tất |
| `answers-A.jsonl`, `answers-B.jsonl` | Mỗi câu một record, citations, coverage/thiếu ý, trạng thái, token và thời gian |
| `semantic-review.jsonl` | Rubric, người duyệt, nhãn đúng/đủ/sai nguồn/sai năm và căn cứ |
| `lifecycle-report.json`, `ui-report/` | Negative tests, trạng thái phục vụ, ảnh và phép đo UI |
| `summary.md` | Chất lượng theo nhóm, A/B, độ trễ/cỡ mẫu, lỗi, giới hạn và quyết định |

Truy vết một câu lỗi theo thứ tự: **nguồn gốc → bản đọc canonical → bản chuẩn bị → publication/index binding → retrieval candidates → context thực gửi → câu trả lời/citation**. Nếu dữ kiện không vào canonical thì sửa parser/OCR; có canonical nhưng mất khi chuẩn bị thì sửa compiler; có trong index nhưng không vào context thì sửa RAG/budget; context đủ mà trả sai thì sửa generation/verification. Không sửa tất cả tầng cùng lúc hay tăng TopK mù.

## 12. Điều kiện hoàn thành

- [ ] G0 xác minh được Qwen llama.cpp, provider khác và manifest an toàn; không gán thông tin cũ thành quan sát mới.
- [ ] G1–G3 hoàn thiện một luồng, giữ quyền/nguồn/duyệt và tự sync; không thêm thao tác kỹ thuật cho cán bộ.
- [ ] Gate mã nguồn/trình duyệt có receipt, không bỏ qua lỗi nền.
- [ ] 8 tài liệu được kiểm đủ đường đọc; 97 câu × 2 biến thể có record và nhãn; holdout độc lập được duyệt.
- [ ] Đạt §7, §8 và ma trận §9; mọi câu lỗi có tầng nguyên nhân và báo cáo trước/sau sửa.
- [ ] Pilot 3–5 người thực hiện T1–T6: ≥80% hoàn tất tác vụ thông thường không cần dev chỉ đường; không S1, không S2 chặn công việc; phân biệt thời gian thao tác/chờ.
- [ ] Biên bản nêu rõ phạm vi đã chứng minh và giới hạn; production rollout được quyết định riêng, không tự deploy/push/reset.

Các checkbox trên hiện **chưa được đánh dấu hoàn thành**. Phiên lập kế hoạch chỉ kiểm cấu hình DB và manifest file bằng thao tác đọc; chưa gọi model thật, chưa chạy test sản phẩm mới hoặc pilot.
