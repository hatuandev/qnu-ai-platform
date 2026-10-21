# Context586 — Chạy lại đủ 6 câu lỗi với timeout Luna 30 giây

**Đã chạy đủ P01, P05, P07, P09, P10 và P16: 2 PASS, 4 FAIL.** Giữ nguyên mã ứng dụng, model, bộ câu/rubric và nguồn/index PDF staging. Không sửa lỗi hoặc thử lặp từng câu để chọn kết quả tốt hơn.

| Câu | Kết quả mới | Thời gian toàn luồng | Đối chiếu rubric |
| --- | --- | --- | --- |
| P01 | FAIL | 28.33 giây | Vẫn từ chối VISIBLE_ANSWER_NOT_SUPPORTED, không nêu được tính chất mô phỏng/không áp dụng thực tế theo rubric. |
| P05 | PASS | 27.44 giây | Nêu đúng Ước tính2027 là dự kiến lập kế hoạch, không nghiệm thu; quy ước không áp sang Ghi nhận2025/2026. Các quote exact của chú thích nguồn hỗ trợ đầy đủ. |
| P07 | FAIL | 61.23 giây | Đúng phương thức/30ngày/không miễn an toàn/không nhóm A nhưng vẫn bỏ điều kiện cơ sở tiếp nhận tạm đóng, có nhật ký và xác nhận giảng viên cùng kỳ; rubric chưa đạt dù status answered. |
| P09 | FAIL | 0.66 giây | ROW_ANSWER_SOURCE_INVALID |
| P10 | FAIL | 0.69 giây | ROW_ANSWER_SOURCE_INVALID |
| P16 | PASS | 34.4 giây | Đủ điều kiện thiếu biến/chứng cứ thì Chưa đủ điều kiện tính, không kết luận Đạt/Cần khắc phục và không gán0; các câu nguồn và sáu citations hỗ trợ. |

P05 đạt trong lượt này dù không có sửa mã; lượt583 từng bị bộ kiểm chứng chặn khi đã lấy được chú thích. Một lần đạt chưa chứng minh lỗi lựa chọn/kiểm chứng đã được khắc phục ổn định. P16 tiếp tục đạt sau lượt585, không còn lỗi timeout trong hai lượt thử này. P07 vẫn thiếu điều kiện dù API/service trả trạng thái answered; citation hợp lệ không thay cho câu trả lời đầy đủ.

## Phạm vi và điều kiện đo

- Timeout provider Luna vẫn **30 giây**, đã đọc lại DB trước và sau. Đây là timeout mỗi lần gọi provider, không phải tổng thời gian RAG gồm nhiều bước.
- Actual model `gpt-6-luna`: **21 usage / 21 success, 0 fallback, không có model ngoài Luna**. Cấu hình fallback Qwen giữ nguyên; scope test chỉ Luna như583/585 để bảo đảm so sánh cùng model.
- Cùng binding `bnd_12190866d5ec`, source `ks_rev_fef00606f91f`, index `idx_rev_bba8c17700d0`, generation `vg_a6e3190d11af`; 327 điểm staging, 0 retrievable, chưa có active index/publication.
- Câu hỏi, rubric, expected spans và mapping được lấy nguyên từ frozen64 Context583, chỉ chọn đúng 6 ID đã lỗi; freeze trước khi inference. Sáu câu là các session độc lập, không mượn đáp án lượt trước làm history.
- Existing authenticated candidate snapshot/server validators, persisted assistant profile, real RAG retrieval/reranker/LLM; không mock, không dependency override hoặc bật lifespan app. Đây là test RAG service staging, không phải published assistant HTTP/UI E2E.
- Chấm mới từng câu theo nội dung nguồn/rubric, không gọi judge LLM. Nhãn vẫn agent-source-checked, chưa independent human holdout.

## Bằng chứng và kiểm tra sau chạy

- Đủ đúng 6/6 ID, không thiếu/trùng; mỗi câu gửi một lần. Runner exit0; scorer **exit1 vì còn 4 câu FAIL**.
- **17/17 citations** đúng binding/index/source revision, canonical hash, span và quote. Các câu có lỗi hoặc thiếu điều kiện vẫn FAIL, không bỏ khỏi mẫu.
- Tokens ghi nhận từ usage thành công: input 112883, output 6034; max prompt 9131. Số usage không được coi là tổng mọi HTTP attempt; không ước lượng chi phí khi chưa đối soát giá.
- Hash app/tests, source/assistant/provider-config/index/generation row seals và count/payload Qdrant khớp trước/sau. Local development; DB/MinIO/Qdrant loopback được kiểm trước khi chạy.
- Postcheck PASS: timeout30, index staging ready, chưa publication, 0 thread/message benchmark tồn lại. Không tạo gap persisted hoặc DB/Storage runtime cần dọn; giữ inference usage và artifacts benchmark để audit.
- Không cập nhật model/config trong586; lần đổi timeout được người dùng giao và lưu riêng ở585. Không app fix, migration, reparse, reindex, publish, restart, deploy, commit/push hoặc hạ Quality Gate.
- **Không chạy lại toàn64**, không ghép 2 ca thử lại thành điểm benchmark mới. Kết quả583 gốc giữ **54/60 = 90%**, social4/4. Full Pytest/FE build/ablation hiện tại NOT RUN; 18 FAIL của full582 vẫn là kết quả lịch sử.

Lệnh thật, cwd repository, `backend/.venv/Scripts/python.exe`: `.antigravity-bridge/validation/context586_prepare.py` exit0; `context586_run.py` exit0; `context586_postcheck.py` exit0; `context586_score.py` exit1. Bắt đầu/kết thúc UTC: 2026-10-21T07:48:35.449711+00:00 → 2026-10-21T07:51:11.595273+00:00.

Bằng chứng riêng, ignored: `backend/storage/context586/` có manifest, raw responses, adjudications, labels-final, summary, usage, single-model verification, run-complete và postcheck. Không chép corpus/private prompt/credential vào Git.

[Phân tích nguyên nhân6ca](../context584/SIX_FAILURE_ROOT_CAUSE.md) · [Timeout30 và thử riêngP16](../context585/TIMEOUT30_P16_RETEST.md) · [Benchmark64 gốc](../context583/PDF_BENCHMARK64_REPORT.md).
