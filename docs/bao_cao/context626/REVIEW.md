# Context626 — Thử cx/gpt-6-luna và tiếp tục compiler

Ngày 2026-10-24. **Đã thử lại bước 86 thành công và chạy hết phần còn lại đến bước 123. Chưa APPROVED toàn compiler:** kết quả cuối là `needs_attention`, `machine_complete=false`.

## Phạm vi

Người dùng yêu cầu đổi sang `cx/gpt-6-luna` và thử các bước chưa thực hiện được. Lượt kiểm thử dùng alias này qua ModelOps, thinking medium, timeout request 30 giây, không fallback. Không đổi model mặc định toàn ứng dụng. Không sửa mã nguồn ứng dụng, nguồn, Quality Gate hoặc publication.

Giữ ba DOCX 2024–2026 và 381 bằng chứng đóng băng. DB test local được xác minh tên và nonce sở hữu; DB, MinIO, Qdrant đều kiểm tra địa chỉ local trước khi chạy. Các artifact đi qua LocalStorageDriver trong Storage kiểm thử đã có từ Context623. Không dùng DB hay Storage production.

Capacity endpoint báo context 272.000 token và output tối đa 128.000 token; runtime cấp output theo phần context còn lại, không đặt lại trần cố định cho từng gói. Đây là capacity được công bố, chưa phải exact maximum đã kiểm chứng bằng inference. Không suy giới hạn từ tên model.

## Kết quả thực chạy

| Kiểm tra | Kết quả |
|---|---|
| Retry đúng request 86 đã lưu | PASS JSON/materialization, 15,734 giây, 1 lần gọi, stop, không fallback |
| Dữ liệu retry 86 | 6 thực thể, 6 assertion; request/hash và Storage readback khớp; job uncertain cũ giữ nguyên |
| Review tiếp theo ở 87 | 6/6 assertion được đánh giá supported, không missed evidence trong review này |
| Tiếp tục 87–123 | 37 phản hồi, tất cả stop, không lỗi provider, không fallback |
| Tổng mới trong Context626 | 38 dispatch/38 phản hồi; 315.308 input token, 15.005 output token theo metrics |
| Bundle cuối | 58 assertion, 9 section, 1 relation; unpublished, needs_attention |
| Lưu/đọc | Service validation, đọc lại bằng session mới và idempotency không phát sinh call đều PASS |
| Nghiệm thu độc lập | FAIL/exit 1 do machine_complete=false và packet chưa đủ; không phải lỗi kết nối |

Lượt này tái sử dụng candidate trước bước 86 từ `gh/gpt-5.6-luna`, retry 86 và các bước mới dùng `cx/gpt-6-luna` (response báo `gpt-6-luna`). Không coi đây là benchmark toàn bộ compiler chỉ bằng model mới; không relabel kết quả cũ thành kết quả do cx tạo.

## Tái sử dụng an toàn khi đổi model

Đổi configuration hash làm đổi namespace của entity/assertion, nên lần tiếp tục đầu bị guard request hash chặn ở bước 35, trước bất kỳ inference mới nào. Đã giữ nguyên job này và chẩn đoán ngoại tuyến.

Adapter kiểm thử dùng ánh xạ ID một-một của transport hiện có. Chỉ tái sử dụng khi schema, instruction và toàn bộ request trên wire giống nhau sau ánh xạ, đồng thời payload gốc chỉ đổi các trường tham chiếu ID. Nguồn, giá trị, scope, điều kiện, ngoại lệ và verdict không được đổi. Ánh xạ đã chứng minh được giữ cho các request correction tiếp theo; không thay literal hoặc viết lại lý do ngữ nghĩa.

Replay ngoại tuyến đã đi hết 1–86, không gọi model/DB. Có 30 request cần ánh xạ namespace; các bản gốc và provenance model được giữ, mỗi ánh xạ có hash và audit trong job kiểm thử mới. Các ca âm thay instruction, quote hoặc scalar đều bị chặn. Bốn ca âm của receipt/recovery cũng đạt. Lần tiếp tục thật chỉ dispatch từ 87.

