# Phiên 805 — Đổi model9router sang Luna và thử sửa chính tả OCR

## Yêu cầu và thay đổi

Người dùng yêu cầu thay GPT-OSS bằng `cx/gpt-6-luna` ở9router, rồi test lại.
Áp dụng ModelOps/ingestion/clean-code; giữ các thay đổi đang có của người dùng.

- Connection discovery qua API ModelOps xác nhận model mới có trong catalog,
  HTTP200; metadata context/output đều unknown, không đoán theo tên model.
- PATCH model entry hiện có từ `ollama/gpt-oss:120b` sang `cx/gpt-6-luna`, đổi tên
  hiển thị; endpoint và protected credential giữ nguyên, không đọc/xuất key LLM.
  Xóa khai báo capacity cũ nếu có để không kế thừa nhầm; sync metadata hiện tại.
  Model9router mới được giữ lại theo yêu cầu, không rollback về GPT-OSS sau test.
- Cấp tạm model cho workspace để thử qua đường runtime chính thức, sau test trả
  đúng grants/defaults cũ có kiểm tra drift. Chat mặc định workspace vẫn Qwen.
- Profile `scripts/e2e_profiles/qnu-server.json` dùng Luna cho lựa chọn9router,
  alias chính xác `gpt-6-luna` đã quan sát ở8phản hồi. Không thêm alias tùy tiện.
- Cập nhật test selection và ba hướng dẫn test hiện hành, không viết lại nhật ký
  lịch sử GPT-OSS. Không sửa logic OCR, prompt, validator, retrieval hoặc compiler.

## Thí nghiệm model thật

Cùng source0/hash, cùng7trang114units/8nhóm, promptv4/contextv1 và danh sách
context_evidence_ids như802/804. Private API loopback với code hiện tại, không
restart API/worker/FE chính. Mỗi nhóm1request/1QNUattempt, không retry/salvage.

Model yêu cầu `cx/gpt-6-luna`, quan sát `gpt-6-luna`. Capacity chưa khai báo nên
ModelOps dùng provisional32768context/4096output, reasoning server default;
không công bố đây là capacity đã xác minh. Không sửa tham số reasoning/timeout.

**Kết quả toàn cohort: FAIL, chưa nghiệm thu đầy đủ.**
4completed/4failed,10gợi ý contract hợp lệ,0withheld/0uncertain/0NOTRUN.
Tổng usage18.940token,61,24giây cộng request. Không lỗi cắt output; cả8finish_reason
stop và upstream QNUevent codeok/attempt1. Failedbatch vẫn có usage đã ghi nhận.

| Nhóm | API | Gợi ý hợp lệ trả được |
|---|---|---:|
| p15-probe | completed |2|
| p01-00 | ocr_spelling_invalid |0|
| p02-00 | completed |3|
| p15-00 | ocr_spelling_invalid |0|
| p20-00 | ocr_spelling_invalid |0|
| p27-00 | completed |2|
| p31-00 | ocr_spelling_invalid |0|
| p32-00 | completed |3|

Probe trang15 sửa đúng `hồ so→hồ sơ` và `cơ bán→cơ bản`, nguồn quote trước/sau
khớp; đối chiếu crop PDF gốc xác nhận. Trang32 sửa đủ `he→hệ`, `dịa→địa`, `chi→chỉ`
đúng ảnh. Năm gợi ý trang2/27 hợp lệ contract nhưng chưa độc lập đối chiếu toàn bộ
với ảnh trong phiên này. Không gọi10gợi ý là10PASS ngữ nghĩa hoặc đạt toàn32trang.

## Những lỗi còn lại

- Trang1: vị trí sai ở chữ xuất hiện lặp; quote chứa thêm sửa ngoài span.
- Batch trang15: sửa cả unit chỉ có trong readonlycontext, không thuộc targets;
  thêm mục unchanged và vị trí anchor lặp không xác định. Guard chặn đúng.
- Trang20: chữco lặp nhiều lần nhưng offset sai, không định danh được occurrence.
- Trang31: original không khớp nguồn hoặc unchanged, batch bị từ chối.

Các batchfailed vẫn FAIL, không nhặt từng item có vẻ hợp lệ để làm xanh. Trong
lượt này vấn đề còn lại tập trung ở contract vị trí/quote/target, không outputlimit.

## So sánh có giới hạn

| Cohort | completed/failed | Gợi ý contract | Tokens | Giây |
|---|---|---:|---:|---:|
| Qwen802 |4/4|1|17.571|60,95|
| GPT-OSS804 |1/7|0|57.927|84,32|
| Luna805 |4/4|10|18.940|61,24|

Luna cải thiện trên probe và các mẫu đã đối chiếu. Chưa xếp hạng tổng quát:
Qwenoutput16384/thinkingoff, hai model9router output4096/reasoningdefault; chỉ
7trang, không CER/WER hoặc toàn32trang. Probe GPT-OSS bị cắt nên không đánh giá
như một sửa sai ngữ nghĩa; probe Qwen trả rỗng, bỏ sót.

## Kiểm chứng và toàn vẹn

- `backendV1/.venv/Scripts/python.exe tmp/ocr805-live.py`: exit0,8nhóm đủ;
  exit0 của runner không biến kết quả chất lượngFAIL thànhPASS.
- Inspector và report offline exit0:8QNUattempt1, source/selection/prompt/context
  giống baseline; không gọi lại model.
- `frontendV1`: `npx vitest run tests/e2e-provider-selection.test.ts`,5PASS/0FAIL.
- `scripts`: `../backendV1/.venv/Scripts/python.exe -m unittest test_e2e_provider_setup`,
  17PASS/0FAIL. Fixture cũ dùng GPT-OSS để kiểm tính tổng quát vẫn giữ.
- `npm run test:e2e:typecheck`:PASS,exit0. Biome một testfile ban đầu formatFAIL,
  sửa xuống dòng theo formatter, chạy cuốiPASS. Không đổi assertion để làm xanh.
- Full Pytest/full Vitest/production build NOT RUN vì không đổi logicBE/FE;
  không coi các lỗi nền đã được sửa hoặc lấy kết quả lịch sử làmPASS mới.
- Read-only xác nhận latest30/hash
  `988fe0ae8b9b5c66675dbeef43c02cde575b5c4f72d99bcd137fb19603c89c5f`
  và compiler30 completed/pinned đúngversion/hash. PDF và rawOCR hash không đổi;
  không SaveReview/compiler/publish/index. API tạm đã đóng, grants/defaults restore.
- Kiểm cuối JSON, liên kết mới/anchor hướng dẫn, UTF8 khôngBOM/LF và gitdiff.

Artifact tại `tmp/ocr805/`: report.md/json, manifest, rawresponses, receipts,
diagnostics, model-change-before/model-changed, discovery-target, integrity-final,
grants-restored; preview.md/json chỉ ghép10gợi ý từ completedbatch, **chưa lưu**.
Phiên đi qua nửa đêm; lệnh model chạy2026-11-01UTC, nhật ký dùng02/11giờ máy.

Bước tiếp phù hợp: giảm việc bắt model tự đếm offset và trích lặp câu bằng cách
định danh occurrence từ nguồn ở server, giữ kiểm tra dữ kiện/target; đo cohort mới
riêng sau thay đổi. Chưa triển khai bước đó trong task thay model này.
