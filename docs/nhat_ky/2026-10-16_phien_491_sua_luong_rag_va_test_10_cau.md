# Phiên 491 — Sửa theo batch, kiểm chứng lại 10 câu

## Yêu cầu và phạm vi

Người dùng chọn làm từng đợt rồi kiểm chứng 10 câu, không chạy bộ82.
Đợt này tập trung **từ chối sớm ở bảng/fact và kiểm tra số**, không coi cả bốn
nhóm lỗi490 đã được sửa. Dùng skill clean-code/backend/RAG pipeline/evaluation.
Không thêm thuật toán mới, không sửa nguồn/OCR, không reindex, không bật preset
TopK hoặc quy tắc tính điểm, không migration/restart/push/deploy.

## Thay đổi

- `rag/prose_fallback.py`: khi structured route trả missing và chưa có claim/cell
  được xác minh, kiểm tra thêm đoạn văn canonical trong **cùng snapshot xuất bản**.
  Tái dùng BM25, reranker theo cấu hình, passage-ID binding và independent semantic
  audit hiện có. Không biến bảng vừa bị bác thành văn xuôi để né kiểm chứng.
  Chỉ xuất đáp án nếu có claim và audit complete, không conflict; lỗi provider/DB/
  hợp đồng model đi xuyên, không trở thành “không có dữ liệu”. Giữ source preferences.
- `rag/service.py`: đấu nối ở missing fact/table và numeric failure. Không ghi đè
  đáp án supported/partial, conflict hay scope ambiguous bằng prose fallback.
  Numeric failure không thể phục hồi trả lý do `NUMERIC_GROUNDING_FAILED` cùng
  thông báo chưa chốt được số liệu; không dùng mẫu khẳng định kho thiếu dữ liệu.
  Cache version thêm `prose-recovery-v1` để không tái dùng đáp án của logic cũ.
- `rag/citation_guard.py`: so sánh **giá trị số đầy đủ** thay vì substring hai chiều,
  chuẩn hóa dấu phân cách/zero decimal. Bỏ allowlist số tuyển sinh và việc coi query/
  system prompt là chứng cứ. Giữ ranh giới gate multi-digit hiện hữu; số đếm/ordinal
  một chữ số không được kiểm chứng ngữ nghĩa chỉ bằng gate này. Đây **không phải**
  kiểm chứng metric/year/điều kiện và chưa sửa được các nhầm lẫn đó.
- Bổ sung `tests/test_rag_prose_recovery_491.py`; fixture ở các test488,
  `test_revision_safe_qdrant_and_retrieval.py`, `test_temporal_fact_contract.py`
  khai báo rõ canonical rỗng khi kiểm tra no-evidence. Giữ assertion chặn số bịa,
  không lấy dữ liệu2025 trả cho2026, lỗi hạ tầng không giả thành câu trả lời.

### Ngân sách bước phục hồi

Lượt thật đầu phát hiện model server báo **8192 token** và request structured
đòi 4000 output trong khi input vượt phần còn lại. Bước phục hồi nay giữ tối đa
3body units,6000ký tự context và1600output token cho các subcall kiểm chứng;
header/dependency vẫn nguyên nhóm nên số block có thể lớn hơn3. Ngân sách này là
giới hạn riêng bước phục hồi, **không đổi max_tokens5000 hay config trợ lý trong DB**.
6000ký tự không được tuyên bố tương đương một số token cố định.

## 10 câu được chọn và kết quả cuối

Chọn Q03/Q05/Q08/Q09/Q10/Q11/Q14/Q17/Q19/Q20 từ bộ490, chỉ profile legacy đang
dùng. Có câu sửa trực tiếp, control giữ nguyên và negative/rule-disabled. Không phải
10câu ngẫu nhiên hay phép đo toànapp. Chạy ở `RagService`, chưa HTTP/SSE/UI và chưa
kiểm chứng chuỗi hội thoại thật trong bộ10này.

