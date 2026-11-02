# Phiên 819 — Sửa và kiểm chứng quy trình ngược V1

## Phạm vi

Theo yêu cầu tiếp tục xử lý sau review 818: sửa hai P2 (trạng thái chỉ mục sau
thay bản và cache chat sau quyết định xuất bản), tách trần thời gian tác vụ model,
hoàn tất phép thử thay tài liệu. Giữ các thay đổi chưa commit 815–818 và lịch sử
lượt compiler uncertain 811. Không tích hợp MinerU, không push và không restart
API/worker chính.

Áp dụng các skill clean-code, backend-architect và frontend-architect. Workspace
trong `backendV1` vẫn là biên giới quyền; không bỏ kiểm tra membership cho worker.

## Thay đổi

- API `compiled-documents/{id}/index-readiness` kiểm tra quyền và manifest hiện
  hành; đối chiếu đúng document/version/state/hash/quyết định xuất bản. Không suy
  readiness bằng thứ tự timestamp và không gọi embedding để kiểm tra.
- Frontend đọc readiness từ API, hiển thị loading/lỗi trung thực và không đề nghị
  lập chỉ mục lại khi chưa kiểm tra xong. Trường hợp thay bản tạo candidate trước
  quyết định xuất bản vẫn được xác nhận ready nếu binding khớp.
- Sau quyết định publish/withdraw, làm mới cache index và chat trong session và
  workspace tương ứng. Backend vẫn chịu trách nhiệm che kết quả có nguồn đã hết
  hiệu lực; cache frontend không phải hàng rào quyền.
- Bốn tác vụ OCR/compiler/AI review/index dùng
  `WORKER_MODEL_JOB_TIMEOUT_SECONDS=86400` (24 giờ mặc định), cấu hình được.
  Tác vụ bảo trì giữ 1800 giây. Đây không phải chạy vô hạn; độc lập với provider
  wait, lease, quyền hủy và quy tắc không gửi lại lời gọi uncertain. Đã cập nhật
  `.env.example` và tài liệu runtime; không sửa `.env` đang chạy.

## Kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| Frontend regression 5 suites, gồm 9 ca mới | PASS: 35 tests |
| Frontend toàn phần `npx vitest run` | PASS: 700 tests / 79 suites, exit 0 |
| `npm run build` (gồm TypeScript) | PASS, exit 0 |
| Biome 7 file liên quan | PASS, exit 0 |
| Ruff 8 file Python liên quan | PASS, exit 0 |
| `git diff --check` | PASS tại thời điểm kiểm tra |
| Backend toàn phần, database riêng | CHƯA HOÀN TẤT: ngắt ở 30%; 395 PASS / 3 FAIL đã ghi nhận |

Lần kiểm tra backend đầu tiên (unit + 4 nhóm integration) có 706 PASS, 2 FAIL,
24 ERROR, exit 1. Các ERROR do thư mục tạm Windows không truy cập được. Không sửa
quyền hoặc xóa thư mục tạm cá nhân; lần toàn phần dùng `--basetemp` riêng trong
workspace. Giữ nguyên log lần đầu, không đổi assertion để làm xanh.

Hai bài FAIL đã chạy riêng trên worktree sạch cùng HEAD trước thay đổi
`81e5f1a250ffa041682edcf3d141def561a046c9`: cả hai vẫn FAIL (exit 1).

- `tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`
- `tests/integration/test_lifecycle_659.py::test_preview_is_bound_to_actor_and_state`

Chúng liên quan fixture purge thiếu membership của background actor. Không nới
guard để làm test xanh. Database của phép đối chiếu đã được dọn, remaining=0.

## Lượt backend toàn phần bị ngắt

Lượt full đầu dừng khi phát hiện launcher chưa đặt namespace cache test và
`TEST_REDIS_URL`. Giữ log `tmp/reverse819-full-pytest.log`; database của lượt này
đã được dọn (remaining=0). Đây là lỗi thiết lập kiểm thử, không coi là lỗi ứng dụng.
Lượt cuối dùng namespace `qnu:test:`, queue riêng, Redis E2E loopback, basetemp
riêng và chặn kết nối ngoài loopback. Bài kiểm tra Redis trước đó lỗi đã PASS.

Lượt cuối bị ngắt ở khoảng 30%; tiến trình không còn chạy. Log đã ghi 395 PASS,
3 FAIL, chưa có tổng kết hay exit code Pytest cuối. Ba ca FAIL đã quan sát:

