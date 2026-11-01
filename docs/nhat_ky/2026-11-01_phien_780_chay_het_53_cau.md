# Phiên780 — Tiếp tục đủ53 câu, giữ kết quả lần đầu

Người dùng yêu cầu chạy hết câu hỏi sau khi phiên779 dừng ở F14. Phạm vi là39 câu chưa dispatch, giữ14 kết quả cũ, không sửa RAG/compiler/ModelOps/prompt/benchmark/bộ chấm, không retry để làm xanh.

## Cách thực hiện

- Đọc checkpoint và báo cáo779:12PASS,2FAIL,39NOT_RUN. Xác minh cả39NOT_RUN chưa có dispatch/turn trong checkpoint; không gửi F01–F14 lần nữa.
- Dùng runner Playwright tạm trong `tmp/remaining780.spec.ts`, tái sử dụng đúng `authenticate`, `askAdmissionQuestion`, `checkAdmissionAnswer` và các helper preflight hiện có. Không thêm API/model adapter hoặc thay code ứng dụng.
- Kiểm tra lại SHA256 ba nguồn, publication/index manifest, assistant/provider/reranker và fingerprint cohort cũ. Budget phải khớp lần đầu; quota chỉ đọc. Không đổi cấu hình assistant nếu cohort đã khóa.
- Mỗi câu mới lưu dấu dispatch trước POST, đúng idempotency-key cũ theo benchmark/case. Không phát lại request lỗi. Theo yêu cầu chạy hết, các lỗi hợp đồng từng câu (`answer_response_invalid`, `answer_cell_selection_required` và các mã citation/cell/source/verification invalid) giữ FAIL rồi chuyển câu kế; lỗi hạ tầng/quyền/quota/snapshot vẫn chặn để tránh gọi sai nguồn hoặc gửi không kiểm soát. Lượt đầu dừng ở BC24-02 do mã cell_selection cũng là502; sau khi đọc phân loại, tiếp tục đúng20NOT_RUN, không gửi lại33câu trước.
- Báo cáo tổng hợp giữ nguyên từng record F01–F14, đồng thời giữ nguyên file report gốc. Kết quả toàn cohort vẫn FAIL khi còn lỗi cũ; không cộng PASS từ lượt retry. Đây là một cohort tiếp tục qua hai thời điểm, không phải53 request chạy liên tục.

## Kết quả

**Đã gửi53/53 câu, tổng hợp37PASS/16FAIL/0NOT_RUN.** Kết quả vẫn FAIL. Không sửa assertion hoặc câu trả lời để đổi kết quả.

| Nhóm | PASS | FAIL |
|---|---:|---:|
| Ngưỡng đầu vào2026 | 16 | 3 |
| Thông tin2025 | 9 | 3 |
| Báo cáo2024 | 7 | 5 |
| Đa tài liệu/phạm vi | 5 | 5 |

Các lỗi được giữ:

- F13: bộ chấm yêu cầu cùng một statement có ngưỡng và ngoại lệ; model tách hai statement. Giữ FAIL của779, chưa điều chỉnh hợp đồng/chấm ngữ nghĩa.
- F14, I25-07, MX-04: `answer_response_invalid`.
- F18, I25-04: `chat_output_truncated`.
- BC24-02, BC24-05, BC24-10: `answer_cell_selection_required`.
- I25-05, BC24-04, BC24-08, MX-02, MX-05, MX-10: model từ chối câu mà benchmark kỳ vọng có căn cứ.
- MX-01: **gián đoạn**, không tính là model trả sai. User ngắt turn khi đã dispatch; API/FE/runner cùng dừng. Sau bật lại cùng phiên, server vẫn ghi turn running. Đọc lại bằng GET, chặn POST với câu đã gửi, ghi FAIL `interrupted_inflight` trong report và tiếp tục9câu mới. Không sửa trạng thái DB, không chờ vô hạn, không nhận PASS cho lượt chưa xác nhận.

Đối chiếu DB chỉ đọc lúc12:24 ngày01/11 (Asia/Bangkok): **53turn/53idempotency-key,0duplicate**,44completed/8failed/1running(MX-01). Đây là đủ53 câu đã được gửi, nhưng chỉ52câu có trạng thái server kết thúc. Chưa thể nghiệm thu MX-01; giữ lịch sử để đối soát tiếp, không gửi lại âm thầm. Kết quả14records gốc được so sánh equality với report779 và không đổi.

## Bằng chứng và vận hành

- Phiên live giữ `93faa11f0caf`, API64624/FE64625. Sau user ngắt, xác minh dịch vụ không còn listen rồi bật serveẩn30640 để tiếp tục đúng phiên (sourcehashkhôngđổi); không cleanup/init/reindex/xuất bản lại. Gỡ stage.lock mồ côi sau xác minh runner cũ đã dừng. Một lần đối soát gặp ERR_CONNECTION_REFUSED trước đăng nhập, không dispatch câu mới; được giữ trong artifact. Lượt đọcMX-01 sau restart được dừng riêng runner vì server vẫnrunning, không dừngserve hoặc gửi lạiMX-01.
- Lệnh: `backendV1/.venv/Scripts/python.exe -X utf8 tmp/run-remaining780.py`; harness gọi Playwright `--config tmp/remaining780.config.ts --project=desktop-chromium --headed`, một worker/retries0/traceoff/videooff, dùng bridge đăng nhập hiện có và biến hạ tầng riêng của phiên.
- Gốc: `tmp/v1-e2e/93faa11f0caf/runs/admissions-chat-1793507789510629500/admissions-answers.json`.
- Các chặng tiếp tục: `admissions-chat-remaining-1793509092195536400` (đếnBC24-02), `admissions-chat-remaining-1793509929381740900` (đếnBC24-12 rồibịngắt), `admissions-chat-remaining-1793510267924618100` (servechưabật,khônggọimodel), `admissions-chat-remaining-1793510314242605100` (đọcMX-01running), trong `tmp/v1-e2e/93faa11f0caf/runs/`.
- **Tổng hợp cuối:** `tmp/v1-e2e/93faa11f0caf/runs/admissions-chat-remaining-1793510384663788200/admissions-answers.json`. Playwright exit1 vì còn16FAIL, không làm xanh cohort.
- Báo cáo và runner tạm không vào Git; không chép nội dung nguồn/prompt/bí mật vào memory. F13/F14 giữ nguyên; nhãn vẫn draft, đánh giá ngữ nghĩa độc lập NOT_RUN.