**AI source-review cuối:3đạt /1một phần /4không đạt /2lỗi thực thi. Acceptance FAIL.**
Không cộng answered thành đúng. Cùng10câu ở baseline490 là3đạt/1partial/6fail,
nên **chưa có cải thiện tổng số câu đạt** và không có cơ sở nói bản này ổn định hơn toàn diện.

| Câu | Chấm cuối | Ghi nhận |
| --- | --- | --- |
| Q03 Tổng chỉ tiêu2026 | Lỗi | `ALL_PROVIDERS_UNAVAILABLE`; có rerank timeout trước đó, fallback ngoài bị chặn. Không đủ trace để quy nguyên nhân primary cho mạng/hardware. |
| Q05 Phương thức | Không đạt | Đúng danh sách chính nhưng lại thêm cột chỉ tiêu, nhầm số ngưỡng20/15/600/19/16 thành chỉ tiêu. Luồng synthesis/fact relevance còn lỗi. |
| Q08 Giáo viên/PT4 | Không đạt | Mở đầu đúng, còn nói một số ngành giáo viên chỉ xét học bạ và kéo bảng metric không liên quan. |
| Q09 Tiếng Anh nhân2 | Đạt | Trích đúng, gọn: không nhân hệ số hai; phục hồi thành công từ `ROW_SELECTION_MISSING` sang `VERIFIED_PROSE_FALLBACK`. |
| Q10 Nguyên tắc quy đổi | Lỗi | `EVIDENCE_MODEL_CONTRACT_INVALID` ở SourceAnswerAudit sau hai attempt hiện hữu; không nuốt lỗi để xuất đáp án giả. |
| Q11 KV1 | Không đạt | Đã trả0,75 và công thức giảm, nhưng thêm khẳng định sai rằng cả ưu tiên+thưởng bị giới hạn10%; không chấm đạt vì số chính đúng. |
| Q14 Tổ hợp Sư phạm Toán | Một phần | Giữ conflict Tin/Tín và citations; chưa chốt phần chung gọn, không âm thầm sửa OCR. |
| Q17 Điểm lịch sử | Không đạt | `ROW_AUDIT_REJECTED` còn nguyên; có bảng lịch sử trong nguồn, prose fallback không được dùng để né audit ô. |
| Q19 Chỉ tiêu2027 | Đạt | Không lấy số2026 hoặc năm học2026–2027 thay chỉ tiêu tuyển sinh2027. |
| Q20 Công cụ tính điểm | Đạt | Từ chối đúng do chưa có ruleactive; không tự kích hoạt hoặc tự tính số chính thức. |

Kết quả Q09 là cải thiện xác định được; Q11 chỉ khôi phục ý chính nhưng chưa đúng
toàn bộ. Q05 so với baseline có thể sai khác do sinh model temperature0.2; không
quy mọi sai khác thành tác động nhân quả của thay đổi code.

## Thí nghiệm, lỗi phát hiện và bảo toàn dữ liệu

- 22nguồn và snapshot `b7456674dcc9b51ce736`; các fingerprint config/metadata/
  snapshot/sources của cả ba lượt đều unchanged, khớp490. Không đổi profile DB.
- **10câu khác nhau, có3lượt chạy trọn cùng bộ10 trong quá trình sửa**; không chỉ
  chạy10request. Giữ đủ30attempts và lỗi tiền kiểm, không xóa/rerun chọn đáp án đẹp:
  - `storage/quality_491/results.json`: lượt đầu lỗi context8k,1answered/3insufficient/6error.
  - `storage/quality_491/final/results.json`: sau thu gọn context,4answered/6insufficient;
    phát hiện chọn bản chỉ tiêu đầu mùa và gate một chữ số quá rộng, đã sửa tiếp.
  - `storage/quality_491/acceptance/results.json`: code đã chốt,4answered/
    4insufficient/2error; bảng chấm ở trên áp dụng **toàn bộ lượt này**.
- Cache bypass đọc/ghi; không dùng cache làm đáp án. Không ghi conversation/gap;
  ModelOps usage/capability có thể ghi như luồng thường. Không gọi là zero-write DB.
