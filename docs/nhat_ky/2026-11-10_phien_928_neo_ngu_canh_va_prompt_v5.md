# Phiên 928 — Neo ngữ cảnh, cách ly gợi ý chính tả và prompt v5

## Phạm vi và nguyên nhân

Lượt tự động trước đây dừng ở 75/600 đoạn, sau đó ghi nhận 425/600 khi bảy nhóm
trả về `ocr_spelling_invalid`. Bộ xác thực cũ loại toàn bộ phản hồi nếu một gợi ý
không khớp, nên một lỗi nhỏ khuếch đại thành 175 đoạn chưa soát và làm phiên cha
thất bại. Truy vấn chỉ đọc trên lượt `ocr_f783f4304b35` xác nhận 24 nhóm/600 đơn vị;
phát lại 17 phản hồi v4 đã lưu qua bộ kiểm mới cho 17/17 phân tích được, 9 gợi ý
→ 6 áp dụng, 3 giữ lại, 0 loại. Vì vậy điểm chặn chính là cách xử lý toàn batch,
không phải model không thể trả output hợp lệ.

## Thay đổi

- Phase 1 — neo theo ngữ cảnh và cách ly từng gợi ý:
  - `backendV1/qnu/domains/ocr/review/anchors.py` chỉ chấp nhận vị trí khớp chuỗi
    gốc; chuỗi lặp lại chỉ được căn lại khi đúng một lần xuất hiện được
    `context_before`/`context_after` chứng minh, còn lại loại với
    `source_anchor_ambiguous`. Không fuzzy match.
  - `backendV1/qnu/domains/ocr/review/context.py` phân loại từng gợi ý thành áp
    dụng được, giữ lại hoặc loại bỏ; loại `no_change`, `empty_replacement`,
    `numeric_change`, `overlap`; gợi ý đổi chữ cơ sở/dấu câu được giữ lại với
    `source_image_required` để đối chiếu ảnh.
  - `backendV1/qnu/domains/ocr/review/schemas.py` bổ sung `rejected_suggestions`
    (chỉ evidence ID, lý do, khoảng vị trí) và `withheld_suggestions` trong phản hồi.
  - `backendV1/qnu/domains/ocr/review/automatic.py` cộng dồn gợi ý giữ lại/loại vào
    trace phiên cha; nhóm không phân tích được hoặc sai schema chỉ làm hỏng nhóm đó,
    các nhóm khác vẫn chạy, và phiên cha chỉ hoàn tất khi mọi đơn vị đã được kiểm tra.
    Lỗi quyền, quota, đổi nguồn/model và hạ tầng vẫn dừng lượt như cũ.
- Phase 2 — chính sách theo độ xác định của neo: neo xác định nhưng ngữ cảnh không
  chứng minh được vị trí thì giữ lại với `context_unverified`; chuỗi lặp lại có ngữ
  cảnh mâu thuẫn thì loại, không bao giờ tự áp dụng.
- Phase 3 — prompt `qnu.ocr.spelling/v5` trong `detection.py`: nêu rõ chỉ sửa đúng
  từ/cụm nghi sai, không viết lại câu, không đổi số/năm/mã/đơn vị/tên riêng, không
  lấy chữ từ ngữ cảnh chỉ đọc, phải trích nguyên văn ngữ cảnh của chính đơn vị và
  bỏ qua khi không đủ chắc. Idempotency key gắn với phiên bản prompt nên v4 không bị
  chạy lại; lịch sử v3/v4 giữ nguyên.

## ModelOps

`ocr_review` hiện vẫn ánh xạ capability `chat`; chưa có ô mặc định riêng cho tác vụ
này. Muốn chọn model mạnh hơn riêng cho soát chính tả cần thêm capability/default
trong schema, migration và giao diện quản trị. Không thay cấu hình model dùng chung,
không gửi văn bản tài liệu sang nhà cung cấp cloud khi chưa có phê duyệt.

## Đo chẩn đoán trên cùng nguồn thử

Chỉ đọc, không phải nghiệm thu chất lượng:

