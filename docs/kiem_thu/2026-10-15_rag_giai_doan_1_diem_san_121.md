# Giai đoạn 1 - Chẩn đoán RAG điểm sàn, sau reset DB

Ngày: 2026-10-15. Phiên 466. Chỉ chẩn đoán, tạo công cụ trace và regression;
**chưa sửa runtime, bật policy, đổi model/max_tokens hoặc lập chỉ mục lại**.

## 1. Phương pháp và phạm vi

- Đọc DB đang cấu hình bằng transaction `READ ONLY`; phân giải lại ID/snapshot sau reset.
- Đọc và render PDF trên máy, không OCR lại/ghi đè nguồn. Đã xem trang 1, 2, 7, 8.
- Kiểm tra SHA-256 binary trùng `origin_file_hash` của đúng nguồn đang xuất bản.
- Thực hiện 2 câu hỏi qua **service trợ lý thực**, cùng đường gọi của API chat nhưng
  chạy trong tiến trình chẩn đoán để quan sát tham số/kết quả của từng tầng.
  Không phải kiểm thử HTTP transport, đăng nhập hoặc giao diện.
- Các wrapper chỉ quan sát và gọi nguyên hàm gốc, không thay nội dung trả về,
  không gửi đáp án chuẩn cho model, không thay chính sách/model/corpus.
- Chạy trong sandbox trước: embedding/chat không kết nối được, cả 2 ca lỗi
  `ALL_PROVIDERS_UNAVAILABLE`. Đã loại lượt này khỏi đánh giá chất lượng.
- Đọc catalogue model ngoài sandbox được HTTP 200; chạy lại 2 ca ngoài sandbox,
  embedding và reranker có phản hồi thật. Lượt này là baseline hợp lệ.
- Các lượt chat tạo hội thoại/usage/key-health/circuit-breaker bình thường.
  Có 4 hội thoại test: 2 lỗi sandbox và 2 baseline. Không xóa log của chúng.

Không test 20/82 câu, không migration/seed/reset/restore/purge/reparse/reindex/publish.
Không đụng `docs/tai_lieu`, Git index, commit, push hoặc deploy.

## 2. Định danh corpus mới

| Trường | Giá trị quan sát |
| --- | --- |
| Trợ lý / collection | admissions / col_admissions |
| Tenant / workspace | tenant_qnu / workspace_qnu |
| Số binding xuất bản | 21, đều active ở thời điểm kiểm tra |
| Epoch / snapshot fingerprint | 2 / c61c923b10b4f8f1aa58 |
| Nguồn đích | TB điểm sàn 26.pdf |
| Binding | bnd_e4b071bb147f |
| Source revision | ks_rev_73ea05d14446 |
| Index revision | idx_rev_a443d796d020 |
| PDF SHA-256 | 236ab3573d6d683a760ed227512022d6c21a03ba5c147c32d4ed7b042f7c6d45 |
| Canonical SHA-256 | cc91c629659b85b2fcebb778bc8fdbb00d8b21fd2941312bd51565028d9eb23c |
| Nội dung nguồn | 8 trang, canonical 17.030 ký tự, 86 chunks, 284 facts |
| Review | auto_ready, artifact issues rỗng |

Đã kiểm tra lại trực tiếp Qdrant: **86/86 point ID + revision + content hash khớp**.
Không chỉ dựa vào parity report lưu lúc publish. Không gọi embedding/upsert trong phép đối soát này.

### Cấu hình thực tế sau reset

- `execution_mode=rag`, **`knowledge_policy.evidence_policy.enabled=false`**.
- Nhánh đang chạy: `RagService.ask` legacy classifier/fact lookup/hybrid/generation;
  **không chạy** QueryPlan/BM25 evidence/independent semantic audit/historical-reference
  của `answer_with_evidence`. Đây là khác biệt quan trọng với audit kiến trúc trước reset.
