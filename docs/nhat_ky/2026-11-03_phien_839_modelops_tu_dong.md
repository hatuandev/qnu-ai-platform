# Phiên 839 — ModelOps tự động cho trợ lý và đăng ký model

Trợ lý cho phép để trống ngân sách đầu ra qua migration 0012. Hội thoại và API tích hợp dùng cùng giá trị đã lưu, gồm chế độ tự động. Giá trị đã lưu trước đó được giữ nguyên.

API thêm model tự thử discovery khi thiếu thông tin và chưa có metadata phù hợp. Dùng kết quả hiện hành nếu có, giữ ngân sách tạm tính khi server không công bố.

Managed chat chỉ thử lại một lần khi request tự động bị từ chối rõ ràng qua HTTP 400/422 và provider trả mức đầu ra thấp hơn có thể xác minh. Lưu quan sát trong tiến trình tối đa mười phút theo provider, endpoint và model. Không ghi đè capacity đã công bố. Compiler giữ lựa chọn tự động khi chạy các phần. Các lỗi context hoặc cắt đầu ra vẫn do từng luồng xử lý.

Chưa áp migration lên DB ứng dụng và chưa gọi model thật.

Rà toàn bộ caller còn phát hiện viết lại câu hỏi nối tiếp đặt 1.024 token và
policy kiểm chứng mặc định 2.048, chặn trên 16.000. Đã bỏ các mức mặc định này:
rewrite dùng ModelOps tự động; verification chấp nhận null hoặc số dương do
người dùng chọn. FE đồng bộ nullable, bỏ trần 16.000. Policy đã lưu giữ số cũ.
OCR ảnh legacy có override môi trường tùy chọn thay mặc định 8.192; run cũ vẫn
đọc số đã ghim. MinerU không thay đổi.

Kiểm tra hiện có: frontend trọng tâm 66/66, build/TypeScript và Ruff phạm vi
đạt. Full frontend trước batch cuối: 739 đạt/1 lỗi ở
ocr-original-preview.test.tsx, ca gọi onPageChange khi số trang vượt tổng.
Không sửa vùng preview đang có diff riêng. Backend full đang chạy DB cô lập;
hai lượt sơ bộ đã dừng khi phạm vi bổ sung, receipt xác nhận DB đã dọn.

Kiểm chứng sau batch đầy đủ:

- `frontendV1`: `npx vitest run --maxWorkers=2` đạt 741/741, exit 0.
  Các lần lỗi preview/timeout trước đó vẫn giữ log; chưa sửa component preview
  trong phạm vi ngân sách. Bộ trọng tâm 7 file đạt 66/66.
- Root: harness cô lập với các file capacity/discovery/budget/assistant follow-up,
  policy kiểm chứng, OCR config và migration đạt 85/85, exit 0, 116,44 giây pytest.
  DB qnu_v1_test_35f011bc6ee74dcb đã dọn, sentinel bảo toàn.
- Full backend hiện chạy trên DB qnu_v1_test_11e503375cb94671. Đã ghi nhận
  test_docx_table_has_real_structure_and_original_is_unchanged thất bại;
  chưa có tổng kết cuối. Không gọi model thật, không retry benchmark để làm xanh.

Đã bỏ hai biến output không còn được dùng khỏi Compose và mẫu môi trường root;
mẫu OCR legacy để override ở dạng chú thích. Cập nhật compiler-v1, model-capacity,
ocr-processing, rag-answers và quy trình tài liệu lớn theo chế độ tự động.
`docker compose --env-file .env.dokploy.example config --quiet` với các giá trị
kiểm thử tổng hợp đạt exit 0; không tạo container. UTF-8 không BOM/LF và
`git diff --check` đạt.

Probe schema ứng dụng từ cấu hình mặc định backendV1 bị PostgreSQL từ chối
xác thực. Không đoán credential, không chạy migration lên DB ứng dụng, không
restart. Migration0012 đã được harness áp thành công trên các DB test riêng.

## Kết quả cuối

- Full backend root qua harness cô lập: **1.323 PASS / 2 FAIL / 0 SKIP / 0 ERROR**,
  1.325 node đối chiếu JUnit, exit 1, pytest 2.546,30 giây. Receipt xác nhận DB
  qnu_v1_test_11e503375cb94671 đã dọn và sentinel bảo toàn. Tổng gate vẫn FAIL.
- `test_docx_table_has_real_structure_and_original_is_unchanged`: thất bại tại
  `any(c["header"] for c in cells)`. Cùng test/loại assertion đã có trong báo cáo
  full qnu_v1_test_649bcbc70b714402 trước thay đổi ngân sách. Không sửa parser
  hoặc đổi assertion bảng trong phạm vi này.
- `test_pdf_flow_produces_pinned_evidence`: snapshot full còn assertion cũ 8.192,
  nhận 131.072 theo fixture model. Tái hiện riêng xác nhận đúng chênh lệch đó.
  Cập nhật test kiểm tra ngân sách lưu null và hai request gửi đúng mức model;
  lần đầu bổ sung assert đọc sai đường dẫn metadata đã được sửa sang `limits`.
  Kiểm tra cuối riêng **1 PASS**, exit 0, 6,77 giây; DB
  qnu_v1_test_839651d86a474760 đã dọn. Không thay mã xử lý để làm test xanh.
- Backend trọng tâm 85 PASS trước đó và regression OCR cuối 1 PASS là các gate
  riêng; không đổi nhãn full thành PASS, không cộng trùng chúng vào full.
- Frontend full cuối **741 PASS**, trọng tâm 66 PASS, build/TypeScript PASS,
  E2E typecheck PASS, Biome16file PASS. Ruff phạm vi và diff whitespace PASS.
  Docker Compose config tổng hợp PASS; 8 unit runner V1 PASS.
- Không gọi model thật, không restart/reindex/publish, không Git commit/push.
  DB ứng dụng chưa migration do cấu hình kết nối mặc định không xác thực được.
  Khi dùng môi trường V1 đã cấu hình đúng DB, áp migration0012 bằng lệnh migrate
  của runner trước khi chạy backend mới; các DB test đã chứng minh upgrade đạt.
