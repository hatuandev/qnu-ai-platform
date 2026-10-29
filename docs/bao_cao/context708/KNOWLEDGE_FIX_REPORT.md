# Context708 — Sửa chức năng quản lý kho tri thức V1

Ngày: 2026-10-29. Người dùng báo upload được nhưng thiếu nút xóa, yêu cầu kiểm tra và sửa các chức năng trong kho tri thức. Đối chiếu ảnh và trang local của Phòng Công tác sinh viên; giữ nguyên hai tài liệu người dùng.

## Kết quả và phạm vi

| Vấn đề xác nhận | Hành vi sau sửa |
|---|---|
| Menu tài liệu thiếu xóa/lưu trữ, chế độ bảng chỉ có hiệu đính | Dùng chung SourceActions ở thẻ và bảng: chi tiết, tải xuống, OCR, đổi tên, di chuyển, lưu trữ và xóa theo quyền |
| Thiếu tải xuống ở danh sách | Tra revision_no hiện tại ra revision ID thật, tải đúng bản gốc; thiếu revision thì báo lỗi, không lấy số phiên bản làm ID |
| Menu vòng đời kho lồng trong dropdown khác | Đưa control vòng đời ra ngoài dropdown trên danh sách và chi tiết, tránh đóng/unmount dialog khi chọn thao tác |
| Ba chặng 3–5 chưa có thao tác | Nối nút tới các trang biên soạn, tài liệu xuất bản và chỉ mục/tìm kiếm hiện có; giữ màn chi tiết và review gate riêng |
| Thanh chặng không thao tác bằng phím | Dùng Button thay div role=button không xử lý Enter/Space |
| Lỗi danh sách/thư mục/revision bị hiển thị thành trống hoặc không mở dialog | ErrorState/thông báo có thử lại; quick OCR hiện loading/error khi chưa đọc được revision |
| OCR chỉ lấy 100 nguồn, deep link nguồn ngoài trang không tìm được | Phân trang OCR, đọc nguồn được chọn bằng endpoint theo ID; đổi nguồn remount studio, quay lại xóa đúng lựa chọn |
| Trạng thái danh sách OCR không cập nhật dù chi tiết đã kết thúc | Poll danh sách khi có queued/running; dừng khi tất cả ở trạng thái cuối |
| Lỗi OCR không hiện rõ ngoài tab kỹ thuật | Banner nguyên nhân và mã lỗi theo run đang chọn, không gán thành công giả |
| Worker mất quyền admin local | Tái tạo danh tính từ quyền dev gate hiện tại ở server cho OCR/Compiler/index/auto-review; actor khác vẫn kiểm membership hiện tại |
| Xóa thư mục che cây nhưng không xử lý tài liệu như mô tả | Chỉ xóa thư mục rỗng; server trả409 folder_not_empty nếu còn tài liệu/thư mục con; UI chặn khi impact lỗi/không có/không rỗng |
| Di chuyển khi chưa tải được thư mục đích | Chặn submit khi query chưa thành công, hiện lỗi/thử lại; không coi null và undefined là hai thư mục gốc khác nhau |
| Đếm gốc kho sai khi có thư mục | Tính từ tổng nguồn trừ nguồn trực tiếp trong các thư mục |
| KPI khẳng định hệ thống/OCR sẵn sàng dù chưa cấu hình | Bỏ hai KPI không có nguồn health; số tài liệu trên danh sách ghi rõ chỉ trong các kho trên trang |
| Header tràn ngang trên điện thoại | Cho nhóm nút xuống hàng, tiêu đề/chặng co giãn; kiểm viewport390×844 sáng/tối |

Tìm kiếm nhanh chỉ lọc trang đã tải, nhãn ghi rõ “trong trang này”. Không triển khai tìm kiếm toàn bộ tài liệu phía server trong phiên này.

## Quyền và bảo toàn dữ liệu

