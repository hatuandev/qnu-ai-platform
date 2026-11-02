# Phiên 802 — Kiểm thử sửa chính tả bằng model thật

## Phạm vi

Người dùng yêu cầu chạy lại quy trình sửa chính tả sau cải tiến801. Kiểm tra source
OCR gốc của Quy chế363, không ghi đè bản29 đã biên soạn, không tạo compiler mới,
không publication/index. Giữ các thay đổi chưa commit của người dùng.

API cũ chỉ inspect latest, nên thêm tùy chọn `DetectRequest.source_version` có
version/hash bắt buộc khớp, mặc định None giữ optimistic lock latest. Snapshot
lịch sử bất biến được dùng ở cả đầu/cuối request. Hash idempotency mặc định loại
riêng field mới nếu None để tương thích request đã lưu. Không thay ModelOps model,
promptv4 hoặc cơ chế validator để làm test xanh.

## Kiểm thử model thật

- Mở API tạm ở loopback với code mới, cùng quyền/storage/ModelOps của phiên
  `93faa11f0caf`, không restart API/worker/FE chính, không migrate DB live.
- Preflight không có compiler queued/running. Chỉ dùng policy `enable_thinking`
  đã khai báo verified, tạm thêm taskocr_review vào off qua API ModelOps; lưu trước
  và restore nguyên trạng có kiểm tra concurrent drift. Không truyền key LLM từ
  .env sang tiến trình; inference lấy key từ ModelOps DB. API tạm đã đóng.
- Model `qwen3.8-27b-q4`, provider hiện có, output16384, source v0/hash
  `bf81dd5b252b66e18dfb1e3f32ae271f340d49f411324a9a6ef4e31a1ac7dcb0`.
- Frozen manifest 7 trang1,2,15,20,27,31,32;114 đoạn/ô,8 request. Probe riêng
  `ev_p015_b007` không nằm lại trong batch trang15 nên không gửi trùng unit.
- **4 completed / 4 failed / 0 uncertain / 0 NOT RUN. Tổng chất lượng FAIL.**
  8/8 upstream attempts đúng1, codeok trong ModelOps events; không retry.
- Usage17.571 tokens,60,95s tổng thời gian request. Không `length`, token-limit,
  quota hoặc timeout. Upstream200 có usage dù validation gợi ý thất bại.

| Request | Kết quả | Gợi ý trả được |
|---|---|---:|
| p15-probe | completed, bỏ sót `cơ bán → cơ bản` | 0 |
| p01-00 | completed, không có gợi ý; không chứng minh chữ đúng | 0 |
| p02-00 | completed, không có gợi ý; không chứng minh chữ đúng | 0 |
| p15-00 | failed, quote không khớp nguồn | 0 |
| p20-00 | failed, anchor mơ hồ/quote bị sửa trước | 0 |
| p27-00 | failed, anchor không khớp | 0 |
| p31-00 | failed, anchor/quote/unchanged không hợp lệ | 0 |
| p32-00 | completed, `liên he → liên hệ` | 1 |

Phản hồi gốc đều được giữ trên StorageDriver; bản copy tmp phục vụ chẩn đoán.
Ví dụ trang31 model trả context_before đã là `Quy tắc quy đổi...` thay vì OCR thật
`quy đỗi...`, context_after cũng không thay đổi. Trang15 quote đã tự rút gọn từ câu
nguồn. Guard không nhận quote hoặc offset gần đúng để áp dụng. Tách từng item để
chẩn đoán offline, không cứu/sửa những item đó rồi công bố batch PASS.

Đối chiếu ảnh trang32 xác nhận sửa `he → hệ` đúng, nhưng cùng dòng `dịa chi`
còn thiếu sửa `địa chỉ`. Probe trang15 nhận đầy đủ unit và heading/neighbor nhưng
vẫn trả mảng rỗng; chưa có thí nghiệm A/B để quy nguyên nhân riêng cho prompt hay
model. Việc thêm ngữ cảnh chưa đủ nghiệm thu khả năng sửa tiếng Việt.

## Kiểm chứng code và toàn vẹn

- Red API trước thêm source_version:4FAIL vì DTO chưa hỗ trợ tham số mới.
- Sau sửa: FastAPI/DB/loopback API29PASS/0FAIL (history802/context801/review651),
  exit0,100.04s. Cả2DB test sở hữu riêng đã drop, remaining0.
- Full Pytest:693PASS/1FAIL/77SKIP,exit1,30.89s. Lỗi nền716
  `test_accept_rechecks_publication_after_preview_before_preparing_purge` giữ nguyên;
  tổng gate FAIL. FE không sửa nên không chạy lại build/tests.
- Ruff/format3 file PASS, diff và UTF8/LF/link mới kiểm cuối.
- SELECT read-only xác nhận TextVersion mới nhất29, hash
  `102a200441d5c986fc5dd7194ff37e0b1a5945ae1f0374282a61468600670876`;
  compiler `cmp_5b8a2375d0d9` completed/attempt1 vẫn ghim đúng version/hash đó.
  SHA256 PDF gốc không đổi. Không gọi SaveReview trong lượt thật.
- Helper inspect lần đầu đọc xong raw gặp AttributeError do S3BlobStore không có
  close; sửa helper và đọc lại, không gọi lại model hoặc thay kết quả cohort.

## Artifact và bước tiếp

Tại `tmp/ocr802/`: report.md/json, manifest,8receipt+response+raw,diagnostics,
integrity-final.json,policy-before/restored,preview.md/json. Preview chỉ chứa một
sửa từ batch thành công, **chưa lưu DB**; các phần không kiểm giữ OCR gốc, có nhãn rõ.

Chưa nghiệm thu OCR/sửa chính tả toàn32trang, chưa CER/WER hoặc browser QA. Cần cải
thiện hợp đồng sinh đề xuất (model chưa trích nguyên văn/đếm span ổn định) và giảm
bỏ sót có đo lường; không nới source/numeric guard hoặc retry để có số PASS đẹp.
Không tự coi sửa chính tả là khôi phục bảng trang32 dư cột.
