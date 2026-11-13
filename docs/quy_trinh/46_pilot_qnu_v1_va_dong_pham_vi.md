# 46 — Pilot QNU V1 và đóng phạm vi bản đầu

> Tài liệu sống (V1). Trạng thái 2026-11-08: bộ công cụ pilot đã soạn; môi trường dev đã backup và áp migration `0015`–`0017` (`alembic current` = `0017_answer_review`) với API/worker/giao diện chạy được; **phiên pilot thực tế NOT RUN** vì chưa chọn đơn vị/người tham gia, workspace chưa có thành viên/trợ lý/tài liệu xuất bản. Không dùng tài liệu này để tuyên bố pilot đã đạt.

Mục tiêu P7: để người nghiệp vụ tự hoàn tất luồng thêm tài liệu → yêu cầu sửa → duyệt → xuất bản → hỏi đáp → cập nhật bản mới; ghi nhận thời gian, điểm vướng và lỗi thật; chỉ sửa trở ngại UX trong phạm vi trước khi mở rộng tính năng.

## 1. Điều kiện vào pilot

- P1–P6 đã bàn giao trong working tree; chạy gate tự động ở §7 trên đúng mã sẽ dùng cho pilot.
- Môi trường **dev/staging được phép**, không phải production. DB đã áp migration theo thứ tự `0015_preparation_intent` → `0016_review_submission` → `0017_answer_review` (ngày 2026-11-08 trên DB phát triển, sau backup `storage/backups/qnu_pre_pilot_20261108_170941.dump`); kiểm bằng `alembic current` trên bản sao.
- Có backup PostgreSQL/object store/Qdrant và bản lưu khóa ModelOps trước khi migrate; xem [triển khai Dokploy](../trien_khai/02_quy_trinh_trien_khai_dokploy.md) và [an toàn dữ liệu](../trien_khai/03_an_toan_du_lieu_va_van_hanh.md).
- Workspace pilot riêng, collection riêng, provider/model được phép dùng và corpus đã được đơn vị đồng ý. Không dùng khóa LLM trong `.env` để vượt ModelOps.
- Có ít nhất một người điều phối (không hướng dẫn thay người dùng) và một người ghi biên bản. Verifier đọc diff/chạy lại gate, không chỉ nhận lời người triển khai.

## 2. P7.1 — Chọn đơn vị và người tham gia

Đề xuất 3–5 người, **không giả định đã được chọn**:

| Vai trò | Số người đề xuất | Việc chính trong pilot |
|---|---:|---|
| Editor | 1–2 | Thêm nguồn, chuẩn bị nội dung, biên soạn, gửi duyệt |
| Reviewer | 1 | Yêu cầu sửa, duyệt nội dung |
| Admin đơn vị | 1 | Xuất bản, quyền thành viên, phạm vi trợ lý |
| Người tra cứu | 1 | Đặt câu hỏi, đọc/mở dẫn chứng, gắn nhãn kiểm thử nếu được cấp |

Tiêu chí đơn vị: có tài liệu thật được phép dùng cho thử nghiệm, có người chịu trách nhiệm duyệt, chấp nhận ghi biên bản ẩn danh. Không đưa PII, tài liệu mật, prompt riêng hoặc Base64 OCR vào Git.

Ghi nhận tối thiểu (ẩn danh người, dùng mã):

| Mã người | Vai trò | Workspace | Đồng ý ghi biên bản | Ngày |
|---|---|---|---|---|
| P-01 | editor | WS-PILOT | có | |
| P-02 | reviewer | WS-PILOT | có | |

Không suy vai trò từ JWT, tên tài khoản hay AI; admin gán membership qua màn hình Thành viên và kiểm lại quyền thực tế.

### 2.1. Đơn vị dev đã seed (chưa phải người thật)

Ngày 2026-11-08, để kiểm thử vai trò ngay trên môi trường dev, đã seed idempotent workspace `shl` — “Trung tâm Số & Học liệu” (`ws_31a7278f42e7`) với 4 membership đang hoạt động: `act_dev_shl_admin` (admin), `act_dev_shl_editor` (editor), `act_dev_shl_reviewer` (reviewer), `act_dev_shl_reader` (member). Lệnh: `uv run --frozen --env-file ../.env python -m scripts.seed_shl_pilot`; chạy lại không tạo thêm, không đổi vai trò/trạng thái. Khóa dev nằm ở `backendV1/.local/shl-pilot-accounts.json` (đã Git ignore), không ghi vào log/tài liệu.

