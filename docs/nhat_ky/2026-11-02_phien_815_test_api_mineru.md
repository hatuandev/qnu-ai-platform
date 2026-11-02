# Phiên 815 — Thử API MinerU trên server QNU

## Phạm vi

User cung cấp file HTTP và yêu cầu test thử. Chạy ad-hoc theo API đó, dùng credential tại máy chỉ trong bộ nhớ, không ghi key/header/upload URL có chữ ký vào báo cáo. Không tích hợp hoặc thay OCR provider trong ứng dụng. Giữ nhánh v1.0.3; không commit/push/restart/reindex.

Đối chiếu OpenAPI thực tế trước khi tạo task; endpoint không khóa trả401, có khóa200, health/parser tự báo4.1.3. Tier standard có sẵn. Một mẫu PDF native2trang của E2E và một PDF trích nguyên trang15/32 từ Quy chế363, không sửa bytes nguồn gốc. Mỗi mẫu chỉ create/upload một lần, chỉ GET để polling; không retry inference để xanh.

## Kết quả live

| Mẫu | Task | Tạo → completed | Parser duration | Kết quả |
| --- | --- | ---: | ---: | --- |
| Native PDF2trang | job_7b96c2adcf1daec06d7ae5f9 | 6,42s | 3133ms | PASS luồng API; parse_mode txt |
| Scan363 trang15/32 | job_4f295a4037c16f2f065be222 | 39,81s | 36846ms | PASS luồng API; parse_mode ocr |

Create202, raw binary PUT200, status200, download200/ZIP cho cả hai. Đường download theo file_id như ví dụ user hoạt động. ZIP native3tệp, scan4tệp (MD, structured JSON, middle JSON, ảnh bảng). Lưu nguyên ZIP, hash artifact và mapping trang trong tmp/mineru815/.

Kiểm chất lượng có giới hạn: native2/2trang trùng text nguồn nếu bỏ khác biệt khoảng trắng, 13/13bbox hợp lệ. Scan2trang có16/16bbox hợp lệ; năm probe mục tiêu được đối chiếu ảnh nguồn đều khớp. Bảng trang32 đúng4hàng ×8cột/32ô, còn ảnh. Không đo CER/WER hoặc tuyên bố toàn32trang PASS OCR.

## Điểm cần giữ khi tích hợp

Middle JSON có schema docvortex.middle2.0, page/block/bbox và HTML table; bảng tiếp nối dùng td trong HTML nhưng Markdown dùng hàng đầu làm header. Không nên suy cấu trúc chỉ từ Markdown. Chưa thấy bbox từng ô trong HTML trả về; chưa đánh giá rowspan/colspan hoặc nối với trang31 vì không gửi trang đó. Không tự tạo dữ kiện header/footnote bị thiếu.

Catalog /mineru/v1/models trả MinerU; /v1/models của QNU trả4ID. Không gọi inference Qwen/BGE/Nemotron nên không coi catalog là kiểm thử model.

Artifact để user mở: tmp/mineru815/REPORT.md, scan363/extracted/markdown.md, structured_content.json, middle_json.json và scan363/output.zip. Hash PDF gốc được kiểm lại khớp; không sửa chính tả bằng AI/compiler hoặc đăng ký publication. Không cần chạy unit/build cho lượt kiểm API và tài liệu này. Nhận xét so sánh hơn Nemotron và nghiệm thu toàn PDF là NOT RUN.
