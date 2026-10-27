# Context614 — Kết quả compiler ba DOCX 2024–2026

## Kết luận

Compiler đã tạo bundle, lưu và đọc lại khớp hoàn toàn qua service trong database/LocalStorage thử riêng. Kết quả vẫn **needs_attention**, **machine_complete=false**, **chưa APPROVED và chưa xuất bản**. Liên kết cấu trúc đã được bổ sung; hiểu đúng toàn bộ ngữ nghĩa vẫn chưa đạt. Không áp các candidate vào dữ liệu có hiệu lực.

| Hạng mục | Kết quả cuối |
|---|---:|
| Nguồn DOCX giữ hash | 3 |
| Proof nguyên gốc giữ trong catalog | 381 |
| Proof có navigation cấu trúc | 362 |
| Proof được chọn cho chủ đề | 129 |
| Packet trích xuất | 42 |
| Thực thể / assertion | 102 / 116 |
| Section / group / relation ứng viên | 36 / 36 / 18 |
| Assertion xuất hiện trong section | 116/116 |
| Packet complete | 11/42 |
| Giá trị unknown | 54, tất cả value=null |
| Cặp liên nguồn đã xét | 66/66, không còn pending trong danh sách này |

Catalog snapshot giữ `59eb474ad57dc88b943504a46bc9cce8c718a302072b309c5c87022bd7f6ef66`. Không suy completeness của toàn tri thức từ 66 cặp: đây là tập ứng viên tìm bằng thuật toán nhãn hiện có, không phải mọi quan hệ có thể tồn tại.

## Đối soát nội dung độc lập

| Trường hợp | Bằng chứng và kết quả | Quyết định |
|---|---|---|
| 1.070 | Được nối tới mục sau đại học/thạc sĩ; entity cuối là tổng chỉ tiêu trình độ thạc sĩ, không còn mang nhãn tổng đại học. Reviewer vẫn để unresolved vì header chưa được xác nhận đầy đủ. | Giữ candidate; không coi là quota đại học đã xác minh. |
| 3.362 | Raw paragraph/hàng tổng và vị trí cột khảo sát được giữ; không có affirmative assertion mang giá trị này thành quota giáo viên trong bundle cuối. | Không tự chuyển unknown thành 0 hoặc xóa raw proof. |
| **5.081** | **Vẫn có lỗi ngữ nghĩa:** model đặt tên `Total admission quota`, trong khi bảng đang tổng hợp giới tính thí sinh trúng tuyển đã nhập học. Cả item reviewer và section reviewer đánh dấu supported, nhưng đối soát trực tiếp xác định đây là số thực tế nhập học, không phải chỉ tiêu kế hoạch. | **Finding chặn APPROVED. Không tin riêng cờ supported của LLM.** |
| Năm/trạng thái/phạm vi | Còn các scope không chép đúng literal; có claim suy trạng thái proposed từ heading; có một claim unknown bị nguồn bác bỏ vì nguồn đã nêu quan hệ phụ thuộc. | Giữ blocker, không sửa dữ kiện bằng phỏng đoán. |

Tại trường hợp 5.081, ngữ cảnh gửi model đã có preamble về thí sinh nam/nữ trúng tuyển đã nhập học, header candidate giới tính/số lượng/tỷ lệ, vị trí ô và hàng tổng. Vì vậy lỗi còn lại không phải mất con số hoặc không truyền được chuỗi liên kết; model vẫn gán sai vai trò metric dù có raw context. Cần siết hợp đồng giữa nhãn ngữ nghĩa đề xuất và nhãn/loại số liệu nguyên văn, không vá bằng từ khóa hay số của ca này.

## Các blocker đang giữ