Đã kiểm qua HTTP in-process (TestClient trên DB dev, không ghi dữ liệu): 4/4 tài khoản đăng nhập 200, `/auth/me` đúng `actor_id`, workspace hiển thị và chi tiết 200, danh sách 4 thành viên đúng vai trò; PATCH thành viên không tồn tại trả 403 cho editor/reviewer/reader và 404 cho admin đơn vị cùng platform admin. Ngày 2026-11-08, sau khi người dùng cho phép, API dev `127.0.0.1:8002` đã được khởi động lại bằng đúng lệnh cũ (từ thư mục gốc repo): `uv run --project ./backendV1 --frozen --extra dev uvicorn qnu.main:app --host 127.0.0.1 --port 8002`; log ghi tại `backendV1/storage/context636/dev-api.out.log` và `.err.log`. Sau restart: `/health` 200, kiểm HTTP thật 21/21 đạt (4/4 khóa seed đăng nhập, workspace/members 200, biên quyền PATCH 403/404, platform admin 200). Kiểm trình duyệt 1280px bằng Playwright với dev-key form: 4/4 vai trò đăng nhập được, trang Thành viên hiển thị đủ 4 dòng cho mọi vai trò; admin có nút “Thêm thành viên” bật và 4 ô chọn vai trò, các vai trò khác chỉ đọc; điều hướng theo vai trò đúng (admin/editor thấy Cần xử lý + Chuẩn bị nội dung + Xuất bản; reviewer không thấy Chuẩn bị nội dung; reader chỉ thấy nhóm tra cứu); 0 lỗi console — tổng 32/32 kiểm tra đạt.

Đây là tài khoản dev để kiểm thử, **không phải người tham gia pilot**; T1–T6 với người thật vẫn NOT RUN cho tới khi có điều phối viên, thư ký ghi biên bản, trợ lý và kho tài liệu đã xuất bản.

## 3. P7.2 — Kịch bản tác vụ và đo thời gian

Người dùng tự thao tác trên UI. Điều phối viên chỉ can thiệp khi người dùng bị chặn hoặc hỏi; mỗi lần can thiệp đếm là **một lần cần dev hỗ trợ**. Không thao tác hộ.

| Mã | Tác vụ | Đường đi gợi ý (nhãn UI hiện hành) | Bằng chứng cần lưu |
|---|---|---|---|
| T1 | Thêm tài liệu | Kho tri thức → chọn kho → Đọc nội dung → tải tệp/đăng ký nguồn → Chuẩn bị nội dung → chờ trạng thái sẵn sàng | mã nguồn, trạng thái cuối, thời điểm |
| T2 | Gửi duyệt và yêu cầu sửa | Phiên bản → Gửi duyệt → reviewer mở Cần xử lý → Yêu cầu sửa kèm lý do | mã phiên bản, lý do (không chứa dữ liệu nhạy cảm) |
| T3 | Duyệt | Reviewer/admin mở phiên bản → duyệt | trạng thái trước/sau |
| T4 | Xuất bản và đồng bộ | Xuất bản → publish → theo dõi Đồng bộ cho trợ lý đến `ready` | bản xuất bản, trạng thái sync |
| T5 | Hỏi đáp có dẫn chứng | Trợ lý AI → Trò chuyện; mở dẫn chứng; nếu có quyền, dùng Kiểm thử và gắn nhãn | câu hỏi, dẫn chứng mở được, nhãn |
| T6 | Cập nhật bản mới | Tải revision mới → Chuẩn bị nội dung → thay bản có preview → publish/switch → xác nhận bản đang phục vụ | bản cũ/mới, trạng thái phục vụ |

Bảng đo (một dòng mỗi lần thực hiện):

| Mã | Người | Bắt đầu | Kết thúc | Thời gian thao tác | Thời gian chờ server | Số lần dev hỗ trợ | Hoàn tất không? | Vướng mắc |
|---|---|---|---:|---:|---:|---:|---|---|
| T1 | P-01 | | | | | | có/không | |

Quy ước: thời gian thao tác = từ lúc người dùng bắt đầu đến khi gửi thao tác cuối; thời gian chờ = thời gian chờ job/sync/provider, ghi riêng. Không gộp latency quan sát với ước lượng. Mục tiêu đề xuất (chưa phải số đo): ≥80% người hoàn tất tác vụ thường gặp không cần dev chỉ đường.

