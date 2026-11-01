# Phiên 796 — Review độc lập bản sửa FE795

Ngày 01/11/2026. Người dùng yêu cầu xem lại bản triển khai prompt794. Review đọc Git/diff, source và kiểm chứng độc lập; không sửa application hoặc cấu hình live. Áp dụng clean-code, frontend/backend và ModelOps của repo.

## Kết luận

Catalog BE đã nối ngân sách sang consumer; đường Save xóa giới hạn có xác nhận; ba mã lỗi BE được phân loại; nguồn từng giới hạn token đơn đã có projection. Full FE xanh là kết quả đã tái thực chạy. Tuy nhiên còn ba P2:

1. **Pending patch của form sống qua lỗi và lần mở sau.** `provider-form-dialog.tsx:189–206` reset form/confirmation nhưng không xóa `pendingClearLimitsPatch`; catch ở220–226 cũng giữ patch. Tái hiện: sửa tên, xóa limits, Save và xác nhận; API thất bại; đóng/mở form thấy tên cũ đã lưu; bấm nút Xóa khai báo rồi xác nhận ⇒ request lại kèm tên nháp của lần trước. Dòng212 ưu tiên patch cũ nên có thể cập nhật dữ liệu người dùng không còn thấy trong form hiện tại. Cần reset patch theo vòng đời form/provider và tách intent xóa riêng với Save đang chờ; giữ draft khi lỗi trong cùng phiên chỉnh sửa.
2. **Nguồn OCR vẫn bị gắn nhầm.** `provider-detail.tsx:299–302` hỏi nguồn `input_tokens_upper_bound`, trong khi BE lưu và trả nguồn của cả khai báo OCR dưới khóa `ocr_page_input`. Resolver không tìm khóa cha nên fallback sang capacity_basis. Với context/output từ server và OCR operator_configured, dòng bound lại ghi Server công bố. Probe dùng đúng TokenLimits/OperationalBudget hiện tại đã xác nhận. Cần lấy provenance của `ocr_page_input` cho các trường con OCR.
3. **Regression mới dùng dữ liệu không thuộc hợp đồng BE.** `modelops-p2-regressions-795.test.tsx` dùng calculated/verified/healthy, capability compiler, effective_context/effective_output, operational_ceiling, context_window và prop showDetail. Contract thực dùng configured/unknown/stale, declared/provisional/blocked, capability chat và `token_limits.context_window_tokens`, nguồn application_default. Vitest transpile nên test vẫn chạy; production tsconfig chỉ include src/vite.config.ts. Kiểm kiểu riêng file mới báo **19 lỗi**, đều ở file regression. Một số assertion chỉ kiểm nhãn xuất hiện đâu đó hoặc echo lại healthy giả, không chứng minh wire từ API tới UI. Cần fixture theo response/schema thật, assert theo từng dòng và regression cho hai tình huống trên; không mở rộng contract để hợp fixture sai.

Hai probe FE đều PASS ở kỳ vọng mô tả khuyết điểm; đây là xác nhận lỗi, không phải nghiệm thu tính năng.

## Kiểm chứng thực chạy

| Kiểm tra | Cwd | Kết quả |
|---|---|---|
| `npm test -- --run --reporter=json --outputFile=../tmp/review796-full-vitest.json` | frontendV1 | Exit0, **651 PASS / 0 FAIL / 0 pending**, 95 suites |
| `npm run build` | frontendV1 | Exit0; Vite12.72s + tsc đạt; warning bundle lớn hiện hữu |
| Biome các file FE sửa/thêm | frontendV1 | Exit0, **22 file PASS**, không auto-fix |
| Ruff ba file ModelOps BE sửa | backendV1 | Exit0, PASS |
| `python -m pytest tests/unit -q --basetemp=../tmp/pytest-review796-owned` | backendV1 | Exit1, **655 PASS / 1 FAIL**, 29.43s |
| API catalog/projection/quyền với PostgreSQL test riêng | backendV1 | Exit0, **4 PASS**, 9.56s; migration exit0; xác nhận DB sở hữu còn0 sau drop |
| `npm exec -- vitest run --config tmp/review796.config.ts` | frontendV1 | Exit0, **2 probe xác nhận khuyết điểm**, 6.32s |
| Typecheck riêng test795 với Vite types | frontendV1 | Exit2, **19 lỗi trong file regression mới** |
| `git diff --check -- frontendV1 backendV1` | root | Exit0, PASS |