- Primary: provider `prov_rtx5090_vllm`, model `qwen3.5-9b`.
- Fallback: provider `prov_cloudflare`, model `@cf/meta/llama-3.1-8b-instruct`.
- max_tokens 5.000; reranker cấu hình top_k 5, threshold 0,4.
- Chỉ ghi nhận cấu hình; không tự bật evidence policy hoặc đổi các tham số trên.

## 3. Đáp án chuẩn theo PDF, không theo trí nhớ/model

Trang 1 hiển thị **121/TB-HĐTS, Gia Lai ngày 09 tháng 7 năm 2026** và tiêu đề
ngưỡng bảo đảm chất lượng đầu vào tuyển sinh đại học chính quy năm 2026.

| Ngành | Mã | Trang hàng dữ liệu | Thi TN THPT | Kết quả học tập THPT | ĐGNL ĐHQG TPHCM | ĐGNL ĐHSP HN |
| --- | --- | --- | --- | --- | --- | --- |
| Quản lý giáo dục | 7140114 | 1 | 15 | 18 | 600 | 15 |
| Sư phạm Toán học | 7140209 | 2 | 20 | – | – | 20 |

Trang 8 giải thích ký hiệu “–” là trường không xét tuyển phương thức tương ứng
đối với ngành đó. Không suy luận ý nghĩa dấu này chỉ từ ô trống.

Khi trả lời Sư phạm Toán học qua ĐGNL ĐHSP HN, cần giữ điều kiện bổ sung ở Chú ý 2
trang 8: ngoài mức điểm bảng, có điều kiện kết quả học tập/lớp 12 và điểm thi hoặc
điểm xét tốt nghiệp. Chú ý 1 bắt đầu trang 7, nối sang trang 8. Đáp án nghiệm thu
không được biến ngưỡng bảng thành cam kết đủ mọi điều kiện hoặc chắc chắn trúng tuyển.

### Phần bóc tách đã đúng

- Hai hàng ngành, giá trị và tên bốn cột còn đầy đủ trong canonical/facts/chunks.
- PDF vật lý trang 2 không lặp header. Canonical trang 2 **đã có header kế thừa**.
- Hàng Giáo dục Thể chất tràn qua trang 1/2 đã được nối trong canonical, không lấy
  phần tràn đó làm header của hàng Sư phạm Toán.
- Do đó, không tái hiện được giả thuyết “mất toàn bộ header trang 2” cho nguồn này.

### Phần dữ liệu còn thiếu/sai ngữ nghĩa

- Native text trang 1 là `Số: /TB-HĐTS`, `Gia Lai, ngày tháng năm 2026`:
  mất số 121 và ngày/tháng hiển thị trong hình. `document_number` và `issued_date` null.
- Provenance cho biết `ocr_engine=native`, `parser_profile=standard`,
  `reused_artifact=true`; cả 8 trang hiện ghi engine native. Chưa OCR rescue.
- Không thể vá metadata bằng suy đoán từ tên file hoặc chọn một ngày căn cứ pháp lý.
- Các facts hàng đích đều `applicability_year=null`, `qualifiers.method=null`.
  Năm 2026 nằm ở phần giới thiệu, không nằm trong từng header cột.
  Đây là chỗ cần liên kết căn cứ phạm vi, **không được gán năm ban hành cho mọi ô**.
- Ba cột có chữ “điểm” bị nhãn nội bộ `cutoff_score`; cột kết quả học tập THPT có
  giá trị 18 bị nhãn `admission_method`. Nhãn gốc/giá trị ô vẫn còn, nhưng mã ngữ nghĩa sai.

## 4. Baseline hai câu và chuỗi nguyên nhân

### A. Quản lý giáo dục

- Hội thoại: `stage1_466_0bdd89b236594216`.
- Tổng thời gian service: 2.021,11 ms; response latency: 1.882,16 ms.
- Trả `answered`: “điểm sàn ... là 15 điểm”, không tách bốn phương thức.
- Đánh giá thủ công: **không đạt đầy đủ**. 15 là một mức đúng nhưng không đại diện
  cho học bạ 18 và ĐGNL ĐHQG TPHCM 600. Chưa đủ căn cứ từ trace để nói model
  thực sự lấy 15 từ hàng nguồn nào.
