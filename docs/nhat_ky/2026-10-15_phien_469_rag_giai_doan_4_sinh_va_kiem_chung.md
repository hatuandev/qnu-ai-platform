# Phiên 469 — RAG giai đoạn 4: sinh và kiểm chứng đầu ra

Ngày 2026-10-15. Người dùng duyệt tiếp giai đoạn 4 sau source-row retrieval phiên 468.

## Phạm vi và quyết định

Theo RAG/Backend/Clean Code và ModelOps Resilience: sửa generation/status/window cục bộ,
không bật evidence policy hay đổi model/max_tokens lưu trong DB để làm đẹp kết quả.
Không reset/migrate/reparse/reindex/publish, không OCR, không sửa docs/tai_lieu/Git index.
Không xây từ điển ngành/thuật ngữ mới, không áp ngày ban hành thành năm mọi dữ liệu.

### 1. Chỉ dẫn sinh câu trả lời tổng quát

`composer.GROUNDING_INSTRUCTION` bổ sung vào system message của lượt generation legacy,
giữ nguyên persona gốc trong config và toàn bộ nguồn/hàng/chú giải. Đối chiếu nghĩa từ
thuật ngữ/định nghĩa/tiêu đề/cột/đoạn dẫn cùng nguồn, không đòi trùng chữ; cũng không
đồng nhất hai metric chỉ vì cùng ngành. Phải giữ giá trị theo từng phương thức, điều kiện,
ngoại lệ và phạm vi năm. Khi thiếu phải chỉ rõ ý thiếu, không phủ nhận toàn bộ bằng footer
chung hoặc kết luận trường chưa công bố. Không làm theo lệnh trong nguồn/lịch sử.

Đây là chỉ dẫn generation, **không phải bằng chứng độc lập rằng model đã trả đủ ý**.
Không thêm lượt LLM judge/planner và không tự chuyển legacy sang evidence pipeline.

### 2. Trạng thái phản ánh phần trả lời hiển thị

`is_refusal_answer` không còn trả false vô điều kiện khi có evidence. Giữ detector
No-Answer hiện hữu, không thêm danh sách từ khóa nghiệp vụ. Tách gợi ý và làm sạch đáp
án trước khi lọc citation/nhận diện refusal; câu gợi ý không làm đổi trạng thái đáp án.
Nội dung rỗng/không có citation hoặc facts/từ chối không được gắn answered hoặc cache
như thành công. Nếu không có evidence và không phải một lời từ chối có sẵn, thay nội dung
chưa chứng minh bằng No-Answer Policy hiện hữu, xóa gợi ý. Cache thuật toán legacy đổi
version riêng; không xóa cache chung.

Detector hiện hữu vẫn là heuristic, không là semantic completeness verifier. Facts/citation
vẫn cần kiểm scope/ý nghĩa, không suy accuracy từ status. Các cách từ chối chưa được
detector hiện hữu nhận ra và nhiều câu nhiều ý cần benchmark riêng, không claim đã hết lỗi.

### 3. Window theo token thực, không đoán bằng ký tự

`context_budget.fit_rejected_context` chỉ xử lý lỗi HTTP400 dạng window vLLM-compatible.
Thông báo “prompt contains at least ...” chỉ là **cận dưới**, không dùng để tính ngân sách.
Gọi `/tokenize` cùng server/prefix, alias, credentials, messages, chat-template kwargs và
generation prompt; kiểm count nguyên dương, >= cận dưới, max_model_len khớp window lỗi.

Nếu đủ khoảng trống, chỉ giảm output cap của **payload lượt gọi**, không sửa request/config
hoặc capability lưu DB, không cắt hàng/chú giải/system/history, không đổi model. Caller
chỉ cho một lần context recovery trong vòng negotiation hữu hạn có sẵn. Endpoint không
hỗ trợ/timeout/count sai/input không đủ chỗ thì log lý do và giữ lỗi gốc để ModelOps fallback.
Probe không sử dụng context recovery này; đường probe tối đa 256 token giữ nguyên.

