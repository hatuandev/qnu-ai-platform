# Phiên 515 — Thử bản sạch trên DOCX đang có trong kho

## Kết luận

Đã thử đúng `QNU_TuyenSinh_2026_VanBanThuyetMinh.docx` theo lựa chọn người dùng.
Bản canonical đang phục vụ đã sạch theo cleaner hiện tại; không thay đổi một
ký tự. Chunker mới tạo đúng cùng multiset nội dung59 đoạn, nên **giữ publication
cũ**, không chuyển active chỉ để tạo thay đổi. Có index staging mới với seal
toàn vẹn, chưa xuất bản. Không reset DB hoặc sửa21 nguồn khác.

## Phạm vi và phương pháp

- Skill ingestion: giữ bytes gốc, canonical/hash, trang/nguồn và trạng thái duyệt;
  không tự chỉnh dữ kiện hoặc giả phê duyệt. Skill RAG/evaluation: cùng collection,
  nguồn, embedding, reranker, Top K và5 câu; chỉ thay index của một binding trong
  candidate snapshot. Đây là smoke retrieval, không phải benchmark đáp án.
- Binding `bnd_063df26142cb`, source revision `ks_rev_8f3c2063c14e`.
- Origin SHA256 `dc33e52e9cde23923130e12ab2b94690e0c54e8d672b425ff34aef9583374919`:
  bytes đọc từ StorageDriver khớp. Canonical SHA256
  `78598a325c3e36879b0e0d6f341c6af965dbd31c9c1657f822b2084e01babefd` khớp text DB.
- Native OOXML body có0 bảng; 3.985 word tokens. So multiset Word với Markdown
  bỏ marker trang: không thiếu/thêm token nào. Kiểm tra này không chứng minh thứ
  tự đọc/bố cục đúng; không đại diện cho tài liệu có bảng phức tạp hay OCR.
- Cleaner trả nguyên text, inspector không issue; artifact hiện có
  `structured-source-v6-source-units`, review state auto_ready, không yêu cầu
  duyệt thêm. Không sửa artifact sangv7 hoặc gán nhãn đã duyệt bởi con người.
- Giữ7 trang và mapping cũ; không render/revalidate page alignment trong phiên.
  Không tạo revision nội dung giả chỉ để ghi nhận một lần chuẩn hóa no-op.

## Dựng staging thật

Service `vector_generation_service.build_generation_for_source` chạy trên
generation hiện hành `vg_a6e3190d11af`; không gọi parser/OCR.

- Cũ: `idx_rev_21fe29be6449`, chunk set `chk_set_cc2977efe9b0`,59chunks.
- Mới: `idx_rev_89e750bde8bb`, chunk set `chk_set_cbededea47d9`,59chunks/0facts,
  trạng thái ready, không active.
- `derived-bundle-v1` hash:
  `3d3ed7ea058d190b509b17cb022baba3c479e80e507618b53a62b3d1ea34c561`.
- DB/Qdrant kiểm tra point IDs/revision/content hash:59expected/59verified,
  parity_passed=true. Candidate artifact/bundle validation PASS;59 source units
  có mặt đầy đủ. Max chunk882 ký tự trước và sau.
- Multiset chunk_hash cũ/mới giống nhau. Mã/ID mới khác, không phải nội dung tốt
  hơn. Không gán cải thiện câu trả lời cho seal hoặc lần re-embedding này.
- Runtime guard của lượt thử chỉ nhận provider `prov_rtx5090_vllm` và endpoint
  hiện có của server AI, không chỉ dựa tên model. Embedding thật `bge-m3`;
  không mở fallback cloud hoặc đổi cấu hình ModelOps.

## So sánh tìm kiếm thật

5 queries liên quan phương thức2026, năng khiếu, điều kiện sư phạm, hỗ trợ học phí/
sinh hoạt phí và xét tuyển thẳng; mỗi query chạy baseline/candidate đúng một lần.
Giữ toàn bộ22 nguồn, chỉ thay binding đã chọn trong candidate; không cô lập nguồn
để làm đẹp kết quả. Configured Top K20dense/20lexical/30fusion/5context giữ nguyên,
reranker `bge-reranker-v2-m3` nội bộ. Không gọi LLM sinh đáp án, không cache câu trả lời.

| Query | Vị trí tài liệu thử trong baseline Top5 | Candidate Top5 |
| --- | --- | --- |
| 1 | 1,2,4,5 | 1,3,4,5 |
| 2 | không có | không có |
| 3 | 1,2,5 | 1,2,5 |
| 4 | 1 | 1 |
| 5 | 1,2,5 | 1,2,5 |

10/10 requests có kết quả, không degradation; có CE scores thật, ID không lặp và
mọi hit thuộc đúng snapshot/index. Có đổi thứ hạng ở query1 dù text giống nhau;
không nói toàn bộ ranking giữ nguyên. Đây là document presence, **không phải**
nhãn đúng/sai của đáp án. Query2 không có tài liệu thử trong Top5 ở cả hai lượt;
không suy ra không có dữ liệu vì có các nguồn khác được trả về.

## Artifact và bảo toàn trạng thái

Prefix S3, từng object đã readback/hash:
`snapshots/markdown-trials/515/bnd_063df26142cb/`

- `before.json`, hash `544e02a683d0432bec333343828f6cf31e7c3ef7739c1d4a7155c4febeac1292`:
  pointer/epoch/status của mọi binding và source fingerprint.
- `canonical.md`, `source-revision.json`, `old-chunk-set.json`: bản đối chiếu cũ.
- `staging.json`, `new-chunk-set.json`: kết quả dựng thật/manifest mới.
- `retrieval-comparison.json`, hash
  `08799e0538da99d8ffb2a9fe15ab27a0e5b8a27867dc6b70defce5f7542d762a`:
  query, snapshot, policy, ordered hits/content/provenance và diagnostics thật.
- `completion.json`, hash
  `266f20871d91c88dbdacd6d5ea476b58a86b74e0b4666995038edff09aae2203`:
  kết luận KEEP_CURRENT_PUBLICATION_IDENTICAL_CHUNK_CONTENT.

Đọc lại cuối task: source/index/epoch/status của cả22binding giống before,
collection epoch4, generation không đổi. Chỉ tạo thêm chunk set/index/59points
staging cho một nguồn (và usage vận hành embedding/rerank); không xóa points cũ.
Không chuyển active, không chạy rollback; chưa chứng minh thao tác rollback thật.

## Lệnh và giới hạn

CWD `backend`, `.venv/Scripts/python.exe -` với inline orchestration qua service
hiện có: preflight/backup/build, retrieval A/B, native Word đối chiếu/completion,
đều exit0. Lần build đầu dùng sai đường import resolver nên exit1 trước khi
chạymain; sửa import theo mã thật rồi chạy thành công, không gọi model ở lần lỗi.

Không sửa production code, không chạy full pytest/build/UI cho task vận hành này.
Không sinh/chấm đáp án5–10câu, không chạy82câu, không tuyên bố chất lượng RAG tăng.
Không OCR, restart, migration, deploy, commit hoặc push. Model/Top K/prompt và tệp
`docs/tai_lieu` giữ nguyên. Skill giữ source/review gate; không duyệt ngầm nguồn.

## Bước tiếp theo

Muốn đo lợi ích làm sạch cần chọn một tài liệu hiện có thực sự có lỗi bảng/header/
OCR, không dùng tài liệu văn xuôi vốn đã sạch làm bằng chứng thành công. Đánh giá
đáp án chatbot5–10câu là bước riêng; phép thử retrieval ở đây chưa thay thế nó.
