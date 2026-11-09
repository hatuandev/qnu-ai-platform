# Phiên 907 — Tối ưu ngữ cảnh RAG đang làm dở

Người dùng yêu cầu tiếp quản phần tối ưu sau khi dừng agent IDE. Giữ mọi thay đổi KH16 chưa commit, dữ liệu ứng dụng và index đang có; không restart, reindex, reset hoặc push.

## Thay đổi

Tiếp tục payload v19 do IDE đang sửa: bảng dùng catalog chọn ô, không gửi lại geometry/JSON bảng trong prompt; provenance đầy đủ vẫn ở server. Sửa dedup: chỉ alias các chuỗi passage giống hoàn toàn, đúng thứ tự và cùng phiên bản/quyết định xuất bản. Giữ nguyên nội dung khi chỉ trùng một phần để không mất điều kiện/đảo câu. Selection v2 chỉ bỏ bản trùng có cùng text/citation locator/structure; bỏ cắt theo trần số đoạn đoán từ loại câu hỏi. Không hạ output hay tăng context để che lỗi.

Profile QNU E2E trước đó không khai báo reasoning dù seed local có. Bổ sung policy off theo hợp đồng endpoint/model QNU đã kiểm ở G0; helper setup chỉ áp dụng policy profile khai báo, lưu và đọc lại qua ModelOps. Các provider khác không có policy được giữ nguyên. Không sửa cấu hình runtime/DB hiện hành. Các nhóm test Windows TCP dùng opt-in Selector có sẵn, không đổi event loop sản phẩm.

## Kiểm chứng thực chạy

- Backend focused: 80 passed (2,50 giây).
- Toàn bộ unit backend: 858 passed, 4 cảnh báo (19,52 giây), cwd backendV1, basetemp riêng trong workspace.
- API/coverage integration: 34 passed, 2 cảnh báo (290,02 giây), harness DB cô lập, Selector. Receipt qnu_v1_test_e4c34fc5c21f4df8 xác nhận db_dropped=true, legacy_sentinel_preserved=true, exit0.
- Ruff scoped và diff whitespace scoped đạt. Diff toàn repo còn CRLF/trailing whitespace từ thay đổi preparation/router.py ngoài phạm vi, không tự sửa.
- Frontend helper: 3/3 Vitest; Biome scoped, build + TypeScript và E2E typecheck exit0. Build còn cảnh báo chunk >500kB.
- Full backend gồm toàn bộ integration: NOT RUN. Không tuyên bố toàn hệ thống PASS.

Các lượt sai môi trường được giữ: unit lần đầu vướng thư mục Temp Windows; lần root cwd lỗi hai migration test và recovery CLI do đường dẫn tương đối. Sửa cách chạy (cwd backendV1 + basetemp riêng), không bỏ assertion. Lần harness integration đầu cwd backendV1 không đọc được .env root nên lỗi xác thực PostgreSQL trước test; chạy lại đúng root cwd đạt. Hai lần smoke chuẩn bị actor/hash sai dừng trước gọi model; giữ artifact, không tính là inference retry.

## Đo ngữ cảnh/model thật

Artifact cục bộ tmp/v1-user-workflow-eval/ctx-opt-20261108/: baseline-cost.json giữ nguyên; optimized-cost.json, summary.json, live-smoke-authenticated.json, live-smoke-reasoning-off.json, smoke-grading.json và log test/build. Không thêm corpus hay phản hồi model vào Git.

Rebuild cùng snapshot/index và hit IDs của baseline; không retrieval lại/reindex. Đo offline 13 câu: median request bytes giảm khoảng 70,6%. Smoke Qwen 8 câu F01/F02/F03/F06/F09/F11/F12/F13, một lần gửi mỗi câu ở cấu hình gốc. Median prompt token giảm 71,99%, median generation 11,047 giây. Đây là smoke prompt với evidence cố định, không phải E2E retrieval hoặc nghiệm thu 77/97 câu.

Chấm bằng rule benchmark draft: 7 đạt, F13 sai/thiếu điều kiện. Cell proofs cho chấm được dựng lại từ statement materialized trùng khít catalog nguồn, không phải trace raw mới của API. Nhãn chưa được người duyệt xác nhận; rule PASS không chứng minh semantic đúng toàn bộ.

F13 ở cấu hình reasoning mặc định mất 427,891 giây, không đạt nội dung. Chạy một thí nghiệm khác riêng F13 với directive off đã được kiểm chứng cho đúng endpoint/model: 12.211 prompt token, 5,469 giây, insufficient_evidence. Không gộp lần này thành PASS hay retry để làm xanh. Bằng chứng cố định gồm các dòng điều kiện bị rời (trang 7–8), không đủ đoạn nối tiếp để trả đầy đủ. Tối ưu serialization không tự chữa thiếu coverage. Các response gốc vẫn có reasoning; không nhận là đã tắt trên DB E2E đang chạy. Không tuyên bố tốc độ đuôi đã ổn.

## Tiếp theo

Cần kiểm coverage cấu trúc và nối câu cho nhóm câu điều kiện bằng retrieval thật; dùng profile reasoning off đã khai báo cho cohort mới, giữ kết quả lỗi. Chưa chạy lại full benchmark/pilot. Không cần xóa file hoặc lập chỉ mục lại chỉ vì đổi prompt projection.
