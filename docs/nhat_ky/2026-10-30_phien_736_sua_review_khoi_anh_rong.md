# Phiên 736 — Giữ bằng chứng khối ảnh rỗng trong review

Ngày: 2026-10-30. Người dùng gửi log E2E và yêu cầu chẩn đoán, sửa lỗi.

## Căn cứ và nguyên nhân

- Log và checkpoint phiên `7f9361961005`: upload/extraction/compilation PASS; publication FAIL do một finding uncertain; chat/permissions/lifecycle bị chặn đúng prerequisite.
- API cho thấy trang scan có một figure gốc text rỗng, origin native, requires_review=true, cùng hai block title/text từ OCR. Review cũ chỉ có hai source unit nên không đối chiếu được unknown nhắc đến figure.
- `review/material.py` lọc block không có text. Snapshot vẫn giữ figure nhưng context gửi model chỉ dùng source_units và bỏ pages/evidence, gây thiếu bằng chứng.
- Đã xem ảnh trang gốc trong môi trường thử: đây là lớp ảnh cả trang scan. Không sửa OCR hoặc dùng việc xem ảnh để tự xác nhận finding.

## Thay đổi có phạm vi

- `material.py`: giữ mọi block thường, kể cả rỗng/whitespace, với evidence_id, origin, requires_review, label nếu có. Giữ bbox, trang, revision và OCR run. Ô bảng dùng ID riêng của ô, không lẫn ID block; không tạo text thay thế.
- `report.py`: prompt v4 phân biệt text rỗng của block với không có chữ trên ảnh/trang. Review đánh giá bản nháp so với nguồn trích xuất: giới hạn/unknown được phản ánh đúng có thể là covered, không xác nhận OCR đúng. Tự đoán nội dung hoặc chưa đối chiếu được vẫn là finding. Không thay coverage validator hoặc gate phát hành.
- `service.py`: trace ghi đúng prompt_version, tách khỏi schema report v1; hash prompt vẫn được ghi.
- Thêm unit/integration regression và cập nhật phần giải thích khối ảnh trong hướng dẫn test ngắn.
- Không thay source bytes, canonical, bản nháp, model capacity hoặc Compiler output 8192. Bảo toàn diff phiên 733–735.

## Kiểm chứng

- Trước sửa: 12 regression mới FAIL đúng lỗi thiếu block/metadata.
- Sau batch cuối: 43 test trọng tâm PASS (review API 652, structured schema 655, unit và integration 736), 135.24s, exit 0. Unit/keyed riêng 17 PASS. Ruff check và format năm file đạt.
- API integration dùng DB PostgreSQL mới `qnu_v1_test_review_736_*`, local storage và loopback provider; DB được dọn sau subprocess, không truncate DB E2E đang phục vụ.
- Full-suite gate `pytest -v -x -o faulthandler_timeout=45`: **FAIL**, 905 collected, 25 PASS/1 FAIL, dừng ở lỗi đầu sau 206.48s, exit 1. ID: `tests/integration/test_auto_extraction_710.py::test_docx_table_has_real_structure_and_original_is_unchanged`. Gotenberg trả HTTP 500 (`docx_conversion_failed`) với fixture DOCX của test này; nằm ở bước extraction trước Compiler/review, không sửa parser/test helper đó trong task này. Không có bằng chứng full suite PASS. Log `tmp/review-736-full-final.log`. Lượt rộng trước đó cũng gặp cùng ID và đã dừng; regression cuối chạy trên batch mã v4.
- UTF-8 không BOM/LF, liên kết local mới và diff-check đạt. Không thêm secret, Base64 hoặc nội dung OCR vào tài liệu Git.

## Phục hồi phiên live

Chạy API tạm ẩn trên cổng riêng, cùng phạm vi E2E để nạp mã mới; không dừng cửa sổ serve của người dùng. Mỗi lượt review có idempotency key riêng và giữ raw/report cũ. API tạm đã đóng sau tác vụ.

1. Review v3 nhận đủ ba source unit, draft unknown supported nhưng vẫn uncertain về ảnh trực quan. Báo cáo này được giữ, không acknowledge finding.
2. Làm rõ phạm vi đối chiếu trong prompt v4, tạo lượt review mới `rvw_889caa710d12`: HTTP 200, completed, 3 source/5 draft units, finding_count=0. Hash draft trước/sau không đổi. Chỉ cập nhật review ID trong checkpoint thử sau khi báo cáo hoàn tất.
3. Chạy ` .\test-v1-e2e.ps1 run publication`: PASS, 21.3s, exit 0; API xác nhận cả hai phiên bản published, index hoàn tất qua bài test. Original hash hai nguồn vẫn khớp checkpoint.

Báo cáo: `tmp/v1-e2e/7f9361961005/runs/publication-1793332740998763500`.
Log: `tmp/review-736-regression-final.log`, `tmp/review-736-live.log`, `tmp/review-736-live-v4.log`, `tmp/review-736-publication.log`.

## Giới hạn và bước tiếp

- Live review đạt trên fixture này không chứng minh OCR đúng mọi ảnh hoặc không có lỗi ngữ nghĩa ở nguồn khác. Unknown được giữ; không biến NFC/metadata thành chứng cứ OCR hoàn hảo.
- Không chạy lại chat/permissions/lifecycle, không purge hay cleanup/init. Người dùng giữ serve và chạy ba chặng đó theo thứ tự.
- API đang giữ trong cửa sổ serve cũ chưa nạp mã review mới; các bước sau publication không cần review lại. Khi tạo phiên thử mới, serve mới nạp bản sửa. Nếu cần tạo review mới trong phiên hiện tại, dừng serve bằng Ctrl+C rồi serve lại, giữ session; không chạy compilation với hy vọng tự thay review trong checkpoint.

[Hướng dẫn test](../quy_trinh/V1_QUY_TRINH_TEST_LAI.md).