## 4. P7.3 — Ma trận tình huống không chỉ golden path

Chạy trên workspace/kho thử, dùng tài khoản thật của pilot. Mỗi tình huống ghi mã người, thời điểm, mã lỗi/correlation id hiển thị (nếu có) và ảnh chụp màn hình không chứa dữ liệu nhạy cảm.

| # | Tình huống | Cách tạo an toàn | Hành vi trung thực mong đợi | Dấu hiệu FAIL cứng |
|---|---|---|---|---|
| 1 | Thiếu quyền workspace | Người ngoài workspace mở deep link | Từ chối 403/thông báo không có quyền; không lộ tên tài liệu | Hiện nội dung hoặc danh sách tài nguyên |
| 2 | Thiếu quyền gắn nhãn | Editor/reviewer/reader thử gắn nhãn answer review | Chỉ admin/editor/reviewer thấy nút; server từ chối nếu gọi thẳng | Người không quyền gắn được nhãn |
| 3 | Thiếu cấu hình model | Workspace chưa có provider/model được phép | Lỗi cấu hình/hạ tầng riêng; không giả “không có dữ liệu” | Trả câu trả lời ngoài kho hoặc im lặng |
| 4 | Kho rỗng/chưa xuất bản | Trợ lý trỏ collection không có tài liệu đã xuất bản | Readiness `empty`; Kiểm thử từ chối chạy; chat nói thiếu nguồn hợp lệ | Báo ready hoặc trả lời bằng kiến thức ngoài |
| 5 | Đã xuất bản nhưng chưa index | Publish rồi xem trạng thái trước khi sync xong | Readiness `syncing/not_indexed`; không báo ready | Badge ready khi chưa có binding |
| 6 | Sync lỗi | Dùng provider embedding lỗi đã kiểm soát | Readiness `failed` kèm lý do; retry chỉ người có quyền | Tự retry hàng loạt hoặc báo thành công giả |
| 7 | Nguồn mâu thuẫn | Hai tài liệu khác năm cùng chủ đề | Dẫn cả hai hoặc hỏi làm rõ; nhãn `wrong_year` dùng được | Tự chọn một năm không có căn cứ |
| 8 | Sync chưa xong khi đang xem | Mở tài liệu ngay sau publish | Chỉ hiện “đang phục vụ” khi server xác nhận `served_version` | Báo bản mới đang phục vụ khi chưa switch |
| 9 | Thu hồi trong lúc build | Withdraw rồi kiểm dẫn chứng cũ | Không kích hoạt nội dung cũ/mới sai; dẫn chứng cũ báo lý do | Trả nội dung withdrawn hoặc bản stale |
| 10 | Câu hỏi nối tiếp mơ hồ | Hỏi “còn năm 2025 thì sao?” không đủ chủ thể | Yêu cầu làm rõ, khôi phục câu hỏi; không phải lỗi hạ tầng | Báo lỗi model/kết nối hoặc đoán bừa |
| 11 | Provider lỗi giữa lượt | Ngắt provider trong môi trường thử | Lỗi hạ tầng riêng + “Hỏi lại câu này” tạo lượt mới; lượt cũ giữ trạng thái | Báo “không tìm thấy dữ liệu” |
| 12 | Draft/withdrawn lọt phục vụ | Hỏi đúng nội dung chỉ có trong bản nháp/đã thu hồi | Không xuất hiện trong câu trả lời/dẫn chứng | Bất kỳ nội dung draft/withdrawn nào lọt ra |

Bất biến cứng: **không tình huống nào vượt quyền, phục vụ draft/withdrawn hoặc báo ready sai**. Vi phạm bất kỳ mục nào là S1 — dừng pilot, lưu bằng chứng, không tiếp tục các tác vụ khác cho đến khi xử lý.

## 5. P7.4 — Phân loại và sửa trở ngại

| Mức | Định nghĩa | Hành động |
|---|---|---|
| S1 | Vượt quyền, lộ draft/withdrawn, báo ready sai, mất dữ liệu | Dừng pilot; sửa + regression trước khi chạy lại |
| S2 | Không hoàn tất được tác vụ thường gặp | Sửa trong phạm vi UX/lỗi; chạy lại gate |
| S3 | Ma sát nhãn/copy/flow, vẫn hoàn tất được | Gom thành một đợt sửa nhỏ sau pilot |
| S4 | Yêu cầu tính năng mới | Ghi backlog E1–E6 của kế hoạch 15, không làm trong pilot |

