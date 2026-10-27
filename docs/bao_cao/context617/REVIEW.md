# Context617 — Khám phá capacity endpoint và ngân sách compiler tự động

Ngày 24/10/2026. Trạng thái: đã triển khai và kiểm chứng capacity động. Full regression còn lỗi nền, không có regression mới. **Chưa APPROVED toàn compiler.**

## Kết quả thực tế

| Mục | Kết quả |
|---|---|
| Model thử, qua ModelOps được bảo vệ | `ollama/gpt-oss:120b`, reasoning medium; provider trả `gpt-oss:120b` |
| Endpoint công bố | Context **128.000**, đầu ra tối đa **64.000** token |
| Tokenizer | `o200k_harmony`, từ registry tiktoken; không dùng tên model để đoán capacity |
| Phần template đo được | **2.075** token, với hai message system/user |
| Probe tổng hợp gần cửa sổ | **120.002 input + 219 output**, finish `stop`, không fallback |
| Ngân sách đầu ra của probe | **7.998**, tính từ phần context còn lại, không ghim 8.192 |
| Kiểm tra dữ liệu đầu/giữa/cuối | Cả ba marker ngẫu nhiên khớp |
| Sai lệch input cục bộ / usage provider | **0** |
| Giới hạn tối đa được chứng minh chính xác | **Chưa**; thành công xác nhận ít nhất 120.002 input, không chứng minh mọi request 128.000 token đều thành công |

Lượt probe đầu tiên calibration đã thành công nhưng request lớn chưa được gửi: transaction đọc metadata được giữ read-only nên cơ chế lease từ chối UPDATE trước inference. Lỗi harness được sửa bằng kết thúc transaction đọc trước giao dịch inference/usage bình thường. Giữ nguyên artifact FAIL; lượt thứ hai mới là probe lớn PASS. Không gửi lại một inference lớn ở trạng thái chưa xác định.

## Phương pháp

1. Ưu tiên profile endpoint/model đã được operator khai báo, nếu có; không cần chỉnh form ModelOps để chạy discovery.
2. Thiếu profile thì đọc metadata tại **endpoint đang cấu hình**, dùng credential được giải quyết qua ModelOps. OpenAI-compatible/OpenRouter đọc `/models`; Gemini và Claude đọc metadata riêng của model bằng đúng auth của adapter hiện có.
3. Chỉ nhận trường token limit có kiểu và giá trị hợp lệ, gắn đúng model. Khi intermediary và metadata model cùng công bố giới hạn, lấy giới hạn nhỏ hơn. Không suy từ số tham số, tên model, dung lượng file hay độ trễ.
4. Với tokenizer được registry hỗ trợ, calibration tổng hợp qua ModelOps đo phần template bằng `prompt_tokens − tokens(nội dung)`. Chuỗi giống special token trong tài liệu được đếm như văn bản thường.
5. Lỗi HTTP400 có thông số context rõ ràng có thể làm giảm capacity hiệu dụng của đúng route. HTTP401/429/413, lỗi đầu ra, lỗi cấu hình và lời nhắc mơ hồ không phải bằng chứng context. Không cắt nguồn hoặc gửi lại cùng prompt qua khóa khác để che overflow.
6. Tính từng request: `output = min(output_capacity nếu có, context_capacity − input − phần dự phòng đã đo)`. Input gồm nội dung thực gửi và phần template; reasoning dùng chung ngân sách đầu ra theo hợp đồng adapter. Không cộng hai lần phần thinking.
7. Chỉ khám phá primary khi lập kế hoạch. Fallback chưa biết capacity được khám phá khi thực sự dispatch; không bắt model chính dùng capacity nhỏ của model dự phòng và không gọi model dự phòng thừa để calibration.

Cache trong process sống 10 phút, gắn provider/endpoint/model và fingerprint cấu hình credential; không lưu plaintext key hay sửa profile DB. Tokenizer/calibration/capacity tham gia fingerprint compiler để checkpoint không được dùng lại dưới hợp đồng ngân sách khác.

Native Gemini/Claude công bố input limit riêng: bản này dùng nó như envelope chung **theo hướng bảo thủ**, không cộng output để tuyên bố context lớn hơn. Tokenizer chưa được hỗ trợ dùng ước lượng byte có ghi nhãn; không gọi đó là số token chính xác. Native cloud protocol được kiểm bằng fake HTTP; chỉ GPT-OSS qua gateway hiện tại được live-test trong phiên này.

