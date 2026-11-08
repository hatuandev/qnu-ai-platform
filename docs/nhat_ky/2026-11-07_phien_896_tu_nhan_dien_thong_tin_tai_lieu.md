# Context896 — Tự nhận diện thông tin tài liệu khi đăng ký

## Yêu cầu và phạm vi

Người dùng không muốn hiểu thuật ngữ metadata hoặc tự chọn/điền các đề xuất.
Cho phép tự nhận diện và lưu thông tin có căn cứ khi bấm tạo tài liệu/thêm phiên bản.
Đây là thay đổi có phạm vi so với việc chọn từng đề xuất ở Context879/893: chỉ bỏ
xác nhận từng trường khi đăng ký, không bỏ quyền, thao tác đăng ký, review gate hay
duyệt/phát hành. Không thay dữ liệu, cấu hình, dịch vụ hoặc bản xuất bản hiện tại.

## Nguyên nhân và cách xử lý

Bộ đề xuất cũ kiểm chuỗi có xuất hiện nhưng chưa đủ kiểm vai trò: “mùa tuyển sinh
2026” có thể bị gán thành ngành hoặc đợt. Cập nhật quy tắc/prompt supplement v2:
program cần nguồn gọi rõ ngành/chương trình, intake cần đợt/kỳ, năm tuyển sinh là
năm dữ liệu. Không suy từ tên tệp, thời hạn nộp hồ sơ hay ngày ban hành.

- Nhận diện từ nguồn đã ghim, tái kiểm cả đề xuất AI của lượt cũ. Không cần biên
  soạn hoặc tải lại tệp để xem trước thông tin của lượt completed chưa đăng ký.
- Nhãn/giá trị tường minh khác lưu trong attributes JSON; giữ số hiệu có số 0 đầu.
  Thông tin cục bộ không lan sang các đoạn/hàng/ô khác. Xung đột/không rõ giữ unknown.
- GET bản xem trước có quyền, rules_version và hash gắn bundle. POST tính lại,
  từ chối hash cũ trước khi ghi. Lưu provenance source_verified, không giả là đã
  được con người xác nhận, không sửa bản OCR/draft và không gọi thêm LLM.
- API cũ vẫn giữ hash idempotency và thao tác khai báo/chọn thủ công riêng; không
  trộn thủ công với hash tự nhận diện. Trạng thái phiên bản mới vẫn là draft.
- Giao diện bỏ checkbox và trình nhập metadata trong đăng ký, chỉ có Thông tin
  tài liệu và tóm tắt có thể mở xem. Rỗng vẫn đăng ký được; lỗi đọc thì chặn gửi,
  nút Tải lại chỉ đọc bản xem trước. Query ghim phiên đăng nhập, kho và run.

## File chính

Backend: compilation/supplement.py, segments.py; publication/automatic_metadata.py,
service.py, schemas.py, router.py và mô tả metadata.py.
Frontend: register-document-dialog.tsx, automatic-document-information.tsx,
publication-types/requests/queries.ts, compilation-detail-page.tsx.
Hợp đồng: backendV1/docs/compiled-publication.md, quy trình22/33.

## Kiểm chứng

- PASS: harness DB cô lập với unit/integration automatic_metadata896 và
  compiler_supplement879: 15 passed, exit0. Qua HTTP thật: chặn người ngoài,
  hash cũ không tạo dữ liệu, lưu đúng preview, replay, giữ draft/source nguyên trạng.
  Provider giả loopback, không gọi model thật.
- PASS: scoped Ruff; scoped Biome7 file, build kèm TypeScript.
- PASS: Vitest automatic-metadata896, dynamic-metadata880, compilation-tabs849:
  13 passed. Kiểm tạo một lần, không checkbox, không có thông tin vẫn tạo được,
  lỗi preview không ghi, tải lại chỉ GET, cache tách phiên/run.
- PASS: Chromium390/1280px sáng/tối; đã mở tóm tắt, không tràn ngang, nút tạo thấy
  được và bật sau khi tải. Đã xem ảnh390px. Fixture cô lập3096 đã dừng/gỡ, giữ ảnh.
- FAIL toàn frontend: 853 passed/10 failed, exit1. Exact10IDs trùng baseline894:
  OCR806(6), replacement678(3), v1-publication(1); không sửa assertion ngoài phạm vi.
- FAIL/INCOMPLETE toàn backend: collected1506; các nhóm1/2/4 đạt996 pass và3 fail,
  nhóm3 đạt5 pass rồi Windows access violation (0xC0000005) tại
  test_conversations649 courtesy; 502 ca của nhóm này chưa có kết quả xác minh.
  Tổng quan sát1001 pass/3 fail và502 chưa hoàn tất; exit1. Các DB test đã được
  harness dọn, legacy sentinel giữ nguyên. Ba lỗi ngoài phần sửa:
  - test_table_grounding_770.py::test_ingestion_quality_and_dependencies_are_derived_not_source_rewrites
    (baseline: kỳ vọng recipe cũ/v4 trong khi hiện hành/v5).
  - test_rag_modelops_budgets_767.py::test_window_zero_records_bounded_bytes_and_keeps_whole_evidence
    (baseline: fixture actor/db không phù hợp guard hiện hành).
  - test_readiness_666.py::test_readiness_reports_missing_configuration_and_does_not_claim_live_inference
    (kỳ vọng production_auth_configured=false, nhận true; chưa sửa fixture/cấu hình).
  Ca courtesy chạy chẩn đoán DB cô lập riêng:1 pass, exit0; không dùng để đổi kết
  quả full thành PASS, chưa kết luận nguyên nhân access violation. Không tự sửa
  runtime ngoài nhiệm vụ. Full kéo dài1204.55s; không chạy model thật.
- NOT RUN: live LLM mới hoặc benchmark RAG thật. Không tự cập nhật/reindex DB app,
  restart make dev, deploy, commit hay push.

Lệnh từ root: backendV1/.venv/Scripts/python.exe -X utf8
backendV1/scripts/run_isolated_tests.py với4file test nói trên; full gate dùng
script tạm tmp/check-896-backend.py chia tập test không trùng qua cùng harness.
Cwd frontendV1: npm exec -- vitest run <3file>; npm exec -- vitest run;
npm exec -- biome check <7file>; npm run build. Artefact cục bộ nằm tmp/check896*.

## Sử dụng

Khởi động lại make dev để API nhận endpoint mới; không clear dữ liệu. Mở lại
Đăng ký thành tài liệu biên soạn, xem tóm tắt nếu muốn rồi bấm Tạo tài liệu.
Bản đã đăng ký/xuất bản không bị viết lại; quyết định duyệt/phát hành giữ nguyên.
