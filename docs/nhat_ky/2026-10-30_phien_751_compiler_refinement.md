# Phiên751 — Compiler chia tiếp cha–con

## Phạm vi

Người dùng giao tiếp tục IDE đang dở, triển khai chia thích nghi và kiểm chứng chặng compiler. Giữ diff IDE: review/parts, recovery opt-in, scripts. Áp dụng quyền test/live/serve E2E theo prompt được người dùng xác nhận đang chạy, giữ dữ liệu phiên cũ. Không deploy/push/reindex/publication.

## Thực hiện

- Planner v5, projection v4: mỗi lượt mới có phần bền vững; raw length+visible content cho phép chia hai nhóm unit, tránh rowspan, giữ context/output cap. Không retry uncertain hay mọi422.
- Migration0009 parent_segment_id + Markdown artifact. Parent/child trong cùng run, lease serialize index allocation; giữ raw/trạng thái/usage lỗi. JSON/MD mỗi node lưu/readback trước commit; parent ghép bằng backend, main liên kết roots. API đọc node dưới quyền workspace/collection hiện có.
- Giới hạn sâu4/node31xroots/thời gian1500s; dispatch kiểm thời gian còn đủ queue+inference. Usage tổng gồm lần parent lỗi.
- Giữ snapshot v2/v3/v4. Recovery `--recover` của IDE được giữ; thêm replan draft completed do planner cũ nếu chưa xuất bản, cần cùng opt-in. Không cleanup/init/reset DB cũ.

## Kiểm chứng và vận hành

- Regression cũ trọng tâm36PASS; unit mới3PASS; integration SQL/HTTP/artifact mới2PASS trên DB qnu_v1_test_refinement751, RedisDB14 namespace qnu:test:751 (không DB/cache phục vụ).
- Migration từ rỗng đến0009 trên DB riêng đạt; migration0009 vào phiên E2E7082ee7b7311 qua serve hiện có đạt.
- Bộ unit rộng:434PASS/5FAIL/24ERROR.24ERROR do quyền Temp Windows;5FAIL: hai review_parts744 capacity8000, hai migration_baseline661, source_purge716 identity. Không coi tổng gate đạt.
- Integration bổ sung3PASS/1FAIL: test compatibility cũ còn kỳ vọng new run không có part. Đã đổi contract test cho lượt mới một phần, không đổi expectation coverage/review để làm xanh. Legacy code path vẫn giữ. Cần kết quả chạy lại sau thay đổi.
- FE14testPASS, E2ETS exit0; build kết quả chờ. Full test DB riêng và live compilation đang được kiểm tra, cần bổ sung kết quả cuối.
- Lượt IDE trước cmp_a2bf6393ebdf đã completed4/4 trong152.2s, nhưng review cũ interrupted409. Lượt v5 mới được tạo bằng --recover, hai phần chạy đồng thời; chưa kết luận PASS ở mốc ghi nhật ký này.

## Kết quả bổ sung sau triển khai

- 92 unit liên quan compiler/review/refinement/reasoning/admission/migration PASS; Ruff phạm vi thay đổi và `git diff --check` PASS. FE: 15 kiểm tra tập trung, TypeScript E2E và build PASS.
- Chạy tích hợp trên DB riêng `qnu_v1_test_refinement751b`, Redis DB14 và namespace riêng. Refine với output 4096: giữ nguyên ceiling ở mọi request, chia hai con, giữ raw, tổng usage không đếm hai lần; links cha/con/main đọc được và outsider nhận 404 theo hợp đồng workspace. Phục hồi sau commit raw không gửi lại parent. Leaf uncertain giữ unknown usage và không gửi lại. Năm kiểm tra refinement/compat nhỏ PASS.
- Review literal: chỉ so sánh chính xác ô nguồn, không xác minh OCR với ảnh; sai text/span/header/vị trí/bảng hoặc thiếu nguồn đều cần model. Chạy tối đa hai phần review bằng phiên DB riêng, vẫn qua admission chung. Tích hợp HTTP thật với provider giả chứng minh overlap hai request, giảm số call ở phần literal, coverage đầy đủ và replay không gọi lại. PASS.
- Nhóm integration review/gate trước đó: 15 PASS và 1 FAIL do cửa sổ đo overlap giả 100ms quá ngắn; chạy lại case với latency 1s PASS (đo được hai HTTP call đồng thời). Không giảm assertion peak=2.
- Kiểm tra tương thích rộng hơn: 43 PASS/6 FAIL. Nguyên nhân: API raw của lượt một root thiếu alias sang checkpoint; test truncation còn đòi dừng ngay; fixture inflight còn đặt marker ở run thay vì leaf. Đã thêm alias raw có checksum, giữ raw parent đầu tiên, sửa hai test theo contract mới và chạy lại sáu case. Kết quả cuối cần cập nhật ở dưới.
- Bổ sung phép cộng usage theo từng request, dùng usage parent gốc thay vì tổng subtree; nếu một request chưa rõ usage thì tổng vẫn unknown. Unknown ở con lan lên cha. Không hạ trạng thái ambiguous thành lỗi có thể gửi lại.
- Audit lỗi nền `tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`: vẫn FAIL `invalid_identity` (8 case khác PASS), ngoài phạm vi. Full suite trên DB riêng đã dừng sau tiến độ một phần và có FAIL; không báo PASS toàn repo.
- Live compiler `cmp_e5669beece39`: completed 4/4, 211.6s, 126400 token; dùng OCR PDF đã hoàn tất từ trước. Review `rvw_4ffb3fe33a43` giữ chính sách cũ đang chạy, chưa có kết luận E2E cuối tại thời điểm ghi mục này. Không xuất bản.