- Chỉ model nội bộ `qwen3.5-9b`/provider được user cho phép. Lượt cuối có21generate
  thành công đều internal primary, không model fallback ngoài. Một lần định dựng
  adapter Cloudflare bị runner chặn **trước khi gửi**; không gửi corpus ra ngoài.
- Full Pytest chạy đồng thời với lượt model; không dùng latency lượt này để tuyên
  bố nhanh/chậm tốt hơn. Không reset circuit, đổi provider hoặc sửa credential.
- `review.json` lưu nhãn, raw-result SHA và hash3file ứng dụng đã sửa; canonical
  inventory/log nằm riêng trong storage, không đưa corpus hay prompt vào Git.
- Nhãn là Codex đối chiếu canonical đã chốt, chưa phải gold cán bộ tuyển sinh duyệt;
  không đối chiếu ảnh toàn bộ PDF và không có significance/recall vàng.

## Kiểm chứng mã

Ruff có phạm vi đạt. Nhóm hồi quy cuối **115pass** trong4,38giây, gồm fallback,
numeric, source binding, year/snapshot, generation và các test cũ liên quan.
Không sửa assertion để cho số bịa/sai năm qua gate.

Full gate đầu hoàn tất: **1724pass/13fail/17skip**, tổngFAIL, log
`storage/quality_491/acceptance-full.log`/XML. Exact11IDs baseline489 vẫn có;
2lỗi mới là fixture chưa mô tả canonical I/O (`coroutine is not iterable`), không
phải lỗi tự lấy2025 thay2026 hoặc chấp nhận số29,9. Đã cập nhật fixture nguồn rỗng,
giữ assertion gốc và thêm reason rõ; cả nhóm115test thực chạy đạt sau đó.
Hai lượt full trước bị dừng do tiếp tục sửa lỗi phát hiện bởi model, không tính PASS.

Gate full cuối sau fixture: **1726pass/11fail/17skip**, exit1 trong192,08giây,
tổng **FAIL**. XML đối chiếu exact test IDs với489: cùng11lỗi,0thêm/0bớt.
Artifacts `storage/quality_491/verified-full.log`/XML; không gọi toàn suite PASS.
Không chạy lại82câu,
không FEbuild vì không sửa frontend, không test UI/HTTP live.

Lệnh chính (cwd backend, Python3.12 trong venv):

- `ruff check` trên3fileapp và4filetest liên quan.
- `python -X utf8 -m pytest <7file trọng tâm> -q` →115pass.
- `python -X utf8 -m storage.quality_491.run_quality --output storage/quality_491/acceptance`
  →exit0 của runner,10records nhưng2exception; **không gọi10/10PASS**.
- `python -X utf8 -m pytest -v --junitxml=storage/quality_491/verified-full.xml --basetemp=storage/quality_491/verified-pytest-temp`.

Kiểm tra cuối: source code hash khớp lượt10cuối; source/config fingerprints giữ
nguyên; UTF-8 không BOM/LF và liên kết tài liệu491 đạt; `git diff --check` đạt
(có cảnh báo autocrlf Git). Chỉ file thuộc scope491 được bổ sung vào các sửa đổi
chưa commit vốn có; không stage/commit/push artifacts nguồn/runtime.

## Đợt tiếp theo đề nghị

1. Loại fact/bảng không cùng metric khỏi prompt trước synthesis, đặc biệt câu hỏi
   phương thức/policy không được nhận số ngưỡng như quota; kiểm chứng từng claim
   về đối tượng/đơn vị/đợt/năm. Đây là lỗi chính Q05/Q08/Q11, không giải quyết bằng K.
2. Sửa hợp đồng audit và chẩn đoán primary ở Q03/Q10; không tăng retry hoặc bật
   provider ngoài. Kiểm tra supersession trước khi chốt chỉ tiêu đầu mùa.
3. Sau đó mới xử lý audit bảng lịch sử/liệt kê và giải thích hội thoại. Giữ nhịp
   code theo batch rồi test cùng10câu có control, không mở lại full82.

Không tuyên bố đợt2 đã hoàn tất cả4nhóm hoặc đạt chất lượng nghiệm thu.