Lỗi unit còn lại: `tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`, fixture actor thiếu danh tính nên nhận401 thay vì guard409. Giữ nguyên lỗi cũ, không báo full backend PASS. Lượt unit đầu dùng tmp mặc định gặp24 setup errors do WinError5 ở pytest-of-AnhTuan (631 PASS/1 FAIL/24 ERROR); lưu log, đổi sang thư mục test riêng chưa tồn tại rồi chạy lại. Không sửa test/application để đổi kết quả. Đây không phải retry inference.

Typecheck thử đầu thiếu khai báo ImportMeta.env trong config probe; đã bổ sung `vite/client` chỉ vào config ignored, chạy lại còn đúng19 lỗi của regression795. Production build không lỗi vì không kiểm kiểu tests.

### Đối chiếu 26 test cũ

So exact file + test name với793: **22 ID còn nguyên đạt PASS; 4 ID được thay tên/nội dung**. Ba test liên kết compiler/publication/serving đổi thành kiểm panel nhúng; phù hợp UI hiện tại, nhưng chưa kiểm hành trình thao tác trong panel. Test phân trang/chọn workspace Dashboard đổi thành kiểm tự chọn workspace đầu tiên; không phải cùng phép kiểm trước. Không mô tả kết quả này là26 exact IDs cũ cùng đạt. Fixture auth/query ở các nhóm khác đã được bổ sung. Test20 câu tăng timeout15s; lượt full độc lập đo7.38s, nên có bằng chứng ngưỡng5s không đủ trong lượt này. Bốn test capacity cũng tăng timeout, lượt này mất1.22–2.64s; chưa kết luận đó là lỗi sản phẩm.

### API và giới hạn

API probe dùng stack FastAPI/SQLAlchemy và DB riêng `qnu_v1_test_review796_*`, cùng PostgreSQL service nhưng không truy vấn/chỉnh DB live. Kiểm catalog provisional đúng schema, nguồn input thủ công qua HTTP, không xuất secret/config/base_url, outsider404, disabled/revoked không còn trong catalog. Không gọi upstream/model thật; không fake persistence. DB đã drop và kiểm còn0. Test/probe/config review giữ ở tmp Git ignored.

Không chạy visual desktop/mobile/light/dark hoặc live benchmark. Không restart, reindex, publish, đổi key/quota/corpus/ModelOps hay gửi lại uncertain789; giữ session93faa11f0caf. Không kết luận toàn bộ prompt794 đã hoàn tất khi còn ba P2.

## Artifact và bàn giao

- `tmp/review796-full-vitest.json`, `tmp/review796-full-vitest.log`, `tmp/review796-baseline-comparison.json`.
- `tmp/review796-build.log`, `tmp/review796-biome.log`, `tmp/review796-unit.log`, `tmp/review796-unit-owned.log`.
- `tmp/review796-probes.log`, `tmp/review796-contract-types-final.log`, `tmp/review796-api.log`, `tmp/review796-api-migration.log`.
- Probe FE `frontendV1/tmp/review796-probes.test.tsx`; API probe `backendV1/tmp/test_review796_catalog.py`. Không đưa probe xác nhận lỗi thành test acceptance xanh.

Thứ tự sửa tiếp: vòng đời pending patch → nguồn OCR theo field cha → sửa fixture/regression đúng hợp đồng và kiểm lại toàn bộ. Review này chỉ ghi nhận, giữ mọi thay đổi người dùng đang có.