Không sửa runtime hash trong khi live đang chạy. Khi kết quả cuối có, cập nhật nhật ký/snapshot. Dừng ở admissions-compilation PASS, không xuất bản.

## Chốt regression và lượt live cũ

- Unit cuối: 95 PASS. FE cuối: 16 PASS; TypeScript E2E PASS. Build frontend đã PASS trước sửa helper E2E; không có sửa mã ứng dụng sau build đó. Ruff và kiểm tra whitespace đạt.
- Sáu case API thất bại đã chạy lại PASS (`api-final2.log`); tổng nhóm API/automatic/review có 43 PASS trước đó. Thêm alias raw cho một root, checksum/ETag giữ nguyên; test inflight chuyển marker sang leaf đúng hợp đồng mới; test truncation xác nhận lỗi atomic và số call có giới hạn.
- Nhóm cuối refinement/literal/segmented-review/Redis: 7 PASS (`final-contract.log`). Redis Lua thật đạt giới hạn hai caller và giải phóng lease đúng; test lần đầu từ chối prefix E2E kế thừa, chạy lại bằng `CACHE_NAMESPACE=qnu:test:751b:` mới PASS. Các lượt test trước đã dùng Redis DB14 riêng, nhưng `REDIS_NAMESPACE`/`OWN_RECONCILE_ENABLED` không phải tên setting có hiệu lực; đã sửa launcher kiểm tra thành `CACHE_NAMESPACE`/`OWN_RECONCILE`.
- Live cũ hoàn tất review 22/22 nhưng chặng FAIL sau 44.4 phút vì 19 findings: 2 omitted, 9 uncertain, 8 unsupported. Không xuất bản hoặc tự chấp nhận findings. Compiler riêng completed trong 211.6s.
- Đọc báo cáo thấy lỗi review context: citation bảng không khớp ID đơn vị ô; citation ô đã owned ở phần trước không mang đầy đủ hàng/header. Đã sửa mapping context bắt buộc, thêm regression và projection compact có replay cũ. Dựng lại đủ 22 scope cũ khớp hash. Narrative và bảng literal không chung ownership.
- Dừng serve E2E do agent tạo PID7468 sau khi lượt cũ kết thúc, nạp mã mới PID29780; không dừng container dữ liệu, không cleanup/init. Đang chạy lại review bằng `--recover`; cập nhật kết quả cuối bên dưới.

## Tiếp tục sau review chưa hợp lệ

