# Phiên 953 — B2: đo kích thước đầu vào rerank, thêm trace `rerank_input` và xác nhận live

- **Yêu cầu.** Người dùng duyệt backlog B2 theo định nghĩa đã chốt: **đo trước**, chỉ cắt khi số đo cho thấy vượt ngưỡng; nếu cắt thì cắt theo ngân sách **có bảo toàn phần ngữ cảnh + dòng khớp**, không cắt mù (dòng dữ liệu có thể nằm sau phần đầu). Hiện trạng: gửi toàn bộ text ứng viên cho reranker. Kỳ vọng cải thiện: giảm latency rerank khi 20–30 ứng viên, không giảm chất lượng.
- **Môi trường.** Dev API `127.0.0.1:8002`; workspace `ws_39c202a81045`; các collection có index active gồm `col_cf4c14e7c49d` (gen 2), `col_853a15b89a4a` (gen 2), `col_3eb45a408346`, `col_f813d479b31f`, `col_042b8acbb9bb`, `col_a41c290efff5` (gen 2), `col_0daa6e0ed137` (gen 1, 465 chunk). Rerank provider `prv_8f5c1f17c932` — `bge-reranker-v2-m3`, `context_window_tokens=8192`, `max_input_tokens=null`, `capacity_status=configured`. Dev DB vẫn ở migration 0025; `SCHEMA_HEAD=0026` — **không migrate**.
- **Phương pháp.** Đọc chỉ-đọc trace đã lưu trong `chat_turns.result` và metadata chunk của run active để đo phân bố kích thước; sau đó thêm instrumentation trace (không đổi hành vi), chạy regression cô lập và xác nhận một lượt live duy nhất trên API đã restart.

## 1. Đo trước (không sửa mã)

- Quét 15 lượt hội thoại gần nhất, trong đó 12 lượt có trace rerank; số ứng viên mỗi lượt từ 1 đến 18.
- Usage provider đo được: 18 ứng viên = 3.317 token, 453 ms; 3 ứng viên = 689–690 token, 484–515 ms → trong mẫu nhỏ, latency **không** tương quan với kích thước đầu vào.
- Dựng lại `rerank_text` từ dữ liệu thật: batch rerank thật tối đa **617 B/tài liệu** (max_length=512 là giới hạn token, không phải byte). Trên 465 chunk của run active: p50 **542 B**, p90 **752 B**, p99 **1.825 B**, max **3.081 B**; **0/465 vượt 8.192** (và 16.384).
- Guard hiện cộng byte UTF-8 + 64 cho mỗi tài liệu (10.433 "unit" cho 18 tài liệu) trong khi provider đo 3.317 token; reservation settle về token đo thật nên phần giữ chỗ dư chỉ tạm thời, không chặn quota.
- **Kết luận đo:** đầu vào cách trần rất xa; cắt theo ngân sách mù sẽ bỏ dòng dữ liệu/citation nằm sau prefix mà không có lợi ích latency đo được → **không cắt**.

## 2. Thay đổi mã (chỉ instrumentation, giữ nguyên hành vi)

- `backendV1/qnu/domains/modelops/rerank.py`: tách `capacity()`, `parts()`, `measure()`; `budget()` dùng lại các hàm này, giữ nguyên điều kiện `capacity_status ∈ {configured, provisional}` và hai lỗi `rerank_capacity_required`/`rerank_input_limit_exceeded`.
- `backendV1/qnu/domains/knowledge/index/hybrid.py`: thêm một dòng `trace["rerank_input"] = runtime_service.measure(runtime, req.query, documents)` ngay sau `rerank_presentation`. File này đang có thay đổi chưa commit từ trước của người dùng (anchor/fusion/`select_reranked`) — giữ nguyên, không đụng.
- `backendV1/tests/unit/test_rag_modelops_budgets_767.py`: thêm ca `test_rerank_trace_measures_sent_bytes_and_capacity_headroom` — đo đủ khóa trace, ca vượt capacity vẫn bị `rerank_input_limit_exceeded`, ca thiếu capacity vẫn bị `rerank_capacity_required`.

## 3. Kiểm chứng

- Unit file `test_rag_modelops_budgets_767.py`: **16 passed**.
- Cô lập 2 tệp `test_rag_modelops_budgets_767.py` + `test_hybrid_655.py`: **28 passed / 128,62 s**; DB tạm `qnu_v1_test_*` đã drop, sentinel giữ; migration 0026 chỉ áp lên DB tạm.
- Ruff check PASS; `ruff format --check` PASS trên `rerank.py` + test mới (hai khối chưa format trong diff cũ của `hybrid.py` giữ nguyên, không đụng).
- **Restart API dev:** dừng cây tiến trình cũ (PID 5972/22488/5428), chạy lại `uv run --env-file ../.env python -m uvicorn qnu.main:app --host 127.0.0.1 --port 8002` (PID 16868, không reload); health `/openapi.json` = 200.
- **Live đúng 1 lượt** trên `col_cf4c14e7c49d` gen 2 (không re-index): `POST /search` mode `hybrid_rerank`, pin provider `prv_8f5c1f17c932` → **HTTP 200**, 5 hit; rerank 15 ứng viên → 15, **2.512 token, 610 ms**, presentation `qnu.evidence-reading/v1`; `trace.rerank_input` = `{documents: 15, query_bytes: 109, doc_bytes_total: 6.091, doc_bytes_max: 582, guard_bytes_total: 8.686, guard_bytes_max: 755, capacity_tokens: 8.192, capacity_status: "configured", over_capacity_documents: 0}`.
- **Cấu trúc trace:** endpoint `/search` trả trace phẳng (`trace.rerank_input`); trong `/answers`/lượt hội thoại, trace retrieval nằm dưới `trace.retrieval` và được lưu vào `chat_turns.result`.

## 4. Kết luận

- B2 hoàn tất ở mức **đo + instrumentation**: quyết định **không cắt** dựa trên số đo thật (tài liệu lớn nhất 582 B trong lượt live, 3.081 B trong toàn run 465 chunk, so với trần cấu hình 8.192).
- Không đổi hành vi/contract API khác ngoài khóa trace mới; không đổi prompt/index/dữ liệu; không re-index; không migrate dev DB; chưa commit/push.
- Full suite **NOT RUN** (chi phí; baseline FAIL 4/1627 giữ riêng); `NOT RUN ≠ PASS`; một lượt live không đại diện cho mọi corpus.

## 5. Bước tiếp (chờ duyệt)

- **B1** — đọc cả bảng cha cho câu liệt kê/đếm: khi bảng vừa ngân sách, đưa cả bảng từ bản xuất bản đóng băng kèm chứng minh "đủ/thiếu dòng"; thiếu thì báo thiếu; không để LLM tự cộng số.
- **B3** — đo `contextual_search` để quyết định mặc định: A/B bật/tắt trên 97 câu (cần generation index riêng cho nhánh bật), so pass/token/latency.
- **G4** — đo A/B 8 nguồn × 97 câu với model thật; migration 0026 vào dev DB và commit checkpoint vẫn chờ duyệt riêng.
