# Phiên 528 — Đợt 4–6: dọn kho và nạp nguồn chuẩn

## Quyền và kết quả

Người dùng xác nhận **không cần sao lưu, cứ thực hiện**. Đây là ngoại lệ cho batch
này trong `col_admissions`, không phải thay chính sách sao lưu toàn app. Đã thông
báo việc xóa bản hiệu đính cũ không có bản backup để khôi phục. Không nhận mật khẩu.

- Dọn 22 nguồn/33 source revisions cũ qua pause → durable purge; xóa chunks/facts/
  points theo binding và namespace. Giữ audit activations/index tombstones; không
  xóa collection hay Repository. Ngay sau purge: 0 source revisions.
- Chọn 6 Repository documents, tạo lại 6 MD/JSON chuẩn; xác minh pair/checksum/
  binding/source hash thành công, tất cả dùng `qnu-rag-projection/v1`.
- Người dùng duyệt riêng DOCX revision `ks_rev_0c1e98ac424b` qua câu hỏi xác nhận.
  Đã duyệt bằng actor từ dependency server local, dựng vector và xuất bản riêng
  bản đó: `idx_rev_c482a9e11451`, 56 chunks, parity true, epoch50.
- 5 PDF **chưa duyệt/chưa nạp vector/chưa xuất bản** vì còn cờ cần đối soát.
  Không tự gán người duyệt, sửa số OCR hoặc gỡ guard để xuất bản.

## Danh mục sau nạp

| Nguồn | Revision | Khối | Ô bất định | Trạng thái |
|---|---|---:|---:|---|
| QNU_TuyenSinh_2026_VanBanThuyetMinh.docx | ks_rev_0c1e98ac424b | 56 | 0 | Đã xuất bản, không có issue |
| Cac nganh Tuyen sinh 2025_moi.pdf | ks_rev_a6a7a50d2bb0 | 152 | 665 | Chờ đối soát header, native/OCR conflict |
| TB điểm sàn 26.pdf | ks_rev_faf36025f7ab | 586 | 30 | Chờ đối soát header/ô/ngữ cảnh/nối bảng |
| TB học phí K49.pdf | ks_rev_bfe4b12cbf72 | 102 | 0 | Chờ đối soát header/nối bảng/vùng hình |
| Thong_bao_quy_doi_tuong_duong_QNU_2026_Chinh thuc-signed.pdf | ks_rev_c041d878ae7e | 528 | 0 | Chờ đối soát header/nối bảng/vùng hình |
| Hương dan thi Nang khieu GDTC 2026.pdf | ks_rev_5ffe3662aee1 | 43 | 0 | Chờ đối soát header/vùng hình |

Số ô bất định là số trường bị gắn cờ, **không chứng minh có từng ấy lỗi số liệu**.
Zero unresolved cells cũng không tự chứng minh mọi vùng hình/header đã chính xác.
Không suy năm các dòng từ tên file. Không kích hoạt lại quy tắc tính điểm gắn với
revision cũ đã purge; cấu hình được giữ nhưng căn cứ cũ không còn phục vụ.

## Thay đổi mã trong phiên

- `source_purge.py`: liệt kê snapshot/preview và QNU MD/JSON/raw PDF sidecar ở cả
  metadata và provenance. Kiểm toàn bộ đường dẫn trước external delete; kiểm tham
  chiếu của revision khác, không xóa tệp dùng chung; không chạm Repository.
- `source_extraction.py`: khi không chỉ định engine, OCR vùng đầu trang dùng
  PaddleOCR tường minh thay vì `auto` có khả năng mở chuỗi ngoài. Các quyền provider
  tường minh khác không bị đổi; không thay ModelOps DB hoặc cấu hình chatbot.
- `import_batch_service.py`: operator có thể xử lý bằng mã hiện tại không phát job
  sang worker cũ. `dispatch=False` ghi `dispatch_status=operator`; API mặc định
  vẫn enqueue như cũ. Retry giữ lịch sử job thật, không đổi lỗi thành thành công.
- `scripts/standard_migration_batch.py`: kiểm kê có fingerprint, yêu cầu waiver
  tường minh khi purge; chạy service/worker có lease, báo trạng thái thật và mã lỗi.
- `scripts/publish_standard_revision.py`: chỉ một revision được người dùng duyệt,
  kiểm identity/pair/issue/permission; dùng generation hiện tại, không đổi model.
  Tách identity map sau review tương đương các request API riêng biệt, tránh
  quan hệ ORM cũ gây `SOURCE_REVISION_CHANGED`.
- Regression ở purge/PDF/batch import; không sửa frontend, migration, framework,
  runtime đang chạy, restart/deploy, commit/push hay tài liệu nguồn trong Git.

## Diễn biến lỗi thật và giới hạn

1. Regression đầu: 3 FAIL đúng do thiếu cleanup sidecar và chưa chặn đường dẫn
   sidecar sai trước xóa vector. Sau sửa: nhóm purge/pause25PASS.
2. Nạp đầu trong sandbox không nối được OCR (WinError10013); probe có quyền network
   tới PaddleOCR8080 và inference8000 đều HTTP200. Không gọi cloud để vượt lỗi này.