- Item review: 78 verdict supported, 37 unresolved, 1 contradicted. Các số này là **kết quả model**, không phải điểm chính xác/gold; finding 5.081 cho thấy có false supported.
- Cờ không đạt, có thể trùng nhau: entity_scope 21, temporal_roles 14, conditions_complete 3.
- 15 lỗi kiểm tra literal scope; 9 proof còn trong missed coverage; các nhóm này có thể trùng với những số trên.
- Một repair coverage NOT_RUN do request đầy đủ không vừa ngân sách; required proof vẫn được giữ và complete=false. Không tính NOT_RUN thành PASS.
- Synthesis: 29 section supported/7 unresolved; 10 relation supported/8 unresolved; 3 direction issues. Quan hệ vẫn là ứng viên, không có hiệu lực.

Không đổi nhãn/value hoặc xóa assertion để làm bản chạy này đạt. Không gọi thêm model sau lượt hoàn tất chỉ để tô lại kết quả.

## Model và chi phí thực tế

Giữ `ollama/gpt-oss:120b`, gửi reasoning medium/output 8.192, workflow context 24.000. Model mặc định ứng dụng vẫn `gh/gpt-6-luna`; cấu hình provider/default được đối soát hash không đổi. Thinking được xác nhận ở wire, không khẳng định nội bộ upstream thực thi ra sao. Profile context của GPT-OSS chưa được endpoint xác nhận; không suy từ tên model.

| Lượt | Call thật |
|---|---:|
| live — chặn trước verifier vì thiếu budget prior selection | 1 |
| live-final — chọn chủ đề xong, dừng tại cap 30 packet | 72 |
| live-extraction — dừng tại repair budget | 48 |
| live-finalized — dừng do reason vượt 400 sau một correction | 10 |
| live-final-check — dừng do phong bì correction tối thiểu chưa được dự phòng | 50 |
| **live-budget-final — hoàn tất** | **261** |
| **Tổng Context614** | **442** |

Lượt cuối tái dùng đúng 72 call chọn chủ đề đã có immutable receipt và request khớp; không gọi lại chúng. Không có stage inference khác khớp wire đủ điều kiện cache trong lượt cuối, nên không nhận công tái dùng thêm 48 call. Fixture bị chặn ở preflight không có call được giữ riêng, không cộng như inference.

Tổng usage provider báo: 2.285.049 input/479.891 output tokens; tất cả 442 finish_reason=stop, 0 fallback, output lớn nhất 4.157. Không có bằng chứng thiếu context phía provider hoặc output bị cắt; có lỗi JSON/schema và lỗi dự phòng request ở ứng dụng đã được ghi riêng. Không tính chi phí tiền khi chưa có tariff được xác nhận.

## Phạm vi thử và artifact

Đây là compiler chạy thật qua ModelOps và service/DB/Storage thật trong fixture riêng, dùng canonical đã ghim từ ba DOCX; không phải parse lại toàn bộ DOCX hoặc browser/published E2E. Quality report của fixture ghi NOT_RUN, không giả nguồn đã đạt lại toàn Quality Gate ingestion. Bộ ba nguồn không có field-note explicit; đường field-note được kiểm bằng regression độc lập.

- Receipt/bundle: `backend/storage/context614/live-budget-final/` — job cuối `kc_3aef7a1b8c6d49a8910a75de07e8a65d`.
- Bản xem: [Markdown ứng viên](../../../backend/storage/context614/exports/compiled-topic.md), [JSON ứng viên](../../../backend/storage/context614/exports/compiled-topic.json), [lưu ý sử dụng](../../../backend/storage/context614/exports/EXPORT_NOTICE.md).
- Accounting độc lập: `backend/storage/context614/independent-assessment.json`; chi tiết/proof riêng giữ trong Storage, không đưa corpus hoặc prompt vào Git.

Đã dọn cả năm database thử theo tên/nonce ownership. Storage bằng chứng được giữ theo chính sách bảo vệ, không xóa vòng hoặc tắt bảo vệ. Nguồn, shared rows, ModelOps defaults và 2.943 payload vector giữ; không reindex, publish, restart, stage, commit hoặc push.