Hợp đồng metadata đối chiếu với [Gemini Models API](https://ai.google.dev/api/models), [Claude Models API](https://platform.claude.com/docs/en/api/http/models) và [OpenRouter Models API](https://openrouter.ai/docs/api/api-reference/models/get-models). Không dùng bảng tên/model limit sao chép từ các trang này làm capacity của endpoint đang chạy.

Không có công thức bảo đảm lấy được context thực của mọi dịch vụ cloud. Provider có thể không công bố metadata, áp giới hạn theo account hoặc route, hay thay đổi model phục vụ. Thiếu bằng chứng thì báo chưa xác định. Một request thành công chỉ chứng minh mức đã thử, không tự nâng nó thành giới hạn tối đa.

## Thay đổi triển khai

- ModelOps: `capacity_discovery.py`, `request_token_budget.py`, request/capacity schema và dispatcher. Quota được kiểm lại bằng ngân sách thực trước thuê khóa. Giữ nguyên quyền, credential, fallback đã cho phép và usage accounting.
- Compiler: route resolver tự lấy capacity primary, chính sách tự động được truyền tới request generator và planner; bộ đếm tokenizer ở bước gửi chạy ngoài event loop. Các policy cũ 24K/2.500 còn để đọc/kiểm thử tương thích, không phải fallback âm thầm khi production route thiếu capacity.
- Dependency: thêm `tiktoken` vào pyproject và lockfile; không cài một model server hoặc framework mới.
- Non-streaming compiler được hỗ trợ. Automatic budget có schema truyền riêng ở transport hoặc cấu trúc hội thoại chưa calibration bị từ chối rõ ràng; không giả số đếm chính xác. Streaming cũ giữ hợp đồng hiện có.

## Compiler trên ba DOCX 2024–2026

Sử dụng service create/read hiện có, actor và DB/LocalStorage fixture riêng. Giữ **381 canonical proofs**, snapshot `59eb474ad57dc88b943504a46bc9cce8c718a302072b309c5c87022bd7f6ef66`; không reparse, reindex hoặc sửa nguồn. Chỉ câu 5.081/Giới tính năm 2025; **không chạy 64 câu**.

Kết quả **FAIL ở hợp đồng tham chiếu**, không phải overflow: 29 inference, tất cả `stop`, không fallback; input lớn nhất 32.535, output lớn nhất 2.898, không request nào bị ước lượng thiếu input. Ngân sách đầu ra từng request được endpoint cho tới 64.000; không bị trần 2.500/8.192 cũ.

29 là số inference của các bước compiler, không gồm những probe calibration/kiểm chứng capacity riêng ở trên. Discovery tokenizer cần một probe calibration khi cache chưa có; chỉ primary được probe trước thực thi, không gọi fallback thừa.

Hai lần PacketDraft bị từ chối theo quy tắc correction có sẵn. Model chọn `q7` làm metric và `q84` làm scalar trong khi các trường ấy chỉ được chọn từ enum role tương ứng và không chứa các ID này. Không đổi enum, không tự gán ID khác hoặc làm yếu Quality Gate để vượt qua. Không có bundle cuối để nghiệm thu nội dung hoặc trả lời câu hỏi 5.081.

Seals sau thử xác nhận shared source/binding/revision/index, assistant, provider và defaults giữ nguyên. ModelOps chỉ ghi lease/usage vận hành hợp lệ. Mặc định toàn app vẫn `gh/gpt-6-luna`; GPT-OSS là override có phép trong tiến trình thử này.

## Kiểm chứng

- Baseline discovery: **14 PASS / 5 FAIL**, exit 1. Năm lỗi có test ID lưu trong XML: malformed metadata, top-provider context, wrapped runtime error và disabled provider. Sau sửa: cùng 19 ID PASS; không xóa case lỗi.
- Baseline dynamic compiler: **2 PASS / 5 FAIL**, exit 1; sau sửa các case đã PASS.
- Focused rộng: **338 PASS / 1 FAIL**, exit 1; test mock route 603 thiếu contract provider mới. Đã cập nhật fixture bằng discovery mock, giữ kiểm tra opaque seal/rotation và không gọi mạng thật.
- Focused chốt: **54 PASS**, exit 0, bao gồm 43 test mới và route adapter tests. Có test fallback/lease/quota, auth/redirect/secret, endpoint isolation, native cloud metadata, special-token text và minimum output.
- Ruff trên 16 file thuộc phạm vi: **PASS**, exit 0.
- Full đầu trong `checks-final`: **INCOMPLETE**, dừng khi review phát hiện cần tránh discovery fallback trước primary. Không dùng kết quả dở làm PASS.
- Full cuối `checks-release/full-final.xml`: **3.744 PASS / 18 FAIL nền / 17 SKIP**, exit **1**. Toàn suite vẫn **FAIL**. Log lần này không thống kê riêng subtest; không cộng số subtest lịch sử từ baseline.
- Đối chiếu với `context614/final-validation/full-final.xml` (3.622/18/17): cả **18 test ID lỗi và nguyên nhân khớp chính xác**; không regression hoặc test mất không giải thích được. Có 123 ID thêm đều PASS, gồm một ID đổi tham số `[600-False]`→`[600-True]` đã ghi rõ do wire packing Context616. Mức tăng ròng là 122 test, không gọi cả 123 là test mới độc lập.
- Registry lookup tokenizer được giữ thuần đọc tên encoding; nạp asset/đếm nội dung ở bước calibration và generate chạy ngoài event loop. Focused release trên mã chốt **54 PASS**, exit0; fingerprint 16 file Ruff chốt giữ nguyên sau validation.

Artifact riêng trong `backend/storage/context617`: baseline/focused XML và exit receipt, `live-capacity-2/result.json`, `compiler-live/failure.json`, metrics và seals. Không đưa corpus hoặc artifact riêng vào Git.

### 18 lỗi nền được đối chiếu

Mọi ID dưới đây có cùng nguyên nhân với baseline614; không sửa fixture/guard để làm suite xanh:

| Test ID (trong `backend/tests`) | Nguyên nhân giữ nguyên |
|---|---|
| `test_configuration_seed_db::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import` | DB test không có `alembic_version`; không migration shared DB để che lỗi |
| `test_consulting_dispatcher::test_dispatch_admissions_with_export` | Thiếu fixture `col_admissions` |
| `test_consulting_dispatcher::test_dispatch_regulations_with_export` | Thiếu fixture `col_regulations` |
| `test_ingestion_resilience::test_shared_capacity_bounds_twenty_simultaneous_requests` | Endpoint capacity AI không khả dụng trong môi trường cô lập |
| `test_ingestion_resilience::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item` | Redis thử nghiệm `127.0.0.1:1` không kết nối |
| `test_ocr_modelops_safety::test_paddle_does_not_fabricate_confidence_or_shift_blank_page` | Endpoint capacity AI không khả dụng |
| `test_publishing_v2_cutover_and_gc::test_gc_api_endpoint` | HTTP403, test kỳ vọng200 |
| `test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api` | HTTP403, test kỳ vọng200 |
| `test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled` | HTTP403, test kỳ vọng400 |
| `test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled` | HTTP403, test kỳ vọng201 |
| `test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit` | HTTP403, test kỳ vọng200 |
| `test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback` | HTTP403, test kỳ vọng200 |
| `test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies` | Không có issue `legacy_payload_schema` như kỳ vọng |
| `test_tools::test_fact_layer_lookup_tool_found` | Fact lookup trả `False` |
| `test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims` | Role `AI.Admin` khác `admin` |
| `test_universal_tools::test_fact_layer_lookup_tool` | Fact lookup trả `False` |
| `test_universal_tools::test_dispatch_admissions_with_dynamic_facts` | Thiếu fixture `col_admissions` |
| `test_vllm_reranker::test_vllm_embedding_generation` | Embedding/capacity provider không khả dụng trong môi trường cô lập |

## Phạm vi và việc còn lại

Không đổi model mặc định, source hoặc Quality Gate; không publish, vector write, restart, migration production, commit hay push. Lỗi enum role của compiler cần xử lý riêng ở bước chọn span/đóng gói và kiểm chứng lại; tăng context không tự bảo đảm hiểu đúng ngữ nghĩa.

Đã dọn **bốn DB thử nghiệm Context617** theo tên/nonce ownership sau khi xuất bằng chứng: focused, acceptance, full bị ngắt và full cuối. Storage bằng chứng giữ theo chính sách bảo vệ; không vô hiệu hoặc bypass thao tác xóa bị chặn ở các phiên trước. Hai DB616 cũ giữ nguyên theo bàn giao616, không sửa hoặc giả trạng thái job cũ.

Xác minh cuối: hash ba nguồn DOCX giữ nguyên; sáu nhóm bảng shared domain (collection/binding/source/index/assistant/provider-defaults) khớp seals trước compiler. Không kiểm lại vector payload nên không tuyên bố hash vector đã được đo trong phiên này; không có thao tác vector write/reindex/publication.
