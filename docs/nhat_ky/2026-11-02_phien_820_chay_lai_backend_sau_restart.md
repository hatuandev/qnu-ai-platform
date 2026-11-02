# Phiên 820 — Chạy lại backend sau khi khởi động Docker

## Yêu cầu và phạm vi

Người dùng đã mở lại Docker, yêu cầu chạy lại phần kiểm tra bị ngắt ở phiên819.
Chỉ kiểm chứng backend; không sửa mã ứng dụng hoặc assertion, không chạy lại
OCR/compiler với model thật, không restart API/worker chính và không commit/push.
Giữ các thay đổi chưa commit của phiên815–819.

Đối chiếu PROJECT_CONTEXT, Git/diff và runtime thực tế. Docker chính đang chạy,
năm container E2E 93faa11f0caf còn dừng: chỉ khởi động lại đúng năm container này.
Database còn sót `qnu_v1_test_reverse819final_1793613912652669300` không có client;
đã dọn và xác nhận remaining=0.

## Phương pháp

- Collector hiện tại thu đủ 1.285 node test. Chia theo file thành ba nhóm rời nhau
  428/429/428; mỗi tiến trình có PostgreSQL database, storage, basetemp, namespace
  cache và queue riêng. Không dùng chung database giữa các nhóm.
- Redis loopback của phiên E2E, DB14, prefix test riêng. Chặn kết nối ngoài
  loopback; provider của các test là giả lập nội bộ. Không gửi corpus tới AI thật.
- Giữ log, JUnit và receipt của từng nhóm. Đối chiếu chính xác tập node ID giữa
  collector và JUnit: không thiếu, thừa hoặc trùng ca, kể cả tham số IPv6 có `::`.
- Không sửa assertion, không retry model để làm xanh. Các kiểm tra bổ sung dưới
  đây nhằm phân biệt lỗi môi trường Windows/fixture với lỗi ứng dụng.

Lệnh điều phối thực chạy tại root:

```text
backendV1/.venv/Scripts/python.exe tmp/resume820/run.py
```

Các tiến trình con chạy `pytest <các file được phân nhóm> -v --tb=short`, có
JUnit và basetemp riêng, cwd `backendV1`.

## Kết quả toàn phần

| Nhóm | PASS | FAIL | Exit | DB còn lại |
|---|---:|---:|---:|---:|
| 1 | 424 | 4 | 1 | 0 |
| 2 | 429 | 0 | 0 | 0 |
| 3 | 425 | 3 | 1 | 0 |
| Tổng | **1.278** | **7** | **1** | **0** |

Không SKIP/ERROR; đủ 1.285/1.285 node. Wall time điều phối 1.152,05 giây
(19 phút 12 giây). **Full gate vẫn FAIL**, không thay kết quả lượt đầu bằng kết
quả kiểm tra bổ sung. Nhóm regression readiness819, worker timeout819 và
lifecycle runtime659: **18/18 PASS**.

## Phân loại bảy ca FAIL

| Ca | Bằng chứng/nguyên nhân |
|---|---|
| `test_lifecycle_659.py::test_preview_is_bound_to_actor_and_state` | Mong 200 nhưng nhận404 khi chuẩn bị purge; platform actor trong fixture không có membership admin thực cho background actor. Đã tái hiện trên HEAD sạch ở819. |
| `test_knowledge_regressions_639.py::test_downgrade_cannot_mark_success_and_block_next_upgrade` | Assert head `0007_native_extraction`, thực tế `0010_review_refinement`; lỗi tương tự trên HEAD sạch trong lượt này. |
| `test_source_purge_716.py` (unit), `test_accept_rechecks_publication_after_preview_before_preparing_purge` | Fixture/mock không cung cấp định danh hợp lệ cho kiểm tra quyền purge; lỗi `Thiếu định danh đã xác thực`. Đã tái hiện trên HEAD sạch ở819. |
| `test_workspace_model_schema.py::test_migrations_match_models_and_exclude_legacy` | Lượt chia nhóm thiếu bảng legacy mẫu của harness chuẩn. Sau bổ sung đúng mẫu trong database thử khác, cả HEAD sạch và mã hiện tại vẫn FAIL vì assert head0007 thay vì0010. So schema/ORM và kiểm tra legacy trước assert head đều đạt ở kiểm tra bổ sung. |
| `test_compiler_source_versions_654.py::test_exact_saved_text_is_pinned_despite_newer_saved_text` | Text đã sửa khớp, nhưng test đọc trường `text_version` không có trong model message đã chiếu gọn; KeyError. Đã tái hiện trên HEAD sạch ở819; không kết luận mất bản sửa chỉ từ assert này. |
| `test_recovery_666.py::test_full_recovery_into_new_targets_keeps_originals_credentials_and_search` | Bộ chạy bật Selector loop để tránh lỗi portal Windows ở nhóm TCP; loop này không hỗ trợ subprocess phục hồi. Tái hiện trên HEAD sạch với cùng thiết lập. Kiểm riêng mã hiện tại bằng Proactor loop chuẩn: **1 PASS**, 18,78s, exit0, DB đã dọn. Đây là sửa môi trường chạy, không đổi mã sản phẩm. |
| `test_source_purge_716.py` (integration), `test_unpublished_purge_is_durable_irreversible_and_keeps_other_uploads` | Các assert purge hoàn tất, xóa đúng bytes, giữ nguồn khác và chống restore đều qua; assert cuối gọi `/lifecycle/source-deletions` thiếu query `collection_id` bắt buộc nên nhận422 thay vì `[]`. Tái hiện trên HEAD sạch trong lượt này. |

HEAD baseline sạch dùng cho đối chiếu: `81e5f1a250ffa041682edcf3d141def561a046c9`
tại `tmp/release-v1.0.3`. Không nới quyền hoặc biến lỗi provider thành không có dữ liệu.

Sau khi chạy riêng phục hồi với đúng loop Windows, ca phục hồi PASS; sáu ca
test nền còn lại chưa sửa. Không cộng lượt kiểm bổ sung vào số ca độc lập của
full suite và không gọi toàn bộ backend PASS.

## Dọn tài nguyên và bàn giao

- Database của ba nhóm, các lượt baseline/diagnostic và database819 còn sót:
  đã xác nhận không còn.
- Chỉ xóa ba key dưới namespace cache test được xác định thuộc lượt này;
  remaining=0. Không `FLUSHDB`, không xóa cache ứng dụng chung.
- Giữ log, JUnit, các lỗi lần đầu và artifact test. Không cleanup/init phiên E2E,
  không thay ModelOps, không chạy lại model thật, không restart dịch vụ chính.
- Sáu ca test nền cần cập nhật fixture/contract đúng hiện trạng ở nhiệm vụ sau;
  không có thay đổi source ứng dụng hay test được thực hiện trong phiên820.
- FE700/700 và nghiệm thu47 kiểm tra model thật là kết quả **phiên819**, không
  chạy lại trong phiên này.

Artifact chính: `tmp/resume820/summary.json`, `verification.json`, `cleanup.json`,
`receipt.json`, `plan.json`, log/JUnit của ba nhóm và các log đối chiếu baseline.