- Classifier: intent mixed, nhận tên ngành nhưng không có entity code và
  `fact_attributes=[]`; không đi qua gate số liệu theo năm.
- Lookup facts giới hạn 5 trả mã ngành/chỉ tiêu/phương thức/tổ hợp ở các tài liệu khác,
  có cả Quản lý nhà nước; không trả ô nào của nguồn điểm sàn.
- Dense top12 **có đúng hàng Quản lý giáo dục ở hạng 11**. Lexical top12 và variant
  `bao nhiêu năm 2026` không có nguồn điểm sàn.
- Sau fusion/rerank top5, nguồn điểm sàn chỉ còn đoạn Chú ý trang 8, không còn hàng đích.
- Prompt cuối chứa facts cũ và các hàng điểm trúng tuyển 2023–2025; không có hàng
  ngưỡng 15/18/600/15 để trả đủ phương thức.

**Điểm mất trực tiếp:** hàng đúng đã tìm được trong dense nhưng rơi trước context cuối;
fact lookup cũng không cứu được hàng đó.

### B. Sư phạm Toán học

- Hội thoại: `stage1_466_785f2ab3d0154c2f`.
- Tổng thời gian service: 1.921,52 ms; response latency: 1.837,01 ms.
- Trả `answered` nhưng nội dung nói “thông tin về điểm sàn năm 2026 không được cung cấp
  trong các tài liệu đã trích dẫn”, rồi đề nghị thông tin điểm trúng tuyển năm cũ.
- Đánh giá thủ công: **không đạt**. Hàng nguồn đang xuất bản có 20/–/–/20.
- Classifier có mã 7140209 nhưng vẫn `fact_attributes=[]`.
- Fact lookup giới hạn 10 không lấy ô của thông báo điểm sàn; có tổ hợp ngành khác.
- Dense top8, lexical top8 và variant top4 đều không có nguồn điểm sàn. Top5 cuối
  là flyer/phương thức và bảng điểm trúng tuyển năm cũ, không phải ngưỡng đầu vào.
- Prompt cuối không có hàng Sư phạm Toán 20/–/–/20.
- `is_refusal_answer()` trả false ngay khi `has_evidence=true`; citation overlap và
  numeric grounding không kiểm tra đủ tính trả lời đúng câu hỏi. Vì còn citation,
  một câu không trả lời số liệu vẫn bị ghi `answered`.

**Điểm mất trực tiếp:** candidate generation/fact selection không lấy được hàng hiện có;
đồng thời nhãn trạng thái che mất việc câu hỏi chưa được trả lời.

### C. Model chính bị lỗi context ở cả hai câu

- Primary vLLM trả HTTP 400: cửa sổ context 8.192 token, yêu cầu 5.000 output và
  báo input tối thiểu 3.193, tổng tối thiểu 8.193 vượt giới hạn.
- Đây là thông báo thực từ provider, không phải phép ước lượng token bằng ký tự.
- Cả hai câu được phục vụ bởi Cloudflare fallback, không phải Qwen chính.
- Một service `generate`/câu ở nhánh này; mỗi lần có primary thất bại rồi fallback.
  Served token counts của fallback: 4.145+55 và 4.644+89.
- Prompt thực khoảng 10k–11k ký tự; không suy ra context window từ con số 5.000.
- Không thể kết luận thiếu ý chỉ vì model nhỏ/context: **hàng nguồn đã vắng khỏi
  prompt**, tăng context hoặc output budget riêng lẻ không khắc phục nguyên nhân đó.

## 5. Regression và kiểm chứng

Thêm fixture văn bản nhỏ trích đúng canonical hai hàng, không thêm PDF/ảnh lớn vào Git.
Fixture giữ header trang 2 được parser bổ sung; không giả làm header in trong bản gốc.

