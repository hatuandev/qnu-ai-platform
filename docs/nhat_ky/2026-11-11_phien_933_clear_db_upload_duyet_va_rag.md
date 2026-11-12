# Phiên 933 — Clear DB, up tệp scan thật, duyệt sửa chính tả, xuất bản và nạp vector RAG

## Yêu cầu và phạm vi

Người dùng yêu cầu: clear lại DB, up một tệp thật, duyệt **sửa** lỗi chính tả
E2E (áp dụng gợi ý, không chỉ bỏ qua), sau đó duyệt nội dung/xuất bản để nạp
vector vào DB vector, chuẩn bị cho RAG.

Phạm vi được người dùng cho phép trong phiên này: reset dữ liệu dev, upload lại,
tạo bản duyệt, xuất bản và tạo chỉ mục. Không commit/push/deploy, không sửa mã
ngoài phạm vi, không chạy test trên DB ứng dụng.

## Reset môi trường dev

- Dừng stack dev; chạy `run_v1.py v1-clear --confirm-local-reset` để xóa các
  volume `qnu_*` (Postgres, Qdrant, Redis, MinIO) của môi trường local.
- Dựng lại hạ tầng, áp migration `0001 -> 0024` (head `0024_spelling_reviews`)
  trên DB mới, seed ModelOps và workspace `ws_686011c2a0af` (mã `shl`) cùng các
  danh tính dev.
- Khởi động lại API 8002, worker ARQ và Vite 3002; `health/live` và
  `health/ready` trả 200 trước khi E2E.

## Tệp và xử lý

- Tệp PDF scan thật 17,5 MB, SHA-256
  `59444d277a5e904808537ce70544c1fc83c0bf0a2f2653b78af362af59d5cccc`.
- Nguồn `src_c4aedffe9fbd`, revision `rev_d08495dee77e`, OCR run
  `ocr_6ef16fde0f6e`; bộ sưu tập `col_2853ae308e33`.
- OCR hoàn tất 32/32 trang trong khoảng 15 giây; chuẩn bị nội dung tự động tạo
  bản `v0` ở trạng thái `ready`.
- Soát chính tả tự động: lượt cha `spl_58a06fd065d3` `completed`, phủ 600 đoạn,
  **25 gợi ý** và **7 gợi ý bị withheld**.

## Duyệt chính tả có sửa

- Áp dụng 21 thao tác "Áp dụng" trên giao diện, gồm các cặp đã sửa: `nổi → nối`
  (2), `phòng vấn → phỏng vấn`, `gọi tất → gọi tắt` (2), `Môi → Mỗi` (2),
  `su → sư` (2), `kiện tương → kiện tướng`, `nguyên vọng → nguyện vọng`,
  `thông nhất → thống nhất`, `nhằm lẫn → nhầm lẫn`, `xét tuyến → xét tuyển` (2),
  `trúng tuyến → trúng tuyển`, `tuyến sinh → tuyển sinh` (2),
  `phần ánh → phản ánh`, `ký luật → kỷ luật`, `dặc khu → đặc khu`.
- Chủ động **không** áp dụng 4 gợi ý `thường → thưởng` vì ngữ cảnh mơ hồ; sau đó
  dùng "Bỏ qua tất cả còn lại" để bỏ qua 4 gợi ý còn chờ + 7 withheld = **11
  disposition**.
- Hoàn tất duyệt: bản ghi `splrev_5b603e7fbdbf` gắn check
  `spl_58a06fd065d3`, `reviewed_version=1`, `reviewed_version_id=txt_1c0125399a69`,
  `change_count=18`, `reviewed_by=act_dev_admin`, thời điểm
  `2026-11-11 09:55:25Z`. 21 thao tác áp dụng gộp còn 18 thay đổi văn bản vì một
  số gợi ý trùng tọa độ.
- Bản `v1` (`txt_1c0125399a69`) có `canonical_sha256`
  `c7d8755ddb44bb732a6be463d6f1b44b98e58b860e02af1646616a106efbffff`; chuẩn bị
  nội dung `prep_466006d10c4d` được tạo lại từ `v1` ở trạng thái `ready`.
- Không tạo yêu cầu soát lại `v1`; đúng quyết định "duyệt một lần sau upload" của
  phiên 932.

## Duyệt nội dung, xuất bản và chỉ mục

- Hộp thoại duyệt/phát hành: nhập lý do "Đã đối chiếu bản biên soạn với tệp gốc
  và duyệt để phục vụ tra cứu."; xác nhận duyệt rồi phát hành.
- Quyết định ghi nhận:
  - `pdec_3ae6cc150cfe` — `approve`, document_sequence 3, lúc `09:56:39Z`.
  - `pdec_a22474341668` — `publish`, document_sequence 4, lúc `09:56:45Z`.
- Tài liệu biên soạn `cdoc_e675de6bf424`, phiên bản `cver_f258b9e92586`.
- Chỉ mục `idx_af04993c0a56`: `completed`, `chunks_total=448`, `is_active=true`,
  chạy `09:56:48Z -> 09:57:20Z`; `kb_index_sync` chuyển `ready` lúc `09:57:21Z`.
- DB có đúng 448 dòng `kb_index_chunks` cho run này. Qdrant collection
  `qnu_v1_idx_1d195484801842a287ca124d6827f252` ở trạng thái `green`, 448 point,
  vector 1024 chiều, khoảng cách Cosine.

## Kiểm tra RAG thật

