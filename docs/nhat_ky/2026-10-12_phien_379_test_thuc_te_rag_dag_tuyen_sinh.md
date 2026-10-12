# Phiên #379 — Kiểm thử thực tế RAG/DAG tuyển sinh sau xuất bản

- Ngày: 2026-10-12.
- Yêu cầu: Đọc PDF tuyển sinh 2026 và kiểm tra trợ lý tuyển sinh trên kho đã xuất bản.
- Skills PDF/RAG/chatbot: đối chiếu nguồn và trang, thử câu có/không có căn cứ, theo dõi ModelOps và trace DAG. Chỉ test/chẩn đoán, không sửa runtime hoặc cấu hình.

## Dữ liệu đối chiếu

- PDF tại `C:/Users/AnhTuan/Downloads/Thong tin tuyen sinh dai hoc 2026_Lan2-1.pdf`: 14 trang, đã đọc text các trang; render/kiểm tra trực quan trang 9 và 12.
- Trang 2: chỉ tiêu dự kiến 4800; PT2/PT3 không áp dụng ngành đào tạo giáo viên.
- Trang 9: IELTS 6.0 → 9.0 điểm, đăng ký hệ thống Bộ 02/7/2026–14/7/2026.
- Trang 12: CNTT 7480201 điểm 2024/2025 = 16.5/21.5. Không có điểm chuẩn chính thức năm 2026.
- Kho đã xuất bản bản DOCX tương ứng (`bnd_7654b2810a0a`), không phải upload PDF này trong phiên. Những nội dung kiểm tra trên trùng nhau giữa PDF đối chiếu và Markdown DOCX truy xuất; chưa xác minh toàn bộ hai tệp tương đương tuyệt đối.
- Active generation `vg_8b7b06c28e51`, provider `prov_rtx5090_vllm`, bge-m3 1024d; snapshot epoch3 có 3 binding/index active. HTTP search lấy được nội dung 4800/trang2 cùng binding/index/source revision thật.

## Kết quả đường đang dùng

8 câu gọi HTTP `/assistants/admissions/chat`, không mock, từng câu độc lập:

| Câu | Kỳ vọng | Kết quả hiện tại |
|---|---|---|
| Tổng chỉ tiêu 2026 | 4800 + nguồn trang2 | insufficient_context, không citations |
| Ngành giáo viên có PT2/PT3 không | Không, trang2 | insufficient_context |
| IELTS6.0 | 9.0, trang9 | insufficient_context |
| Lịch đăng ký Bộ | 02/7–14/7/2026 | insufficient_context |
| Điểm CNTT2024/2025 | 16.5/21.5 | insufficient_context |
| Điểm chính thức2026 | Không suy đoán | insufficient_context; đường này đang loại mọi context nên chưa chứng minh safety hoạt động đúng |
| Xin chào | Nhánh giao tiếp | answered, câu chào tự nhiên |
| Chào + hỏi chỉ tiêu | Nhánh tra cứu | insufficient_context; routing không bị lời chào chiếm nhánh |

- Các câu tri thức khoảng 2.9–3.6s, greeting 0.98s. Không coi HTTP200 là test chất lượng đạt.
- Browser FE tại `/chat/admissions`: nhập/gửi câu chỉ tiêu qua streaming, UI hoàn tất 3117ms và hiện No-answer sai tương tự API; không có trích dẫn.
- Trace execution chỉ tiêu `5235ac48-5d5b-41ae-afd5-f3a7763feb87`: input → condition_route → query_rewrite → knowledge_answer (0 contexts/insufficient_context) → citation_guard ungrounded → no_answer_output. Scope persisted đúng tenant_qnu/workspace_qnu/col_admissions.

## P1 — Reranker loại hết ngữ cảnh dù dữ liệu đúng

- Runtime profile trợ lý có reranker `prov_rtx5090_vllm`, `bge-reranker-v2-m3`, threshold0.4.
- `reranker.py` hai nhánh Cloudflare/vLLM lọc `getattr(c, "score", 0.0) >= score_threshold` (dòng217/235 tại thời điểm rà).
- `FusionCandidate` không có thuộc tính score; response provider relevance_score chỉ dùng tính hạng, không bảo toàn vào candidate. Kết quả lọc mọi candidate thành0, loại hết khi threshold>0.
- HTTP `/rag/ask` cùng câu chỉ tiêu, cùng provider/model: threshold0.4 → 0contexts/no-answer; threshold0 (chỉ trong request chẩn đoán, không cập nhật DB) → 5contexts/4citations và đúng4800.
- Server AI gọi trực tiếp ngoài sandbox/Tailscale: `/v1/rerank` HTTP200, relevant text score0.8970432281, unrelated0.0000892425. Sandbox gọi trực tiếp bị ConnectError, không nhầm lỗi sandbox với server outage.
- Đề xuất: lưu trường cross-encoder score riêng trên candidate, threshold trên relevance_score thực; giữ RRF score để xếp hạng, không trộn scale. Khi provider lỗi fallback RRF phải có trạng thái degraded rõ, không coi RRF hoặc missing score là xác suất. Test regression threshold>0 trước fix, rồi chạy lại chính luồng trợ lý/browser.

