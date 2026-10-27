# Context625 — Tiếp tục compiler từ bước 9

Ngày 2026-10-24. **Chưa nghiệm thu toàn compiler.** Đã xử lý tới bước 85; bước 86 (`PacketDraft`) dừng với `ALL_PROVIDERS_UNAVAILABLE`, checkpoint `uncertain`. Chưa có bundle tổng hợp cuối để đánh giá nội dung. Không coi việc đi qua một bước là xác nhận ngữ nghĩa của bước đó.

## Phạm vi và phương pháp

- Giữ ba DOCX 2024–2026, 381 bằng chứng và hash snapshot `59eb474ad57dc88b943504a46bc9cce8c718a302072b309c5c87022bd7f6ef66`.
- Dùng `gh/gpt-5.6-luna`, thinking medium, timeout mỗi request 30 giây; ngân sách token theo capacity động. Không đổi mặc định ModelOps hoặc nguồn.
- Tái sử dụng các candidate đã lưu sau khi kiểm tra hash request, cấu hình, nguồn, nội dung và receipt. Không gọi lại bước 1–8. Checkpoint uncertain gốc không bị đổi thành completed.
- Recovery là adapter của bộ kiểm thử trong `.antigravity-bridge/validation`, **không phải API recovery production mới**. Các candidate được tái sử dụng không phải phê duyệt.

## Lỗi hợp đồng đã sửa

Bước 54 trả `supporting_context` nhưng `assertion_ids=[]`. Server vốn đã chặn tổ hợp này ở đối soát coverage; tuy nhiên JSON boundary trước đó nhận phản hồi, khiến lỗi chỉ xuất hiện sau khi đã gọi witness độc lập ở bước 55.

Thêm validator vào `CoverageAudit` trong `compilation_runtime_schemas.py`: supporting context phải có assertion, unrelated phải không có assertion. Không thay JSON wire schema, không tự đổi role hoặc điền assertion. Giữ đối soát server về membership, cùng nguồn và tính đầy đủ. Phản hồi sai nay đi vào cơ chế correction có giới hạn đang tồn tại.

Bảy regression đi qua generator/adapter JSON thực với ModelOps giả lập: baseline 3 FAIL/4 PASS, sau sửa 7 PASS. Test backstop server vẫn kiểm dữ liệu malformed bằng đối tượng chưa qua validator; không bỏ guard để làm test xanh.

## Kết quả chạy thật

| Lượt | Kết quả |
|---|---|
| Tiếp tục lần đầu | Bước 9–55 có 47 phản hồi; đối soát phát hiện lỗi role tại 54. Witness 55 hợp lệ được giữ. |
| Tiếp tục sau sửa contract | Tái dùng 1–53; giữ rejection 54; correction mới 55; witness cũ 55 được ánh xạ có audit thành 56. Có 30 phản hồi mới hợp lệ về JSON tới 85; lần dispatch tiếp theo ở 86 lỗi. |
| Bước 86 | `PacketDraft`, `ALL_PROVIDERS_UNAVAILABLE`, `uncertain`; không có output đã xác nhận, không tự gửi lại. |
| Hoàn thành nội dung | NOT RUN: chưa có bundle cuối; chưa thể đánh giá lại đủ các mốc 5.948 / 5.081 / 5.173 và tổng hợp xuyên năm. |

Hai lượt Context625 có 77 phản hồi model được lưu; 78 lần dispatch stage, gồm một lần chưa rõ kết quả ở 86. Không đánh đồng `actual_calls=30` trong receipt lỗi lượt cuối (số metrics phản hồi) với tổng dispatch 31 của lượt đó. Các metrics có phản hồi đều `stop`, không fallback. Không có bằng chứng lỗi vượt context; receipt hiện chỉ lưu mã chung, chưa đủ phân biệt timeout, quota hoặc kết nối. Timeout cấu hình 30 giây không tự chứng minh nguyên nhân của lỗi này.

Checkpoint cũ, job thất bại trước và hash nguồn/cấu hình được đối chiếu giữ nguyên sau chạy. Dữ liệu chung, defaults, provider và domain rows không thay đổi theo seals.

## Kiểm thử

| Kiểm tra | Kết quả / exit code |
|---|---|
| Baseline 7 test mới | 3 FAIL, 4 PASS / 1 |
| Focused contract, semantics, ModelOps, checkpoint | 93 PASS / 0 |
| Ruff 3 file trong phạm vi | PASS / 0 |
| Full Pytest cuối batch | 3.792 PASS, 18 FAIL, 17 SKIP / 1 |
| So với Context623 theo từng ID và nguyên nhân | 18 lỗi trùng chính xác, 7 test thêm đều PASS, không mất test, không regression mới / 0 |
| Recovery negative probes | 5 PASS: config, request, response, receipt và old-stage drift |
| Final service readback/idempotency của lượt này | NOT RUN: chưa có bundle cuối |
| Benchmark 64, FE, indexing/publication | NOT RUN, ngoài phạm vi |

Full suite vẫn **FAIL**. Danh sách từng test, nguyên nhân và before/after có trong `backend/storage/context625/test-id-comparison.json`; log và JUnit ở `backend/storage/context625/final/full-final.*`. Lệnh thực, cwd, database và exit code được lưu trong `checks/*-run.json` và `final/full-final-run.json`.

## An toàn và bàn giao

Đã xác minh DB, MinIO và Qdrant dùng địa chỉ local trước chạy. Regression dùng hai database test sở hữu bằng nonce, Storage tạm và chặn egress ngoài ý muốn; cả hai database đã xóa sau kiểm thử. Storage còn giữ theo chính sách bảo vệ, không bypass xóa. Database acceptance Context623 và các checkpoint được giữ để đối soát/lấy lại bước chưa rõ kết quả.

Không migration dữ liệu thật, sửa nguồn, hạ Quality Gate, reindex, xuất bản, restart, commit hoặc push. Việc cần tiếp theo là xác định kết quả request 86 phía provider hoặc có chỉ dẫn retry rõ ràng, rồi chỉ thực hiện phần chưa hoàn thành. Không tự lặp lại toàn bộ compiler hoặc bước 1–85.

Bằng chứng cục bộ: `compiler-continued9/failure.json`, `compiler-contract-continued/{failure,phases,metrics,postcheck,recovery-preflight}.json` trong `backend/storage/context625/`. Các request/output chứa corpus và registry chi tiết giữ ở Storage kiểm thử, không chép vào tài liệu Git.