Đây là **test adapter**, không phải tính năng resume đổi model mới của production. Không sửa guard của app, không đổi trạng thái uncertain cũ, không giả phê duyệt hoặc nâng cấp checkpoint cũ âm thầm.

## Đối soát nội dung

Ba mốc trọng tâm đạt kiểm tra nguồn và năm:

- **5.948/2024:** chỉ tiêu đúng nguồn 2024.
- **5.081/2025:** có nguồn số thí sinh đã nhập học, gồm locator tổng của bảng giới tính; không đổi thành chỉ tiêu kế hoạch.
- **5.173/2026:** có đúng literal và phạm vi năm 2026; giá trị 4.500 trước đó vẫn được giữ riêng.

Quality Gate vẫn chặn các vấn đề sau:

| Nhóm | Bằng chứng từ kết quả cuối |
|---|---|
| Điều kiện của tỷ lệ | Assertion 50% thiếu ràng buộc áp dụng PT1/PT4 trong gói 2024 |
| Ghép nhãn với giá trị | Một assertion gắn 17 vào nhãn mà nguồn nêu 40; 17 thuộc số nhập học khác |
| Vai trò năm | Số hiệu kế hoạch 323 bị gán vai trò data-year; một số bảng khảo sát chưa chứng minh được năm dữ liệu |
| Vai trò cột | Sáu assertion còn `metric_column_role_unresolved`, dù model có verdict supported |
| Coverage | Còn các bằng chứng chưa đối soát đủ, bao gồm một gói không có assertion nhưng còn 12 proof chưa giải quyết |
| Tổng hợp | 4/9 section unresolved, tại index 1, 4, 5, 6 |
| Chiều quan hệ | Candidate đang ghi 4.500 supersedes 5.173; source và blind direction witness yêu cầu **5.173 supersedes 4.500**. Guard phát hiện và chặn |

Có 6/14 packet chưa complete. Các lỗi ngữ nghĩa trên thuộc bundle kết hợp candidate cũ và kết quả mới; không quy tất cả cho model mới. Tạo được bundle hoặc một assertion được model đánh giá supported không thay thế các guard cơ học và kiểm tra toàn bộ scope.

## Kiểm chứng, an toàn và giới hạn

- Preflight/retry/continuation hoàn tất: exit 0. Lần tiếp tục đầu bị request drift: exit 1, 0 inference. Replay cuối: exit 0. Independent acceptance review: exit 1 đúng vì chưa complete.
- Mã ứng dụng giữ nguyên theo hash toàn bộ `backend/app` trước/sau. Shared sources/defaults/provider/domain seals và các job cũ khớp. Không reindex, xuất bản, restart, commit hoặc push.
- Full regression và benchmark 64 **NOT RUN** trong lượt này vì không sửa app. Kết quả lịch sử Context625: 93 focused PASS; full 3.792 PASS/18 FAIL nền/17 SKIP, vẫn là FAIL, không đổi thành kết quả hiện tại.
- Không tạo database kiểm thử mới. Acceptance DB và Storage tạm được giữ để đối soát các checkpoint; không xóa dữ liệu thật hoặc bypass chính sách Storage. Hai DB regression Context625 đã dọn từ lượt trước.
- Báo cáo này kết thúc phạm vi đổi model/thử lại. Không tự sửa thêm các lỗi ngữ nghĩa hoặc phê duyệt nội dung để làm kết quả xanh.

Bằng chứng ở `backend/storage/context626/`: `stage86/{result,metrics,postcheck}.json`, `offline-replay-drift.json`, `offline-replay-namespace.json`, `compiler-continued2/{result,phases,metrics,postcheck,acceptance-review,namespace-audits}.json` và `closeout.json`. Request/output/registry chứa corpus giữ trong Storage kiểm thử, không chép vào Git.