- Admin nền tảng/admin workspace có xóa tài liệu; editor được sửa/di chuyển/lưu trữ nhưng không xóa; member chỉ có thao tác đọc. Server vẫn là nơi kiểm quyền.
- Xóa tài liệu dùng luồng lifecycle sẵn có: lý do → xem tác động → xác nhận → biên nhận → thùng rác/khôi phục. Không xóa vật lý bản gốc, OCR hoặc lịch sử.
- Xóa thư mục chỉ rỗng, kiểm lại trong transaction có khóa workspace/folder. Không quảng cáo xóa đệ quy khi chưa có contract an toàn cho nguồn/xuất bản/index.
- Quyền worker không lấy từ payload queue hoặc giữ snapshot role. Chỉ danh tính admin local cố định được dựng lại khi dev gate còn bật, ngoài production, SSO tắt và cấu hình mật khẩu dev còn tồn tại. Tắt gate/production/SSO/identity khác không được kế thừa quyền này. Với SSO, tác vụ nền vẫn cần membership hợp lệ; chưa thêm dịch vụ tra quyền SSO nền.
- Không thêm membership, không đổi grants/defaults/model/quota/secret/.env, không migrate/reindex dữ liệu người dùng.

## Kiểm chứng tự động

- Trước sửa, hai integration về xóa thư mục đều FAIL đúng hành vi200 thay409. Sau sửa:2PASS.
- Regression quyền worker trước sửa: admin local1FAIL workspace_not_found; trường hợp tắt gate1PASS. Sau sửa: cả2PASS.
- Integration cuối5PASS/exit0: thêm ca thu hồi membership sau enqueue phải chặn trước provider. DB qnu_v1_test_541b17685f40466e đã dọn; legacy sentinel giữ nguyên. Batch trước4PASS tại DB qnu_v1_test_e24ae1805ab84703 cũng đã dọn.
- Unit quyền nền7ca + folder5ca:12PASS/exit0.
- FE regression đầu9FAIL sau khi bổ sung polyfill môi trường test, xác nhận menu/ba chặng/error/impact. Batch13ca sau sửaPASS.
- FE focused cuối23PASS/5file; full cuối439PASS/49file/exit0 (`npm test -- --maxWorkers=2`). Full trước435PASS; bổ sung banner lỗi và polling có regression riêng rồi full lại439PASS.
- `npm run build`: PASS/exit0, Vite + TypeScript; còn cảnh báo bundle lớn. Biome13file và Ruff9file đúng phạm vi: PASS. `npm run lint -- --max-diagnostics=100`: FAIL/exit1,29errors/7warnings/1info ngoài13file sửa; không tự sửa lan lỗi format/a11y/import có sẵn ở knowledge, modelops, navigation và các phần khác. Log đầy đủ trong artifact.
- Backend full (cwd backendV1): `uv run --frozen --env-file ../.env --extra dev python scripts/test_database.py tests -q --durations=10`, có Redis test DB15 riêng: **FAIL / không có exit bình thường**. Log ghi đủ806/806 dấu kết quả (804PASS/2FAIL/0SKIP), sau đó kẹt teardown của TestClient trên Windows Proactor ở `windows_events.py::_poll`/`close`. Đây là số đếm dấu tiến độ, không phải summary Pytest đã kết thúc. Lưu stack/log và progress receipt trước khi dừng đúng tiến trình pytest; harness dọn DB `qnu_v1_test_f3fe34d7f46541aa`, giữ legacy sentinel, ghi exit4294967295. Không tuyên bố full PASS.
- Hai ID FAIL trùng lượt706:
  - `tests/integration/test_knowledge_regressions_639.py::test_downgrade_cannot_mark_success_and_block_next_upgrade`.
  - `tests/migrations/test_workspace_model_schema.py::test_migrations_match_models_and_exclude_legacy`.
  Cả hai kỳ vọng `0005_provider_connections` trong khi schema hiện tại là `0006_kb_folders`; không sửa assertion ngoài phạm vi để che lỗi.
- Recovery có `QNU_TEST_WINDOWS_SELECTOR_LOOP=true` (opt-in fixture đã có trong repo, chỉ cho test), chạy5integration mới +12unit trọng tâm +2ID lỗi: **17PASS / 2FAIL / exit1** trong15.87giây, thoát và teardown bình thường. Tái hiện đúng hai assertion revision cũ; DB `qnu_v1_test_489a95c372304a79` đã dọn, sentinel giữ, Redis DB15 còn0key. Không đổi event loop của app hoặc production.
- Lượt full thu thập806case trước khi thêm ca thu hồi membership cuối; ca bổ sung đã chạy trong focused5PASS và recovery17PASS. Mã ứng dụng ổn định trước lượt full; không sửa app để làm test xanh.