- Chạy `--runxfail`: **5 passed, 4 failed**. Bốn lỗi đúng mục tiêu:
  1. Hai câu điểm sàn không được nhận là câu số liệu theo năm (2 ca).
  2. Cột điểm kết quả học tập bị gán là định danh phương thức (1 ca).
  3. Có citation thì câu không trả lời bị coi không phải refusal (1 ca).
- Đánh dấu bốn lỗi mở bằng `xfail(strict=True)` cho giai đoạn chẩn đoán. Đây **không phải
  sửa lỗi/pass sản phẩm**; `--runxfail` tái hiện đỏ và khi được sửa sẽ XPASS để bắt bỏ marker.
- Focus gồm fixture mới, source units, temporal contract, table reconstruction/stitching:
  **78 passed, 4 xfailed trong 6,53 giây**.
- Ruff có phạm vi và toàn Backend: đạt (có cảnh báo quyền đọc artifact cũ). Full-suite/FE build không chạy: chỉ thêm công cụ chẩn đoán,
  fixture và test; không có runtime fix để nghiệm thu toàn hệ thống.
- DB snapshot/config/source+facts+chunks/collection-metadata fingerprints trước-sau
  hai ca baseline không đổi. Chưa chứng minh toàn DB không đổi (có log test bình thường).

## 6. Artifact và cách chạy lại

- Công cụ: `backend/scripts/audit_rag_floor_stage1.py`.
- Test: `backend/tests/test_rag_floor_stage1_466.py`.
- Fixture: `backend/tests/fixtures/rag_floor_121_excerpt.md`.
- JSON trace đầy đủ (local, không stage): `backend/storage/rag_stage1_466_verified/report.json`.
- Render nguồn (local): `backend/storage/rag_stage1_466_verified/page_{1,2,7,8}.png`.
- Lượt mạng sandbox loại trừ: `backend/storage/rag_stage1_466_live/report.json`.
- JUnit focus: `backend/storage/pytest466_focus.xml`.

Chạy từ backend, bằng Python của venv đã cài dependency:

```powershell
.\.venv\Scripts\python.exe -m scripts.audit_rag_floor_stage1 --output storage/rag_stage1_next
# Chỉ khi muốn tạo 2 lượt chat thật, dùng mạng/provider thật:
.\.venv\Scripts\python.exe -m scripts.audit_rag_floor_stage1 --live --output storage/rag_stage1_next_live
.\.venv\Scripts\python.exe -m pytest tests/test_rag_floor_stage1_466.py --runxfail -q
```

Không dùng lại tên output cũ nếu cần giữ lịch sử. Tool phân giải ID mới sau reset,
kiểm tra checksum nguồn và dừng khi snapshot/config khác giữa các ca. Không bật policy
khác để làm đẹp baseline. Thời gian 2 ca không phải benchmark p95 hoặc độ chính xác 82 câu.

## 7. Điều chỉnh ưu tiên cho giai đoạn sau - CHƯA THỰC HIỆN

1. Giữ các kiểm thử bảng đang đúng. Sửa OCR rescue metadata nhỏ và liên kết scope/
   loại thuộc tính thay vì viết lại toàn parser vì giả định mất header trang 2.
2. Chốt cấu hình có chủ đích sau reset: có bật evidence pipeline cho trợ lý hay không.
   Không sửa một nhánh đang không chạy rồi coi là đã chữa được chatbot.
3. Sửa chọn facts/candidates theo entity+metric+scope trước LIMIT; không để dữ liệu
   thiếu năm thắng mặc định hoặc lọc sạch dữ liệu có thể chứng minh phạm vi từ nguồn.
4. Kiểm soát window input+output theo ModelOps/provider; không nâng max_tokens mù quáng.
5. Kiểm chứng completeness/status và citation theo câu hỏi, không chỉ word overlap/số xuất hiện.

Giai đoạn 1 đã có đối soát nguồn, trace hai ca, baseline và regression mở. Các lỗi trên
còn nguyên để sửa ở giai đoạn tiếp theo sau khi duyệt; chưa cam kết độ chính xác tổng thể.
