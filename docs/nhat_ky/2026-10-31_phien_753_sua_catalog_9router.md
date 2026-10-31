# Phiên 753 — Sửa discovery catalog lớn của 9router

## Nguyên nhân và phạm vi

Người dùng chọn model chat 9router trong provider-setup rồi bị BLOCKED. Chẩn đoán ModelOps của phiên E2E hiện tại ghi `provider_response_invalid`, HTTP 200. Đọc catalog qua endpoint và key đã bảo vệ trong ModelOps xác nhận 638 model, không ID sai/trùng và có đúng model đã chọn. Adapter cũ từ chối mọi danh sách trên 500 model.

Sửa adapter nhận tối đa 5000 model với mã `provider_catalog_too_large` nếu vượt mức; không truncate. Dùng set kiểm ID trùng; giữ kiểm credential reflection, ID và metadata mọi dòng. Script setup phân biệt discovery thất bại với model vắng mặt, chỉ hiện code/status đã kiểm định, không hiện upstream detail. Không đổi key, default, capacity, DB/checkpoint hoặc restart serve; không inference.

## Kiểm chứng thực chạy

- Trước sửa, ba regression catalog 638/5000/5001 thất bại đúng nguyên nhân.
- Trong backendV1: `.venv/Scripts/python.exe -X utf8 -m pytest tests/unit/test_provider_diagnostics.py -q`: **40 PASS**, exit 0. Có trường hợp model cuối danh sách, vượt trần và lỗi ID/trùng/phản chiếu credential sau dòng 500.
- Root: `backendV1/.venv/Scripts/python.exe -X utf8 -m unittest discover -s scripts -p 'test_*.py' -q`: **23 PASS**, exit 0. Hai case mới kiểm lỗi setup an toàn và model thiếu.
- Ruff check/format-check có phạm vi bốn file Python: PASS. UTF-8/LF và diff-check kiểm cuối task.
- Full Pytest lần đầu: 464 PASS/1 FAIL/69 SKIP/24 ERROR vì thư mục temp Windows từ chối truy cập. Rerun với `--basetemp ../tmp/pytest-753-20261031 --tb=short`: **488 PASS/1 FAIL/69 SKIP**, exit 1. Lỗi nền giữ nguyên `tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge` (`invalid_identity`), khớp lịch sử 751. Không sửa ngoài phạm vi; full gate vẫn FAIL. Integration cần DB test riêng giữ SKIP.
- Live GET catalog bằng adapter mới, cùng endpoint/key ModelOps: **HTTP 200, diagnostic_ok, 638 model**, có alias được chọn. Không lưu raw response/key. Context/output của alias trả null; không tự suy capacity.
- E2E provider-setup/model-chat/compilation sau sửa: **NOT RUN**. Serve người dùng đang chạy mã cũ; cần mở lại trước test. Live discovery không chứng minh inference hoặc biên soạn đạt.

## Bàn giao

Giữ phiên/key hiện tại. Ctrl+C tại đúng cửa sổ serve, chạy lại `./test-v1-e2e.ps1 serve`, đợi E2E live. Cửa sổ khác chạy `./test-v1-e2e.ps1 run provider-setup --headed`, chọn 2; nhập giới hạn context/output Ollama thực tế khi script hỏi. Không cleanup/init. Hướng dẫn tại [quy trình test lại](../quy_trinh/V1_QUY_TRINH_TEST_LAI.md).