3. Job `dispatch=False` ban đầu vẫn pending và bị reconciler đưa sang worker đang
   chạy; 5 item trả `QNU_STANDARD_INVALID`. Chưa truy được reason nội bộ của worker
   cũ; không khẳng định bản thân dữ liệu sai. Dùng nhãn operator + lease, retry bằng
   process nạp mã hiện tại: cả 6 pair/projection hợp lệ. Không restart worker.
4. Script publish đầu gặp stale ORM relationship sau approve; bỏ identity map đã
   load trước duyệt rồi đọc lại qua service, tiếp tục đúng revision, không đổi guard.
5. Audit OCR từ thời điểm batch: 13 record thành công đều PaddleOCR-VL/paddleocr_vl.
   Không lấy success audit làm bằng chứng hoàn chỉnh về mọi failed attempt.

## Kiểm chứng thực chạy

Các Python commands chạy bằng `.venv/Scripts/python.exe` từ `backend`.

- `-m scripts.standard_migration_batch inspect --collection col_admissions`: exit0;
  fingerprint trước dọn `9f6aded9619c1986b8b8836cdd609b235041e0a8ab4784a98232f9866fef7ac4`.
- `purge` với đúng fingerprint và `--without-backup`: exit0, 22 purge jobs completed,
  source revisions0. Không truncate DB, xóa namespace Qdrant hay flush Redis.
- `import` với 6 document IDs ở manifest, retry có kiểm soát: lượt cuối exit0,
  6 item `review_required`, 0 job đang chạy/chờ. Lỗi và job cũ vẫn có lịch sử.
- `status`: exit0, 6/6 pair_valid; 6 nguồn đúng projection, không gọi legacy fallback.
- DOCX ↔ XML gốc: thứ tự **3985 word tokens bằng nhau**, không thiếu/thêm token;
  56 khối. Đây là parity trích xuất, không chứng nhận nội dung pháp lý từ cơ quan gốc.
- `publish_standard_revision` đúng binding/revision đã duyệt: exit0; 56/56 parity,
  pointer/audit active, epoch50. Generation giữ `vg_a6e3190d11af`, bge-m3/1024,
  provider `prov_rtx5090_vllm`.
- Readback snapshot chỉ có `bnd_063df26142cb → idx_rev_c482a9e11451`. DB cuối:
  knowledge_documents0, chunks56, facts0 (DOCX dạng prose), 6 source revisions.
- Repository fingerprint, toàn bộ assistant config hash và collection metadata
  hash trước–sau bằng nhau. Không lưu plaintext cấu hình/prompt/key trong báo cáo.
- RAG search thật, assistant `admissions`, câu hỏi các phương thức xét tuyển:
  dense20/lexical20/fusion30/context5; 20+20hits, fusion27, rerank27→5,
  không degradation, hit đầu có PT1–PT5, chỉ nguồn đã duyệt, total676.89ms.
  Đây là tìm kiếm, **không phải thời gian/độ đúng câu trả lời LLM**.
- Smoke BM25 đơn lẻ top5 trước đó không đưa đoạn đủ5PT vào top5 dù đoạn có trong
  56 blocks; assertion thử FAIL. Hybrid/rerank thực tế phía trên chọn đúng hit đầu.
  Không nâng K/từ khóa thủ công hay tuyên bố mọi nhánh ranking hoàn hảo.
- Nhóm purge/pause/PDF/import: **57 passed**, exit0, 13.81s. Test mới header ban đầu
  gọi sai signature, đã sửa fixture rồi PASS. Sau thêm tham số dispatch true/false:
  4 lifecycle/retry tests PASS (có trùng nhóm57, không cộng dồn).
- Ruff scoped8files PASS. Full suite chạy một lần sau backend ổn định:
  **FAIL**, exit1, **2038 passed / 13 failed / 17 skipped / 23 subtests passed**,
  210.21s, `backend/storage/qnu528-full.log`. Hai parametrized test cases bổ sung
  sau lượt full, đã chạy focused; không chạy full lặp.
- Compare exact IDs baseline511: khớp11/11; thêm2 lỗi dưới đây. Hai test không seed
  dữ liệu độc lập mà đọc thẳng fact CNTT trong `col_admissions`; sau purge không có
  fact đó (facts0), assertion `found is True` FAIL. Không chèn fact giả để test xanh.

```text
tests/test_tools.py::test_fact_layer_lookup_tool_found
tests/test_universal_tools.py::test_fact_layer_lookup_tool
```

11 IDs baseline vẫn giữ trong log và nhật ký526; toàn suite không gọi PASS.
NOT RUN: full chat/gpt-6-luna inference, UI visual, benchmark12/20/82, Docker build,
backup/decrypt/restore. Code được chạy qua operator process mới; chưa xác minh mọi
process backend/worker sống lâu đã nạp cùng mã, không tự restart.

## Bằng chứng bền vững và bước tiếp

Qua StorageDriver: `snapshots/migration-inventory/batch528-before.json`,
`batch528-after-purge.json`, `batch528-final.json`, `batch528-docx-parity.json`,
`batch528-search.json`. Không phải backup và không có quyền phục hồi corpus.

Tiếp: đối soát/hiệu đính 5 PDF theo ảnh gốc và giữ raw JSON, tạo revision mới khi
sửa, duyệt các bản rõ rồi mới nạp/vector/publish. Không duyệt hàng loạt các ô bất
định. Kịch bản12câu được chuẩn bị riêng, chưa chạy và chưa có điểm chất lượng.
