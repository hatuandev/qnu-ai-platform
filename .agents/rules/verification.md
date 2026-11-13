# Kiểm chứng theo phạm vi và rủi ro

Đây là nguồn chung cho AGENTS.md và các skill. Không yêu cầu chạy test ứng dụng cho sửa tài liệu/skill thuần túy.

| Thay đổi | Kiểm tra cuối task |
|---|---|
| Tài liệu/skill/vai trò | YAML frontmatter nếu có, liên kết local, UTF-8/LF, diff và tình huống sử dụng; validator skill khi khả dụng |
| UI/microcopy/style | Biome trên file sửa và `npm run build` trong frontend; script build hiện bao gồm TypeScript. Kiểm tra layout/tương tác khi bị ảnh hưởng; build không chứng minh hình ảnh đúng |
| Logic frontend/auth/API/SSE | Như UI, thêm test hành vi trọng tâm; `npm run typecheck` khi cần kết quả tách biệt hoặc build script không còn gồm TypeScript. Không chạy backend nếu không thay contract/hành vi server |
| Backend | Ruff có phạm vi, regression trọng tâm, rồi full Pytest một lần sau batch ổn định; kiểm tra migration/contract khi liên quan |
| Auth/tenant/secret/dữ liệu/concurrency | Test tái hiện đúng lỗi trước sửa; thêm kiểm chứng ở ranh giới handler/API/adapter liên quan và negative cases |
| Retrieval/model/chunk/index | Regression scope/provenance/ranking và thí nghiệm so sánh cùng snapshot; đổi hành vi tìm kiếm không được nghiệm thu chỉ bằng unit test |

Backend V1: Ruff chạy từ `backendV1` bằng `uv run ruff check <files>`. Từ root dùng `make test-be` cho harness DB cô lập; khi cần pytest trực tiếp phải thiết lập `TEST_DATABASE_URL` thuộc `qnu_v1_test_*` và xác minh fixture trước. Full gate gồm toàn bộ test V1 trong môi trường cô lập, không chạy test trên DB ứng dụng. Kiểm tra fixture trước khi chạy script có thể gọi DB/model/network. Không tự cài thêm gói hoặc chạy live benchmark chỉ để sửa Markdown.

Frontend: từ `frontendV2`, dùng Biome cục bộ đã cài (`npm exec -- biome check <files>`) và `npm run build`. `frontendV2` không có bộ test riêng. Không dùng auto-fix toàn repo hoặc sửa file sinh tự động để che lỗi.

Chạy full suite một lần ở cuối batch; chỉ lặp khi thay đổi mới, failure hoặc nghi vấn chưa giải quyết cần nó. Không chạy lại toàn bộ backend cho UI thuần túy. Nếu thiếu binary/dependency/quyền, ghi NOT RUN và lý do; không coi đọc tĩnh là build/test PASS.

Báo lệnh, cwd, exit code, số pass/fail/skip và giới hạn. Nếu có lỗi nền, đối chiếu exact test IDs với baseline nếu có; tổng suite vẫn FAIL. Không đổi assertion hoặc bỏ guard chỉ để đạt màu xanh.

Test mock/fake chứng minh contract nội bộ, không chứng minh upstream thật hoạt động. Live inference/benchmark chỉ trong môi trường và phạm vi dữ liệu được phép, với egress và credential phù hợp. Không gửi corpus nội bộ ra provider ngoài phạm vi đã cho phép.