Mỗi lỗi ghi: mã, tác vụ, bước, hành vi mong đợi/thực tế, ảnh hưởng, mã lỗi/correlation id, quyết định. Không sửa ranking/chunking, không refactor toàn repo, không thêm dữ liệu giả để “cho qua”. Sau khi sửa S1/S2 phải chạy lại §7 và ghi receipt mới.

## 6. P7.5 — Nghiệm thu, giới hạn đã biết, rollout/rollback

### 6.1. Checklist nghiệm thu

| Tiêu chí | Trạng thái 2026-11-08 | Bằng chứng |
|---|---|---|
| P1–P6 có gate trong phạm vi bàn giao | đạt theo nhật ký 898–902 | log từng phiên |
| Không vượt quyền giữa workspace | gate tự động PASS | §7, test workspace |
| Không phục vụ draft/withdrawn | gate tự động PASS | §7, test publication/lifecycle/readiness |
| Không báo ready sai | gate tự động PASS | §7, test readiness P6 |
| ≥80% người hoàn tất không cần dev | **PENDING** — cần pilot thật | bảng §3 |
| Phân biệt chuẩn bị/chờ duyệt/đang đồng bộ/sẵn sàng | **PENDING** — cần quan sát người dùng | §3, §4 |
| So sánh chất lượng/latency cùng corpus/model/snapshot | **NOT RUN** | cần phiên đo riêng |

Chỉ điền PASS cho dòng có biên bản và bằng chứng thật. NOT RUN/PENDING không phải đạt.

### 6.2. Giới hạn đã biết tại thời điểm bàn giao

- DB phát triển đã ở `0017_answer_review` từ 2026-11-08 (backup trước migrate: `storage/backups/qnu_pre_pilot_20261108_170941.dump`, 217K, 382 mục). Đây là DB dev, không phải staging/production; pilot thật vẫn phải chạy trên môi trường được phép với backup riêng.
- Full backend suite chưa hoàn tất trong các phiên P4–P6; còn lỗi nền Redis751 đã biết, không tuyên bố toàn hệ thống PASS.
- Kiểm trình duyệt P1–P6 đã chạy 2026-11-08: 66 lượt tải (11 route × 390/768/1280 × sáng/tối) trên Vite dev, 0 lỗi console; phát hiện và đã sửa tràn ngang 390px ở thẻ nguồn/thanh “Dẫn xuất & phục vụ” và việc mất `stage=publication` khi mở link collection cũ (commit `f3f47284`), kiểm lại đạt. Đây là kiểm tự động kèm ảnh, không thay quan sát người dùng thật trong pilot.
- Nhãn answer review là đánh giá của người kiểm thử, không phải gold retrieval; benchmark vẫn ở cấu hình kỹ thuật.
- Chưa có sandbox thử bản nháp trước xuất bản (E6); không hứa “kiểm thử draft”.
- Chưa có notification bền vững (E1); reviewer theo dõi qua “Cần xử lý”, không dựa vào thông báo tự động.
- Feedback câu trả lời/assignments/onboarding (E2–E4) chưa có; ghi vào backlog.
- Pilot chỉ trên corpus/model/snapshot được phép; không dùng số liệu pilot để suy chất lượng production.

### 6.3. Rollout và rollback

Tham chiếu [triển khai Dokploy](../trien_khai/02_quy_trinh_trien_khai_dokploy.md), [an toàn dữ liệu](../trien_khai/03_an_toan_du_lieu_va_van_hanh.md), [sao lưu/khôi phục](../trien_khai/04_sao_luu_va_khoi_phuc_dot_1.md).

1. Trước pilot: sao lưu DB/object/Qdrant, lưu commit/tag image, chạy migration trên **bản sao** và `alembic current`.
2. Rollout pilot: deploy đúng môi trường staging đã được duyệt; không tự triển khai production chỉ vì test đạt.
3. Trong pilot: theo dõi lỗi S1; dừng ngay khi có vi phạm quyền/dữ liệu.
4. Rollback: giữ nguyên named volumes; không `down -v`, không prune volume, không reset DB. Rollback image không tự rollback schema; nếu migration đã đổi dữ liệu, dùng kế hoạch khôi phục đã kiểm trên bản sao.
5. Kết thúc: chốt biên bản nghiệm thu, known limitations và quyết định production tách riêng, có người phê duyệt.

## 7. Gate tự động trước và sau pilot

Từ `backendV1`, dùng harness DB cô lập (không chạy trên DB ứng dụng). Lệnh mẫu:

