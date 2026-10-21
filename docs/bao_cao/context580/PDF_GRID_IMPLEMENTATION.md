# Context580 — Sửa lưới PDF, giữ QNU RAG Markdown v1.0

Đã sửa riêng việc nhận dạng cấu trúc PDF và khóa tái sử dụng artifact PDF. Parser DOCX, chuẩn Markdown/JSON, ModelOps và chính sách Quality Gate giữ nguyên. Bản kiểm thử từ PDF thật có Bảng 1 đúng **16 hàng × 12 cột**, nhận 3 tầng header; **192/192 vị trí ô khớp DOCX nguồn** sau khi bỏ khác biệt khoảng trắng.

## Thay đổi

- `parsers/pdf_grid.py`: dùng đường kẻ thật trước; vùng tô nền chỉ bổ sung cạnh ô khi khớp cả hai trục lưới đã nhận được. Giữ các phương án nhận dạng ban đầu và drawing index/bbox, không sửa PDF gốc. Bảng không được phương án mới nhận ra vẫn được giữ ở trạng thái chưa xác minh.
- Phục hồi nhóm ô một cột có viền khép kín từ danh sách cells của PyMuPDF. Tách các nhóm theo khoảng cách và loại các ô đã nằm trong bảng khác, tránh ghép bảng cách xa nhau hoặc kéo dòng gộp của bảng khác vào. Bảng 3 trang 12 từ 3 cột giả về 1 cột; các dòng `0`, `00027`, mã và dữ liệu chưa công bố vẫn là dữ liệu.
- `parsers/blocks.py`: các đường gọi nhận bảng PDF hiện có dùng chung bộ nhận lưới mới; lựa chọn chiến lược tường minh của caller vẫn được tôn trọng.
- `parsers/pdf_header_roles.py`, `pdf_evidence.py`, `pdf_tables.py`: header cần dải nền liên tục, chữ đậm, chuyển tiếp rõ sang ít nhất hai dòng dữ liệu và không có ô gộp vượt ranh giới header/body. Không lấy từ vựng, engine names/bbox/proposal hoặc việc dòng sau là số làm bằng chứng vai trò. Thiếu căn cứ vẫn giữ mọi dòng và `table_header_unresolved`.
- `parsers/pdf_structure.py`: nhận thêm đoạn viền ngắn có vị trí khớp cạnh bảng, tránh biến chúng thành hình nội dung. Giữ raw drawings và hình thật. Builder PDF tăng từ v2 lên v3.
- `services/source_extraction.py`, `source_ingestion_service.py`: fingerprint PDF chứa phiên bản builder PDF, dùng trong khóa cache và normalizer của import/reparse mới. Không tái dùng artifact của parser PDF cũ. Fingerprint DOCX/XLSX vẫn bằng giá trị cũ; không đổi logic bóc tách Office.

Không có từ điển header viết tay, tên chương trình hoặc số 12 gán cứng trong thuật toán. Các ngưỡng hình học là điểm PDF/tỷ lệ ô, không phải quy tắc riêng cho một bảng hay một câu benchmark.

## Kiểm chứng trên file thật

PDF 18 trang có SHA256 `082c412e145a9ef39ae50110ae16cc80c17d612e2f0e00f9d16ee78c7c1c3b02`. Đọc lại native từ bytes local, tái dùng đúng OCR đã lưu của trang 13; không gọi OCR/LLM mới hoặc nhập lại vào kho đang chạy.

| Kiểm tra | Kết quả |
| --- | --- |
| Bảng 1 | 27×34 → 16×12; 3 tầng header; 13 dòng body, gồm dòng tổng |
| Đối chiếu ô Bảng 1 với DOCX | 192 vị trí / 0 sai khác sau chuẩn khoảng trắng |
| Nhóm, Mã CT, Tên chương trình | Ba ô riêng, header path riêng |
| Cột 2027 / Dự kiến / Ước tính (SV) | Giữ đúng đường dẫn header |
| Viền bị coi là hình ở trang 6 | 20 → 0; raw vẫn còn |
| Bảng dài trang 9–11 | 21 → 7 cột ở từng phần |
| Bảng 3 trang 12 | 3 → 1 cột; 7 hàng, 1 header + 6 dữ liệu |
| Cặp MD/JSON qua service tạo artifact thật | PASS trong Storage local riêng; hash/read-back/projection đạt |
| Cú pháp QNU RAG Markdown Standard v1.0 | PASS |
| Round-trip JSON → Markdown | Nội dung parse khớp; thứ tự key metadata có thể đổi khi JSON được sắp xếp |
| Nguồn PDF | Hash không đổi |

Còn 12 vùng bảng vật lý tương ứng các phần bảng nguồn. Những con số này không tự chứng minh mọi quan hệ nối trang đã được xác nhận. Ví dụ một dòng dài ở Bảng 2 tách qua hai trang được giữ cả hai phần; cảnh báo continuation vẫn còn, không ghép scope hay tự phê duyệt.