- Review `rvw_5a8ab4f8d57f` dừng phần7 sau 8.1 phút với `compilation_review_invalid`: model chọn supported nhưng sáu mục không có source_ids. Không sửa raw hay tự gán nguồn. Contract1 thêm anyOf điều kiện; lượt thật `rvw_9951e90217af` trả stop nhưng thiếu explanation/suggested_action ở các mục (decoder không áp đủ sibling constraints). Lượt này FAIL sau1 phút, không có report hợp lệ.
- Đổi sang reference contract2 với các nhánh object đầy đủ (required, status, enum nguồn, minItems), projection compact/v3; scope cũ full/v1/v2 vẫn dựng đúng schema/hash. Synthetic live qua ModelOps/quota/admission cùng Qwen trả covered/supported, đủ ID và các trường; PASS4.1s/1332token. Không dùng kết quả synthetic để kết luận PDF đúng.
- Recovery chỉ cho phép operator `--recover` tạo review key mới khi response invalid của contract cũ và mọi part là pending/completed/failed; có part running/received/uncertain thì chặn. Không retry cùng request hoặc tự hợp lệ hóa dữ liệu. History giữ cả ba review lỗi/cũ.
- Compiler mặc định thích nghi với trần output DB nếu request không chỉ định: 4K model dùng4096, Qwen vẫn8192; yêu cầu tường minh8192 vượt trần4096 trả422. Integration23 PASS (`default4k.log`), gồm API/quyền/raw/refinement/restart/unknown/4K. Không hứa mọi atomic unit vừa4K.
- Full unit cuối:479 PASS/1 FAIL `source_purge716::test_accept_rechecks_publication_after_preview_before_preparing_purge` invalid_identity; không sửa ngoài phạm vi. Unit liên quan102 PASS. FE17 PASS/TypeScript E2E PASS. Schema/literal/segmented integration5 PASS (`schema-complete.log`); Ruff và whitespace PASS.
- Serve mới do agent PID13512; serve PID29724 đã dừng sau review dừng. Lượt contract2 `rvw_8999dd0820c0` có20parts, đang chạy, còn cần kết quả cuối. Compiler completed cũ được giữ; không publish.

## Kết quả bàn giao cuối phiên

- Contract2 live `rvw_8999dd0820c0` completed20/20, có report hợp lệ, chặng kết thúc sau7.8 phút. Không còn lỗi missing source refs/required fields. Đây là lượt dùng cùng draft `cmp_e5669beece39`, không chạy lại OCR hay compiler.
- Report kiểm564 source units/535 draft units: nguồn555covered/8out_of_scope/1uncertain; draft527supported/2contradicted/5uncertain/1unsupported. Còn9 findings nên `admissions-compilation` vẫn FAIL; giữ assertion không findings, không approve/publish. Báo cáo E2E: `tmp/v1-e2e/7082ee7b7311/runs/admissions-compilation-1793376365086778600/html`.
- Hai nhận xét contradicted nằm ở phần diễn giải bảng (khái quát phương thức cho một nhóm và danh sách ngành thiếu chi tiết). Những nhận xét khác gồm khối figure trống, một mục tiếp nối và các unknown về phạm vi/ngày chưa có căn cứ đủ trong lượt review. Không tự sửa nội dung OCR hoặc gán nguồn để làm test xanh. Muốn nghiệm thu xuất bản cần rà soát/sửa draft và review lại; việc này không được coi hoàn tất chỉ vì cơ chế chia phần đã chạy.
- So sánh quan sát: review cũ44.4 phút/22parts/19findings; review mới7.8 phút/20parts/9findings. Đây là hai lần gọi Qwen trên cùng draft, có khác context/schema/local checks/concurrency; không suy rằng semantic findings ổn định hay mọi tài liệu đều nhanh theo cùng tỷ lệ. Compiler4/4 hoàn tất211.6s riêng, usage126400.
- Cơ chế refinement đã được kiểm chứng qua HTTP/SQL/artifact với output4096, depth/atomic stop, raw retention, usage, source ownership, replay sau raw commit và leaf uncertain. Lượt PDF thật không bị truncation nên không dùng nó để tuyên bố đã quan sát refinement live upstream.
- Tổng gate: full unit479PASS/1FAIL source_purge716 ngoài phạm vi. Các unit trọng tâm102PASS, integration API/refinement/default4K23PASS, integration schema/literal/segmented5PASS, Redis admission thậtPASS, FE17PASS/E2E TypeScriptPASS. Full integration toàn repo chưa chạy hết (lượt rộng trước đã dừng), không báo PASS toàn repo.
- UTF-8 không BOM/LF và `git diff --check` đạt. Giữ toàn bộ thay đổi IDE chưa commit; không commit/push/deploy, không reset/checkpoint cleanup hay xuất bản.
- Dừng serve E2E agent PID13512 sau khi kiểm tra đúng cây tiến trình; giữ container dữ liệu và checkpoint. Lần sau mở hai cửa sổ: cửa sổ1 `./test-v1-e2e.ps1 serve`; cửa sổ2 `./test-v1-e2e.ps1 run admissions-compilation --headed`. Lệnh sau hiện sẽ đọc lại review có9 findings và vẫn FAIL cho đến khi sửa draft; không cần cleanup/init/OCR lại.