Lượt full backend đầu dừng khi phát hiện thêm lỗi quyền OCR thật, không ghi PASS: qnu_v1_test_0fa266e3609041a6, exit4294967295; harness đã dọn DB và giữ sentinel. Lượt cuối bắt đầu sau batch quyền nền ổn định, có TEST_REDIS_URL riêng (DB15 loopback được kiểm trống, khác Redis ứng dụng), không sửa env phục vụ.

Artifact local: storage/artifacts/knowledge-fix-708/; receipt DB trong backendV1/storage/context636/. Dữ liệu kiểm thử tổng hợp, provider loopback trong regression; không dùng corpus nội bộ làm fixture hay log secret.

## Kiểm tra giao diện và runtime

Đã tạo riêng collection col_265f31085d60 “Kiểm thử kho tri thức708”, folder “Thư mục kiểm thử708”, source src_eb0eaef42c26. PDF tổng hợp1trang612byte, nội dung “Synthetic knowledge explorer test 708”.

Đã thử thực tế: tạo kho, upload, tải xuống (SHA256 khớp toàn bộ612byte), đổi tên, tạo thư mục, di chuyển vào thư mục, xem impact và chặn xóa thư mục còn tài liệu, xóa source có biên nhận lca_dd61ef030e42, khôi phục source lca_43201f590995. Sau reload, nguồn vẫn ở đúng thư mục. Chưa xóa hai tài liệu gốc của người dùng.

Thử yêu cầu OCR qua API/worker thật trên tệp tổng hợp: lượt đầu ocr_142576868a1b thất bại workspace_not_found, đã tái hiện và sửa quyền. Lượt sau qua bước quyền nhưng thất bại model_not_configured vì workspace chưa được cấu hình model OCR. UI hiển thị nguyên nhân đúng; không tự chọn/cấp model hoặc đổi quota. Người dùng đã chọn “Giữ cấu hình hiện tại, hoàn tất phần sửa chức năng”. Chốt không cấp thêm model, không đổi OCR mặc định hoặc hạn mức; đề xuất nemotron-parse/100.000token/tháng không được áp dụng. Phần sửa chức năng đã hoàn tất; không chạy thêm OCR thật theo đề xuất này. Vì vậy chưa xác nhận pipeline OCR → Compiler → xuất bản → index với provider thật. Các trang chức năng đã nối và kiểm qua UI; regression dùng provider tổng hợp không chứng minh chất lượng AI thật.

Các phiên V1 không còn lắng nghe ở đầu task; kiểm dependency5mụcđạt rồi khởi động phiên riêng để thử. Chỉ dừng/restart đúng cây process do task tạo để nạp bản sửa backend/worker. Runtime đã nạp helper quyền nền mới, API/worker/FE chạy. Health live200/ready200/FE200; đối chiếu hash17file app không đổi sau kiểm chứng cuối.

Ảnh menu tài liệu, bảo vệ thư mục, thùng rác/khôi phục, mobile sáng/tối ở artifact. Bố cục mobile sau sửa: viewport390, documentWidth375, không tràn ngang toàn trang.

Kho kiểm thử đã lưu trữ có thể khôi phục (lca_324a45007723), không lẫn với kho đang sử dụng. Giữ tệp/receipt làm bằng chứng; không purge dữ liệu. Đã trở lại kho gốc của người dùng trên UI.

## Tệp và giới hạn

Frontend: knowledge detail, source actions mới, collections panel, stage OCR, folder delete/move, OCR container/query, hai route knowledge có key theo workspace/kho và regression708. Backend: folder guard; identity dev admin factory/background actor mới; sử dụng helper ở bốn executor knowledge; tests708. Giữ diff có sẵn của các phiên trước (knowledge layout, navigation, startup/storage, provider).

Không Git commit/push/deploy. Không thay parser/prompt/layout OCR, dữ liệu nguồn, publication policy hay fallback/model routing.

Hướng dẫn thao tác đã cập nhật ở [quy trình34](../../quy_trinh/34_frontend_vong_doi_thay_the_va_van_hanh.md#thao-tác-trong-kho-tri-thức).