Artifact [Markdown chuẩn](../../../backend/storage/context580/standard.md), [JSON](../../../backend/storage/context580/structured.json) và [bản đọc](../../../backend/storage/context580/reader.md) thử nghiệm được giữ riêng. ID trong đó là `context580-offline` / `context580-test-only`, không phải revision phục vụ. `real-pdf-verification.json` lưu hash, hình dạng bảng, header paths và kết quả kiểm tra; mã probe và OCR thô không đưa vào Git.

## Môi trường và kiểm thử

Preflight xác minh development và các kết nối PostgreSQL/MinIO/Qdrant đều loopback. Chỉ tạo DB có tiền tố `qnu_test_context580_` kèm nonce và marker sở hữu; schema tạo trong DB test đó, không migration DB dùng chung. Tests dùng Storage local tạm theo nonce; endpoint ngoài phạm vi test chuyển về `127.0.0.1:1`, auto-migrate/seed tắt. Metadata defaults typed được sao chép sang DB nghiệm thu riêng, không sao chép provider/credential hoặc gọi inference.

Regression mới trong `backend/tests/test_pdf_grid_fidelity.py`: bảng nền màu, nhiều tầng header, body có nền, thiếu từng loại bằng chứng header, dòng đầu Alpha/North là dữ liệu, bảng fill-only cạnh bảng có viền, bảng một cột và fingerprint PDF/DOCX. Các regression cũ về engine header proposal, merged body, duplicate legend và provenance tiếp tục được chạy.

- Trước sửa: snapshot mã cũ được preload và xác minh đường dẫn module; bộ regression mới phiên bản 8 ca đạt 4 PASS / 4 FAIL, exit1. Hai ca header, ca metadata fallback và ca một cột còn lỗi. Guard cache thêm sau đó có kiểm chứng riêng ở bản sửa.
- Bộ parser PDF/DOCX cuối, gồm guard cache và giới hạn schema: 124 PASS + 23 subtests, exit0. Fingerprint PDF dài 32 ký tự được lưu/đọc chính xác trong bảng tạm của DB test; không thay schema hiện có.
- Bộ mở rộng cuối: 167 PASS / 2 FAIL + 23 subtests, exit1. Hai lỗi là các ID nền `test_shared_capacity_bounds_twenty_simultaneous_requests` và `test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item`, cùng nguyên nhân baseline576: kiểm giới hạn server AI và Redis test bị từ chối kết nối. Không đổi chúng thành PASS.
- Ruff 9 file sửa: PASS, exit0.
- Full regression trên mã chốt: **2958 PASS / 18 FAIL / 17 SKIP + 23 subtests PASS**, exit1, 450.85 giây. Đối chiếu baseline576: đủ 18 ID lỗi cũ, cùng nguyên nhân đầu tiên, 0 lỗi mới, 0 test cũ đổi trạng thái hoặc mất ID. Tổng suite vẫn là FAIL. [Bảng đối chiếu theo ID](../../../backend/storage/context580/test-comparison.json) và XML/log `checks-handoff/full-verified.*` giữ bằng chứng. Các lượt full dùng mã trước bổ sung hoặc bị ngắt không thay thế kết quả này.

Lệnh chạy từ root: `backend/.venv/Scripts/python.exe backend/storage/context580/checks.py run ...` hoặc `handoff_checks.py run ...`; helper đặt cwd Pytest ở `backend`. Baseline/full/focused có XML theo test ID, receipt exit code và log trong Storage ignored. Probe thật: `backend/.venv/Scripts/python.exe backend/storage/context580/verify_pdf.py`, exit0. Lượt probe đầu có assertion byte-order metadata chưa phù hợp; đã đối chiếu nội dung parse MD/JSON rồi chạy lại đạt, không sửa app để che lỗi.

## Giới hạn và bàn giao

Đây là bản sửa parser và kiểm thử offline qua service artifact thật; không phải upload/import/vector/publication E2E mới. Revision đang có `ks_rev_1071c152fab0` được giữ nguyên. Muốn giao diện nhận kết quả mới cần backend/worker nạp mã mới và tạo revision bóc tách mới trong phạm vi được giao; không ghi đè artifact cũ.

Toàn tài liệu vẫn còn cờ cần đối soát: heading suy luận, hai bảng chưa rõ header, hai continuation, khác biệt native/OCR, hình chưa chép nội dung, ký hiệu chưa rõ và footnote. Trong bản replay còn 14 figure, không tự kết luận chúng là nhiễu; không tự duyệt quan hệ hoặc ép toàn tài liệu thành AUTO_READY.

Không sửa parser DOCX, không hạ Quality Gate, không ghi dữ liệu kho đang chạy, không gọi LLM/OCR mới, không reindex/publish/restart/deploy/commit/push. Giữ mọi sửa đổi Context578–579 và PDF local chưa track. **Cả hai DB test đã xóa sau kiểm marker sở hữu**. Kiểm duyệt tự động đã chặn xóa đệ quy Storage tạm ở lượt đầu; giữ nguyên các thư mục runtime, không thử đường khác để vượt policy. Các bản xuất/báo cáo cần bàn giao trong context580 được chủ động giữ lại.