```bash
export DATABASE_URL="$(grep -m1 '^DATABASE_URL=' ../.env | cut -d= -f2-)"
uv run python scripts/run_isolated_tests.py \
  tests/integration/test_workspaces_modelops_api.py \
  tests/integration/test_workspace_model_boundaries.py \
  tests/integration/test_index_readiness_819.py \
  tests/integration/test_publication_index_sync_878.py \
  tests/integration/test_assistant_readiness_p6.py \
  tests/integration/test_answer_review_p6.py -q
```

Bản đồ bất biến → test:

| Bất biến | Test tiêu biểu |
|---|---|
| Tách quyền workspace, không leo thang qua body/header | `test_swapping_workspace_id_in_body_does_not_escalate`, `test_member_of_a_cannot_manage_b`, `test_revoked_membership_immediately_removes_workspace_and_model_access` |
| Draft/withdrawn không được phục vụ | `test_readiness_tracks_binding_and_withdrawal_without_embedding`, `test_withdrawal_while_building_keeps_newer_intent_and_never_activates_stale_content`, `test_retirement_preserves_citations_and_never_removes_active_or_recent_index` |
| Readiness trung thực | các test `test_collection_without_published_documents_is_empty`, `test_published_but_unindexed_is_not_ready`, `test_completed_index_reports_ready_and_served` |
| Answer review chỉ trên bản xuất bản, nhãn người | `test_review_requires_active_assistant_with_published_sources`, `test_review_runs_on_published_sources_and_stores_human_labels` |

Ghi receipt: tên DB thử, số test, `db_dropped`, `legacy_sentinel_preserved`, exit code, thời gian. Nếu gate FAIL, dừng pilot và xử lý theo §5.

Lần chạy 2026-11-08 trên working tree P1–P6: **43 passed** trong 167,88s; receipt `qnu_v1_test_002421364e204f88`, `db_dropped: true`, `legacy_sentinel_preserved: true`, `pytest_exit: 0`, `seconds: 176.42`. Đây là gate bất biến trước pilot, không thay thế phiên pilot thật.

Ma trận trình duyệt P1–P6 ngày 2026-11-08: 11 route × 3 khổ × 2 theme = 66 lượt trên Vite `127.0.0.1:3001` với auto-login dev; 0 lỗi console; sau sửa không còn tràn ngang; `?stage=publication` và các link cũ `?tab=sources|compilations|documents|index`, `?sourceAction=ocr` giữ đúng stage. Tab order qua brand, 8 mục điều hướng và menu tài khoản. Ảnh đã xem: nguồn 390px sáng, xuất bản 390px/1280px sáng; các tổ hợp còn lại dựa trên số đo và ảnh lưu ở thư mục tạm ngoài Git. Đây là gate UI trước pilot, không thay T1–T6 với người thật. **Ghi chú lịch sử (2026-11-13):** ma trận này chạy trên `frontendV1` đã được gỡ khỏi repo; giao diện hiện hành là `frontendV2`.

Frontend tối thiểu (khi có sửa mã UI): `npm run typecheck`, `npx vitest run tests/v1-answer-review-p6.test.ts tests/v1-conversation-errors-p6.test.ts`, `npm run build`. Kiểm trình duyệt 390px/1280px cho các luồng §3–§4; ghi rõ ảnh đã xem hay chưa. **Ghi chú lịch sử (2026-11-13):** các lệnh `vitest` trên thuộc bộ test `frontendV1` đã gỡ; `frontendV2` hiện chỉ có Biome và `npm run build`, chưa có bộ test riêng.

## 8. Mẫu biên bản phiên pilot

Lưu một tệp trong `docs/nhat_ky/` theo mẫu `YYYY-MM-DD_phien_NNN_pilot_qnu_v1.md`, chỉ gồm dữ liệu ẩn danh:

1. Đơn vị/workspace (mã), người tham gia (mã), môi trường/commit/migration hiện tại.
2. Bảng thời gian T1–T6 và số lần dev hỗ trợ.
3. Kết quả ma trận §4, kèm mã lỗi/correlation id đã che thông tin nhạy cảm.
4. Danh sách lỗi S1–S4 và quyết định sửa/backlog.
5. Checklist §6.1 với PASS/FAIL/PENDING/NOT RUN và bằng chứng.
6. Kết luận: có đủ điều kiện mở rộng không; việc cần làm tiếp; không tự triển khai production.