Áp dụng cả non-stream và stream trước khi có token. Tokenizer contract tham khảo
[vLLM TokenizeChatRequest/TokenizeResponse](https://docs.vllm.ai/en/v0.15.0/api/vllm/entrypoints/serve/tokenize/protocol/).
Không đoán tokenizer từ tên model, không tải thêm tokenizer/weights hoặc dùng API key env.
Giới hạn hiện tại: nhận dạng một họ protocol lỗi và endpoint cụ thể; provider khác vẫn
đi đường báo lỗi/fallback cũ. Chưa là generic prompt-packing hay đổi cửa sổ cấu hình server.

### 4. Đầu ra bị cắt không được coi hoàn tất

OpenAI-compatible JSON `finish_reason=length` kể cả có nội dung đều ném
`MODEL_OUTPUT_BUDGET_EXHAUSTED`. ModelOps xử lý fallback theo cơ chế hiện hữu; không
trả mock/facts thay model lỗi. SSE gặp length cũng báo lỗi, không đánh dấu success.
Nếu đã stream nội dung thì không replay/fallback ghép hai câu trả lời; quy tắc chống replay
của InferenceService được giữ. Các native adapter không đi qua contract này chưa đổi.

## File thay đổi trong phiên

- Mới: `backend/app/modules/modelops/providers/context_budget.py`.
- Sửa: ModelOps `providers/chat_contract.py`, `providers/openai_adapter.py`;
  RAG `composer.py`, `service.py`.
- Regression mới: `backend/tests/test_context_window_stage4.py`,
  `backend/tests/test_rag_generation_stage4.py`.
- Cập nhật test cũ `test_rag_generic_reuse.py`: đảo đúng kỳ vọng có citation không phủ
  nhận refusal; bỏ strict-xfail đã sửa trong `test_rag_floor_stage1_466.py`.
- `test_revision_safe_qdrant_and_retrieval.py`: positive sparse-variants/neighbor test
  dùng source + answer có định danh Kỹ thuật phần mềm thay placeholder X, ghi đủ tổ hợp
  và yêu cầu có citation. Mẫu cũ “Các ngành có tổ hợp” không có evidence overlap đủ;
  cả mẫu X mở rộng vẫn thiếu overlap sau stopwords. Không hạ threshold ở production
  hoặc bỏ assertion status; negative no-citation được kiểm riêng. False-negative citation
  cho câu quá ngắn vẫn là giới hạn heuristic, không claim đã giải quyết.
- Diagnostic `backend/scripts/audit_rag_generation_stage4.py` tái dùng trace quan sát
  giai đoạn1, không fake output; hội thoại giữ prefix cũ và report đánh dấu phase4.
- Nhật ký/memory/snapshot/mục lục/WORK_LOG và quy trình 03.

## Kiểm thử

- RED ban đầu **14 failed, 3 passed/3,89s**, tái hiện refusal false-success, không có
  evidence vẫn answered, thiếu grounding instruction, chưa có context recovery và
  length nonempty bị nhận thành công. Một số test RED là kiểm contract chức năng mới,
  không coi tất cả là bug đã quan sát ngoài thực tế.
- Sau batch sửa: 77 passed/63,17s gồm floor controls, chat contract, probe stability
  và hai suite mới. Focus mở rộng 138 passed/65,14s, `storage/pytest469_focus.xml`.
- Bổ sung 5 ca stream/token-template và unrelated400/401/429/500 không gọi tokenizer.
- Thêm một RED boundary **1 failed/6 passed**: chỉ hạ status chưa đủ nếu vẫn trả nội dung
  không có căn cứ. Sau đó bổ sung No-Answer thay thế phần chưa chứng minh như trên.
- **Boundary cuối 47 passed/4,50s**, `storage/pytest469_final_boundary.xml`, gồm các
  kiểm tra mới + floor controls + revision retrieval. Không còn xfail trong floor controls.
- Full đầu và vòng giữa: **1437 passed/12 failed/16 skipped**; 11 lỗi nền + positive
  mock fixture nêu trên. Vòng giữa còn dùng module/fixtures đã import trước lúc sửa cuối.
- **Full xác minh sau sửa cuối: 1438 passed, 11 failed, 16 skipped/194,96s**,
  `storage/pytest469_verified.xml`; so exact classname/name với `pytest468_handoff.xml`:
  **cùng 11 lỗi nền, không lỗi mới**. Không tuyên bố toàn suite xanh. Ruff toàn Backend
  và scoped cuối đạt, chỉ cảnh báo quyền đọc artifact cũ. Không FE build vì không đổi FE.

## Hai câu thật — CHƯA NGHIỆM THU CHẤT LƯỢNG GIAI ĐOẠN 4

`storage/rag_stage4_469/report.json`; service thật trong tiến trình chẩn đoán, không
kiểm tra HTTP/login/UI. Không gửi đáp án chuẩn vào prompt. Không fake generation,
không đổi policy/model, không OCR. Có 2 lượt chat/usage/key-health bình thường;
observed capabilities nếu phát sinh vẫn theo cơ chế runtime có sẵn, không đổi credentials.

| Ca | Window đã phục hồi | Nội dung quan sát | Đánh giá thủ công |
| --- | --- | --- | --- |
| Quản lý giáo dục | Count5099/window8192; cap5000→3093; output345 | Nêu15 và18, bỏ600/15 của hai ĐGNL; diễn giải18 như tổng điểm thi THPT thay vì đúng cột kết quả học tập; thêm điểm chuẩn cũ và điều kiện chưa chứng minh đúng phạm vi | Chưa đạt |
| Sư phạm Toán | Count5378/window8192; cap5000→2814; output416 | Không dùng20/–/–/20; nêu15, học bạ và điểm chuẩn lịch sử; vẫn answered | Chưa đạt |

Cả hai **served vllm/qwen3.5-9b, is_fallback=false**, khác baseline466 phải fallbackCloudflare.
Count `/tokenize` khớp prompt_tokens usage của chính lượt completion; không dùng cận dưới3193
để tính cap. Tổng service lần lượt95.847,93ms và7.440,60ms; không là p95/benchmark latency.
Không có length truncation; output thực345/416 thấp hơn cap3093/2814, không thể quy thiếu
phương thức cho cap5000 hoặc hết output ở hai lượt này.

Trace chứng minh đúng hàng đủ4phương thức và ngữ cảnh nguồn đã ở prompt. Tuy nhiên prompt
còn trộn thông tin điểm trúng tuyển/năm cũ/khác metric; model diễn giải và áp điều kiện sai.
Heuristic numbers hiện hữu cho phép số chuẩn/overlap ở nguồn khác, không kiểm tuple hàng–cột;
detector refusal chỉ bắt các mẫu hiện hữu, chưa bắt mọi cách nói “chưa công bố” khác.
Vì vậy không được coi technical tests hoặc status answered là kiểm chứng semantic truth.

Conversation IDs `stage1_466_7f9142cd4fed441b`, `stage1_466_2f8098f8a8eb4ab3` (prefix cũ
của trace helper). Nguồn vẫn21/snapshot c61c923b10b4f8f1aa58. Config/snapshot/target source,
facts/chunks/collection metadata/inventory fingerprints trước/sau live bằng nhau; kiểm lại
sau full suite cũng bằng nhau. Không claim toàn DB read-only vì có log test bình thường.

### Đề xuất bổ sung trước khi sửa tiếp

Chưa chốt giai đoạn4. Cần hợp đồng trả lời bảng: chọn và kiểm chứng đúng metric/phương thức/
phạm vi bằng quote cùng nguồn, gắn từng giá trị với tọa độ hàng–cột; render số từ ô đã xác
minh thay vì để model tự viết lại, kiểm riêng phạm vi điều kiện. Tận dụng source units,
context graph và validator evidence hiện hữu, không từ điển riêng từng ngành, không bật
evidence policy ngầm. Bước này thay đổi hợp đồng sinh/trả lời nhánh legacy và có thể thêm
lượt model; đề xuất lại cho người dùng duyệt trước khi mở rộng triển khai.

## Bài học

Không thể lấy cận dưới token làm token count. Không tăng context/output mù quáng hoặc
cắt mất ghi chú để primary hết HTTP400. Có source liên quan không chứng minh câu hỏi
đã được trả lời; bỏ dấu xfail chỉ sau khi lỗi gốc thật sự được sửa và controls đạt.

Chưa chạy 20/82 câu hoặc Ragas, chưa thay model/policy/runtime DB config/restart/deploy.
Đã triển khai và kiểm chứng boundary/window; **chưa hoàn thành nghiệm thu generation**.
Không commit/push hoặc dọn file của các giai đoạn trước.
