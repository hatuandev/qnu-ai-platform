# Phiên 828 — Test MinerU sau giảm VRAM

## Yêu cầu và phạm vi

Người dùng báo `VLLM_GPU_MEMORY_UTILIZATION` từ 0.19 xuống 0.17 và yêu cầu chạy lại để kiểm tra chất lượng. Dùng cùng hai PDF/hash với baseline 822, 61 trang; giữ toàn bộ raw OCR và gold. Không sửa code ứng dụng, ModelOps, review, compiler, index, publication; không restart/push/deploy. Giữ nguyên các thay đổi legacy/docs có sẵn.

## Cách đo và kết quả thực

Mỗi file một create/upload, chạy tuần tự, không retry. Runtime lấy từ ModelOps bằng actor thật qua kiểm tra quyền workspace; bí mật chỉ trong bộ nhớ. Health MinerU 4.1.3; không có telemetry xác nhận VRAM hiệu lực.

| Nguồn | Trang | Tổng thời gian cũ → mới | Parser cũ → mới | CER mẫu cũ → mới |
|---|---:|---:|---:|---:|
| 363 | 32/32 | 131,00 → 129,11s | 115,390 → 115,519s | 4/3.449 → 4/3.449, 0,116% |
| 2699 | 29/29 | 13,14 → 11,61s | 8,242 → 8,224s | 8/3.053 → 8/3.053, 0,262% |

Gold được ghim trước request: 363 revision nguồn 824, 14 đoạn/10 trang/755 từ; 2699 20 đoạn/13 trang/664 từ. Chấm lại baseline với cùng gold. Không phải CER toàn file hoặc chấm độc lập. WER giữ 5/755 và 8/664.

- Kiểm tra ZIP/hash/tham chiếu ảnh/bbox/số trang: PASS, đủ 61 trang có chữ.
- Nội dung và hình dạng 34 bảng giữ nguyên; văn bản chuẩn hóa giống 31/32 trang 363, 29/29 trang 2699.
- Probe giữ 15/16 và 22/22; cùng hàng bảng 2699 giữ 4/5, T02 trang 19 còn lỗi chữ cũ. Không coi toàn bộ OCR chất lượng PASS.
- Trang 30 363 ngoài mẫu có lỗi mới `CSĐT` → `CSDT`, đã đối chiếu ảnh gốc; chú thích 3 đổi biểu diễn định dạng. Không sửa gold hậu nghiệm hay gộp lỗi này vào CER mẫu.
- Cụm cơ bản trang 15/20 đúng và giữ nguyên; lỗi dấu cũ trang 24/31 còn.

Chưa thấy giảm chất lượng đáng kể, nhưng có một lỗi mới ngoài mẫu nên không tuyên bố tương đương tuyệt đối. Không thể quy nguyên nhân cho VRAM: thiếu kiểm soát cache, cold/warm, tải và số lượt. Tổng thời gian hơi giảm nhưng parser gần như không đổi.

## Kiểm chứng và lưu trữ

Từ root: chạy `backendV1/.venv/Scripts/python.exe tmp/mineru828/run.py`, `... compare.py`, `... detail.py`, cả ba exit 0. Xem ảnh render nguồn trang 30. Full BE/FE NOT RUN vì không đổi ứng dụng. Artifact/báo cáo/nguồn chấm trong `tmp/mineru828/`, không đưa corpus vào Git. Báo cáo chi tiết `tmp/mineru828/REPORT.md`.

Tiếp theo: có thể giữ 0.17 cho sử dụng thử, vẫn cần đối chiếu/sửa OCR. Muốn quy nguyên nhân cấu hình phải đo A/B lặp có kiểm soát, chưa nằm trong lượt này.