- Tìm kiếm trực tiếp `hybrid_rerank` với câu hỏi về "gọi tắt" trả 3 hit; hit đầu
  chứa `gọi tắt` (không còn `gọi tất`), dẫn chứng trang 17,
  `ocr_6ef16fde0f6e:ev_p017_b006`, `text_version` là `txt_1c0125399a69` bản 1 và
  `publication_decision_id=pdec_a22474341668` — chứng minh văn bản đã sửa được
  đánh chỉ mục và phục vụ truy vấn.
- Tạo trợ lý `ast_653d73272672` ("Trợ lý tuyển sinh 2026") trỏ bộ sưu tập
  `col_2853ae308e33`; readiness `ready` (1 tài liệu xuất bản, 1 tài liệu phục vụ,
  index run `idx_af04993c0a56`, sync `ready`). Cấu hình test: dense, `top_k=5`,
  `candidate_k=30`, `scope_resolution=catalog`, verification `off`.
- Đường `/chat` của Frontend V2 hiện là mock tĩnh, không phải bằng chứng RAG; trả
  lời thật được gọi qua integration gateway OpenAI-compatible với khóa ứng dụng
  giới hạn đúng trợ lý. Khóa được tạo/rotate trong phiên, secret chỉ giữ tạm và
  **không** ghi vào tài liệu; cuối phiên đã thu hồi khóa (`revoked`, lý do "Kết
  thúc kiểm thử E2E RAG").
- Câu hỏi 1 (định nghĩa "Hệ thống đăng ký xét tuyển được gọi tắt là gì"): HTTP 200
  nhưng pipeline trả `insufficient_evidence`, `reason=model_abstained`,
  `choices[0].message.content=""`, 1.605 prompt / 65 completion token. Đây là hành
  vi đúng: evidence được cấp không chứa định nghĩa "gọi tắt".
- Câu hỏi 2 (tối đa bao nhiêu nguyện vọng và ưu tiên trúng tuyển): pipeline
  `answered`, 2 statement, 1 nguồn `E1` (`ich_3ad25010b71a`), dẫn chứng
  `ocr_6ef16fde0f6e:ev_p018_b004`, trang 18, `pages[17].blocks[3]`,
  `source_id=src_c4aedffe9fbd`, `revision_id=rev_d08495dee77e`,
  `text_version=txt_1c0125399a69` bản 1, canonical `c7d8755d...`,
  `publication_decision_id=pdec_a22474341668`. Nội dung trả lời: tối đa **15
  nguyện vọng**; nhiều nguyện vọng đủ điều kiện thì chỉ công nhận trúng tuyển và
  gọi nhập học theo **nguyện vọng cao nhất**. Usage 1.856 prompt / 224 completion
  / 2.080 total; request log `log_f034ad702566` ghi nhận HTTP 200, 10.437 ms.
- Lưu ý chất lượng: đoạn nguồn Điều 14 khoản 3 vẫn còn các vị trí `nguyên vọng`
  chưa được gợi ý/sửa; bản `v1` chỉ phản ánh đúng các gợi ý đã áp dụng, không phải
  bản đã làm sạch toàn bộ. Model trả lời dùng cách viết đúng `nguyện vọng` nhưng
  không thay đổi dữ kiện nguồn.

## Bằng chứng DB chính

| Hạng mục | Giá trị |
|---|---|
| Bản duyệt chính tả | `splrev_5b603e7fbdbf`, check `spl_58a06fd065d3`, version 1, change_count 18 |
| Disposition bỏ qua | 11 |
| Text version | `txt_1c0125399a69` bản 1, canonical `c7d8755d...` |
| Quyết định duyệt/phát hành | `pdec_3ae6cc150cfe` (approve), `pdec_a22474341668` (publish) |
| Tài liệu/phạm vi | `cdoc_e675de6bf424`, `cver_f258b9e92586` |
| Chỉ mục | `idx_af04993c0a56`, completed, 448 chunk, active, sync ready |
| Vector | Qdrant `qnu_v1_idx_1d195484801842a287ca124d6827f252`, green, 448 point |
| Trợ lý | `ast_653d73272672`, readiness ready |
| Request log gateway | `log_798d5f51c9e2` (abstain), `log_f034ad702566` (answered, 10.437 ms) |

## Kiểm chứng và giới hạn

- Đã thực chạy: reset + migrate + seed; health 200; upload/OCR/chuẩn bị/soát
  chính tả/duyệt sửa/duyệt nội dung/xuất bản/index; truy vấn DB xác nhận đúng
  bản ghi; tìm kiếm trực tiếp và một câu trả lời RAG thật qua gateway.
- **NOT RUN**: full Pytest trên DB cô lập; baseline lịch sử **FAIL 4/1627** của
  phiên 928 vẫn giữ riêng, không chạy lại để làm xanh. Không có thay đổi mã
  nguồn trong phiên này.
- E2E một lượt chạy thật, không phải benchmark; chất lượng OCR/chính tả toàn văn
  (CER/WER, đối chiếu ảnh gốc) vẫn chưa nghiệm thu. F13 (chất lượng RAG) vẫn mở.
- Đã thu hồi khóa tích hợp tạm; không lưu secret trong nhật ký/memory. Chưa
  commit/push/deploy.

## Việc tiếp theo

- Nếu muốn đo chất lượng RAG: dùng bộ câu hỏi có gold answer theo
  `qnu-rag-evaluation`, không suy từ một lượt E2E.
- Nếu muốn sạch chính tả toàn văn: cần cơ chế soát lại/duyệt bổ sung cho các vị
  trí model không gợi ý (ví dụ `nguyên vọng` còn lại trong Điều 14), không sửa
  tay ngoài quy trình.