- 17 phản hồi v4 đã lưu qua bộ kiểm mới: 17/17 phân tích được; 9 gợi ý → 6 áp dụng,
  3 giữ lại, 0 loại.
- Chạy lại bảy nhóm từng lỗi, hai lượt mỗi prompt: v4 cho 16 rồi 29 gợi ý; v5 cho
  23 rồi 20 gợi ý; cả 14 lượt đều phân tích được, không còn `ocr_spelling_invalid`.
- v5 trên toàn bộ 24 nhóm: 24/24 phân tích được, phủ 600/600 đơn vị, 42 gợi ý
  → 36 áp dụng, 6 giữ lại, 0 loại; 68.456 token, 88,96 giây.
- Chênh lệch giữa các lần chạy v4/v5 chưa chứng minh cải thiện chất lượng; không có
  kết luận CER/WER, không dùng cohort này làm nghiệm thu toàn 32 trang.
- Báo cáo chỉ gồm số đếm và mã lý do; không ghi văn bản tài liệu, output model hay PII.

## Chạy thật trên tệp Quyết định 2699

- Nguồn `src_70473ea14ee1`, revision `rev_7e054387943d`; tải qua API của ứng dụng sau
  khi khởi động lại dev để nạp mã v5.
- OCR `ocr_3546d5149370`: 29/29 trang, `completed`.
- Lượt soát tự động `spl_38d718bb5eaf` (`qnu.ocr.spelling/v5`): 993 đơn vị, 40 nhóm;
  `completed`, phủ 993/993, 10 gợi ý áp dụng được, 4 giữ lại (2
  `source_image_required`, 2 `context_unverified`), 0 loại. Không có
  `ocr_spelling_invalid`; log worker không có `spelling_batch_rejected`,
  `spelling_review_failed` hay `auto_spelling_job_failed`.
- Trang chi tiết hiển thị “Có 14 vị trí cần xem” và liên kết rà soát đúng lượt; trang rà
  soát hiển thị 10 vị trí chờ duyệt và 4 vị trí cần dò kèm lý do. Không ghi văn bản tài
  liệu hay nội dung gợi ý vào nhật ký.
- Lỗi giao diện phát hiện thêm: `spellingScope` chỉ chọn được lượt OCR khi có
  `active_run_id` (chỉ trạng thái đang chạy) hoặc derivation; sau khi OCR hoàn tất mà
  chưa có lượt chuẩn bị nội dung, trang rà soát không gọi API và hiện “Chưa có kết quả”.
  Đã sửa `frontendV2/src/lib/spelling-review.ts` để dùng lượt `completed` gần nhất khi
  không có lượt được chỉ định; nếu có `preferredRunId` nhưng lượt đó chưa hoàn tất vẫn
  trả `null`, không tự đổi phạm vi. Không đổi API, schema hay migration.

## Chạy thật thứ hai trên tệp Nhiệm vụ trọng tâm 2025-2026

- Nguồn `src_5f3f001ff22a`, revision `rev_0bc6b3284b28`; tải qua API của ứng dụng.
- OCR `ocr_3c3d2748630e`: 7/7 trang, `completed`.
- Lượt soát tự động `spl_627b3e82039b` (`qnu.ocr.spelling/v5`): 136 đơn vị, 6 nhóm con;
  `completed`, phủ 136/136, 14 gợi ý áp dụng được, 8 giữ lại (6
  `source_image_required`, 2 `context_unverified`), 0 loại. Cả 7 dòng (1 cha + 6 con)
  đều `completed`, không `error_code`; mọi nhóm con dùng prompt v5.
- Trang chi tiết hiển thị “Có 22 vị trí cần xem” và liên kết rà soát đúng
  `revisionId`/`runId`/`textVersion=0`; trang rà soát hiển thị 14 vị trí chờ duyệt và
  8 vị trí cần dò; console không lỗi.