## Các vấn đề tiếp theo sau khi gỡ nguyên nhân P1

Request chẩn đoán `/rag/ask` threshold0, không đổi DB:

| Câu | Nội dung | Lưu ý |
|---|---|---|
| Chỉ tiêu | 4800 đúng | Một lần trả bảng dư thừa, lần khác trả ngắn gọn |
| IELTS6.0 | 9.0 đúng | Kèm citations không liên quan như quy chế thạc sĩ trang21 |
| Lịch Bộ | 02/7–14/7/2026 đúng | Có citations thừa trang1/10 |
| CNTT2024/2025 | 16.5/21.5 đúng | Nguồn chính trang12 đúng; lẫn quy chế học vụ trang19/22 |
| Điểm chính thức2026 | Không bịa số, nói chưa đề cập | status vẫn answered với5citations: chưa chuẩn No-answer contract |

### P2 — Trích dẫn chưa đúng trọng tâm/tên nguồn

- `citation_guard.build_citations` ưu tiên section làm title trước document_title; title có dấu Markdown/dòng bảng thô, không phải tên văn bản.
- Lọc evidence theo giao nhau3từ có thể giữ nguồn khác với cùng từ/mã ngành, chưa chứng minh nguồn hỗ trợ đúng thuộc tính/năm trong câu trả lời.
- Đề xuất title ưu tiên tên văn bản, section riêng; lọc citations theo evidence được sử dụng cho claim/thực thể/năm, không chỉ overlap chung.

### P2 — No-answer status không khớp câu trả lời

- Câu điểm chuẩn2026 trả lời “không được đề cập trong tài liệu” nhưng statusanswered và cócitations. Lần này không bịa số, tuy nhiên gate/DAG/UI có thể coi đó là grounded answer.
- Đề xuất xác định thiếu bằng chứng cho yêu cầu bằng evidence coverage, thay vì vá từ điển câu từ chối; statusinsufficient_context và không gắn nguồn không hỗ trợ như câu có căn cứ.

### P2 — ModelOps/audit chưa phản ánh model thực tế

- Cấu hình assistant còn primarygpt-4o-mini/fallbackgemini-2.5-flash-lite, providerpreferrednull; hai providerOpenAI/Gemini hiện disabled.
- Các inference thành công thực tế trong log dùng Cloudflare `@cf/meta/llama-3.1-8b-instruct`; log tổng hợp `qnu_workflow` vẫn ghi gpt-4o-mini, tokens ước lượng. Không thể lấy log wrapper đó làm bằng chứng model đã gọi.
- Đề xuất thông tin actual provider/model/token lấy từ kết quả ModelOps thay vì primary của policy; cấu hình primary/fallback nên do người dùng chọn model đang hoạt động, không tự đổi DB trong phiên test.

## Giới hạn và tác động

- Đã chạy: 1HTTP search, 8HTTPassistantchat, 7HTTPRAGask (gồm chẩn đoán threshold), 1browserchat/streaming, 1directreranker thật; đọc traces/DB/provider metadata, không đọc/hiển thị secrets.
- Test thật sinh các conversation/workflow traces/usage/quota/keylease/cache/gap theo hành vi ứng dụng; giữ audit, không xóa lịch sử hay reset dữ liệu. Không upload/parse/index/publish lại tài liệu, không sửa provider/assistant/workflow/key/qnu-sso.
- Chưa Ragas50câu, benchmark tải, multi-turn, outage failover thực, injection hoặc mọi nhánhDAG. Không chạy lại pytest/build vì không sửa mã nguồn ứng dụng.
- Kết luận: dữ liệu đã truy xuất được và RAG trả đúng các đáp án mẫu khi bỏ ngưỡng lỗi trong request; trợ lý/DAG cấu hình hiện tại chưa đạt, ưu tiên sửaP1 rồi kiểm tra lại cácP2.