- `tests/integration/test_compiler_source_versions_654.py::test_exact_saved_text_is_pinned_despite_newer_saved_text`
- `tests/integration/test_knowledge_regressions_639.py::test_downgrade_cannot_mark_success_and_block_next_upgrade`
- `tests/integration/test_lifecycle_659.py::test_preview_is_bound_to_actor_and_state`

Hai ca 654/659 cũng FAIL khi chạy riêng trên HEAD sạch; 654 báo KeyError do
assert trường `text_version` không có trong model message. Ca 639 chưa đối chiếu
baseline, chưa có traceback cuối của lượt full; không kết luận đã tìm xong nguyên
nhân. Các ca readiness819 và replacement runtime659 trong lượt này đều PASS.
Không gọi toàn bộ backend PASS; phần test chưa chạy là NOT RUN trong lượt cuối.

Database riêng còn cần đối soát cleanup:
`qnu_v1_test_reverse819final_1793613912652669300`. Khi kiểm tra, container Postgres
E2E đã dừng nên không xác nhận/drop được; không tự bật lại hạ tầng. Các database
của lần scoped, baseline và full đầu đã xác nhận remaining=0. Receipt kết thúc:
`tmp/reverse819/interrupted-final-receipt.json`.

## Nghiệm thu runtime với model thật

Artifact `tmp/reverse819/live/state.json`: status `passed`; 60 bản ghi kiểm tra,
47 tên kiểm tra khác nhau, không có check thất bại. Dùng collection thử riêng
`col_5af51f8ced87` trong phiên E2E 93faa11f0caf. PDF và DOCX là fixture kỹ thuật,
không phải dữ liệu tuyển sinh chính thức.

1. PDF cũ → bóc tách → compiler → phê duyệt nhanh có ghi nhận → index → chat trả
   số liệu cũ 5500.
2. DOCX mới → bóc tách → người dùng lưu sửa thành phiên bản mới → compiler ghim
   đúng bản sửa → phê duyệt; bản cũ tiếp tục phục vụ trong lúc chuẩn bị.
3. Hủy candidate thay thế đầu tiên trước activation: bản cũ vẫn phục vụ.
4. Tạo ý định thay thế tiếp theo, hoàn tất index rồi chuyển bản nguồn/phát hành/
   chỉ mục nguyên tử. Readiness khớp binding; search chỉ lấy bản mới; chat trả 5600.
5. File gốc và hai lịch sử phiên bản được giữ, provider grants không đổi.
6. Lịch sử chat dùng bản cũ được trả `source_status=unavailable`, `result=null`.
7. Thu hồi bản mới: readiness unavailable, search loại tài liệu, chat có nguồn
   này bị đánh dấu unavailable. Archive rồi restore không tự xuất bản lại.

Hai compiler và hai lượt trả lời chat đều dùng model thật qua ModelOps, một lần
gửi cho mỗi lượt. Compiler cũ 12,78s, mới 13,37s; index cũ 1,27s, mới 2,99s.
Không gửi lại model để làm xanh kết quả.

Lần chạy đầu dừng ở preview replacement do platform actor không có membership
admin thực cho background job. Đã bổ sung membership qua API có quyền, tiếp tục
cùng receipt/state và không gửi lại model. Membership tạm đã thu hồi khi xong;
audit và lỗi lần đầu còn trong artifact. Đây là sửa điều kiện thử, không bỏ guard.

Docker E2E ban đầu đã dừng; chỉ khởi động năm container hạ tầng của đúng phiên
93faa11f0caf. Nghiệm thu dùng ASGI runtime riêng và queue riêng; không restart
dịch vụ chính hoặc thay cấu hình model chung. Không dọn corpus hiện có.

## Giới hạn và bước sau

- AI review NOT RUN: sử dụng nhánh duyệt nhanh đã được phép, có quyết định gắn
  đúng phiên bản/hash; không biến bỏ review thành mặc định toàn hệ thống.
- Fixture native: chưa nghiệm thu tích hợp MinerU hay OCR scan trong phép thử này.
- API/worker chính phải nhận mã mới khi người dùng chủ động khởi động lại lúc
  không còn job đang chạy. Worker hiện tại chưa được restart.
- Toàn backend chưa được gọi PASS nếu còn bất kỳ test lỗi nền nào.

Chi tiết: `tmp/reverse819/REPORT.md`; log backend lần đầu và toàn phần,
baseline và frontend giữ ở `tmp/reverse819*`.

## Theo dõi sau restart

Phiên820 đã xác nhận dọn database còn sót và chạy đủ backend; xem [kết quả820](2026-11-02_phien_820_chay_lai_backend_sau_restart.md). Giữ nguyên kết quả ngắt tại thời điểm819 ở trên.