- 14 gợi ý và 8 vị trí giữ lại chưa đối chiếu ảnh gốc; các vị trí giữ lại không áp dụng
  tự động và cần người dùng dò lại. Không ghi văn bản tài liệu hay nội dung gợi ý.

## Kiểm chứng

- Ruff check và format check theo phạm vi chín tệp backend đã sửa: PASS.
- Unit: `test_ocr_spelling_anchors_797.py` + `test_ocr_context_review_801.py`
  → 31 ca PASS trong 0,48 giây.
- Integration cô lập: `test_ocr_context_review_801.py` + `test_ocr_text_review_651.py`
  → 29 ca PASS trong 112,74 giây; biên nhận `qnu_v1_test_7d5e31623b68480d`,
  DB đã dọn, sentinel giữ nguyên, exit 0, tổng 122,86 giây.
- Frontend: `npx tsc --noEmit` PASS; Biome trên `src/lib/spelling-review.ts` PASS;
  `npm run build` PASS.
- Kiểm tra trình duyệt: snapshot cấu trúc xác nhận trang chi tiết hiển thị liên kết rà
  soát với đúng `runId`/`textVersion=0`; trang rà soát hiển thị 10 vị trí chờ duyệt và
  4 vị trí cần dò. Ảnh chụp màn hình NOT RUN vì in-app browser không có viewport hiển
  thị trong phiên này.
- `git diff --check` toàn working tree: PASS (exit 0).
- Full Pytest cô lập: **FAIL** — `4 failed, 1627 passed, 5 warnings` trong 3683,11
  giây; biên nhận `qnu_v1_test_6ae81ec79c9e4b90`: DB đã dọn, sentinel giữ nguyên,
  `pytest_exit: 1`, tổng 3707,16 giây. Bốn lỗi nằm ngoài phạm vi soát chính tả, giữ
  nguyên và báo riêng, không chạy lại để làm xanh:
  - `test_integration_gateway_pipeline.py::test_external_key_calls_real_rag_and_preserves_assistant_config[128]`
    và `[None]`: dòng 67 kỳ vọng `"150"` trong câu trả lời gateway nhưng nội dung nhận
    được chỉ có tiêu đề `Chỉ tiêu tuyển sinh — STT: 1 [E1]`; thuộc nhóm lỗi nền RAG
    fixture đã ghi ở phiên 914/916, không liên quan mã OCR.
  - `test_legacy_source_deletion_718.py::test_legacy_deleted_source_with_published_version_is_still_protected`:
    kỳ vọng 409 `source_publication_in_use` nhưng nhận 200 preview với
    `published_versions_to_withdraw=1`. `purge.inspect_source` hiện dùng
    `allow_published=True` và không chặn ở bước preview; mã và test này không nằm
    trong batch soát chính tả, cần quyết định riêng (sửa guard hay cập nhật hợp đồng).
  - `test_rag_verification_policy_672.py::test_assistant_chat_uses_persisted_hybrid_rerank_policy_and_checks_provider_access`:
    lượt chat trả 504 `chat_provider_uncertain`; lỗi provider/runtime, ngoài phạm vi OCR.

## Giới hạn và vận hành

- Dev đã được khởi động lại để nạp prompt v5; lượt chạy thật chỉ tạo nguồn/lượt mới,
  không sửa lượt cũ hay dữ liệu ngoài phạm vi. Worker không có `--reload`, nên mọi
  thay đổi mã backend tiếp theo vẫn cần nạp lại.
- 10 gợi ý áp dụng được chưa được đối chiếu ảnh gốc và chưa phải nghiệm thu chất lượng;
  F13 ở phiên 908 là vấn đề riêng, không bị tuyên bố đã sửa.
- DB test còn sót 8 cơ sở dữ liệu cô lập: `qnu_v1_test_12473575541d4a85`,
  `4a262de990814899`, `711acdc069ac4b68`, `82581efe0ab043d2`, `974f2878024d45d7`,
  `9f76fb9421be44e1`, `e3e3359983fc407d` (không có biên nhận),
  `f809d0c223404df1`; không tự xóa, cần báo và chờ quyết định dọn.
