# Context592 — Tham chiếu hội thoại có nguồn và sửa lỗi có giới hạn

## Kết quả

Ngày 22/10/2026, sửa hai điểm người dùng yêu cầu: LLM tách tham chiếu đúng vai
trò và pipeline có một lượt sửa khi tham chiếu không hợp lệ. Giữ model, nguồn,
Quality Gate, index/vector và publication. Không reindex/restart/deploy/commit/push.

- Regression cuối: **269 PASS**, Ruff 3 file PASS, exit 0.
- Full backend: **3,139 PASS / 18 FAIL nền / 17 SKIP**, exit 1;
  23 subtests PASS. **16 test mới PASS** so với Context591;
  không thiếu ID, không có lỗi mới hoặc nguyên nhân lỗi nền đổi. Full vẫn FAIL.
- Live follow-up cuối: **8/8**, ca chưa đạt: không có.
  Citation **8/8** exact nguồn/hash/revision/span;
  0 lỗi runtime. F03 trạng thái `answered`, trả đúng **75 SV** năm 2026 cho
  mã AM-0201, trích Bảng 1 trang 6 của PDF.
- ModelOps thật: 4 usage records, 8,835 input và
  1,549 output tokens; 0 fallback.
- Postcheck PASS; nguồn/cấu hình/revision cũ/vector/code giữ nguyên; không còn
  benchmark threads/messages/gaps. Hai DB test đã dọn theo owner nonce.

**Không chạy lại toàn bộ 64 câu trong Context592.** 59/60 tri thức, xã giao4/4
là kết quả lịch sử Context591. Không ghép F03 mới vào bộ cũ để công bố 60/60.
Lượt này tái sử dụng đúng tám câu F01–F08, rubric/gold/phiên hội thoại của bộ đó.

## Context của LLM có vai trò gì?

Context hội thoại cung cấp đối tượng và thời gian mà các từ “đó”, “cùng năm”
đang nhắc tới. Context tài liệu cung cấp header, chú thích, điều kiện và ngoại
lệ để xác định quan hệ trong nguồn. Cả hai cần đúng phần liên quan và giữ nguồn.
Dung lượng context window chỉ đặt giới hạn sức chứa; nó không tự chứng minh
model đã chọn đúng quan hệ hoặc trích đúng căn cứ.

F03 trước đó đã có lịch sử F01/F02. Model xác định đúng mã/năm nhưng ghép vị trí
bảng với đại lượng thành một nhãn chưa được quote chứng minh. Đây là khoảng hở
hợp đồng/kiểm chứng ngữ cảnh, chưa có bằng chứng cần tăng context window để sửa.
Không đổi model hoặc tham số context. Mỗi tham chiếu hiện là một giá trị nguyên
văn, một source_turn của người dùng và một quote chứa đủ giá trị đó.
Lượt cuối quan sát 2193–2223
input tokens mỗi lần lập ngữ cảnh; đây là usage thực, không phải ước lượng dung
lượng context. Không có lỗi context-window trong lượt này.

## Thiết kế và file thay đổi

- `intent_contracts.py`: thêm hai vai trò tương thích ngược `source_locator`
  và `metric`, giữ `topic` cũ. Mọi vai trò đều qua literal quote/value/query
  checks. Tách `referent_errors` để cung cấp mã lỗi có field/index; không log
  standalone query, đoạn trích hoặc giá trị riêng trong diagnostic mới.
- `conversation_resolution.py`: chỉ dẫn tách vai trò; current metric được kiểm
  với câu hỏi độc lập, giữ mọi guard mã/năm/phủ định/đối tượng đã có. Một đề xuất
  followup/filter không đạt được sửa một lần từ đúng lịch sử người dùng, cùng
  thời hạn 20 giây và tối đa hai structured calls, mỗi call max_attempts=1.
- Lượt sửa nhận đề xuất bị từ chối như dữ liệu không tin cậy và mã lỗi server.
  Phải giữ mode/intent và qua lại toàn bộ kiểm chứng. Genuinely ambiguous vẫn
  được clarify; đổi sang independent/social không mở đường vượt guard.
- Lỗi provider/quyền/quota và hủy tác vụ không kích hoạt vòng sửa này. Không
  reset timeout hoặc mở rộng model/fallback/quyền. Policy retry nội bộ ModelOps
  giữ nguyên. Không có credential/config/schema DB/frontend thay đổi.
- `test_context_reference_repair_592.py`: fixture tổng quát dùng mã/năm khác
  benchmark; có literal roles, nhãn ghép sai, stale year/metric, mất số 0,
  giá trị bịa, mất phủ định, đổi mode, shared deadline/cancellation, provider
  errors và mã lỗi diagnostic không chứa giá trị riêng. Không vá riêng F03.
- [Quy trình cập nhật](../../quy_trinh/16_trang_tri_thuc_va_doc_nguon.md).

Tham chiếu hội thoại chỉ diễn giải câu hỏi, không thành fact đã xác minh hoặc
quyền truy cập. Đáp án vẫn đi qua source/snapshot/cell/citation guards sẵn có.

## Các lượt kiểm chứng đã thực hiện

Baseline trên app snapshot trước sửa: 11 FAIL/4 PASS, exit1. Một phần FAIL là
schema cũ chưa có hai vai trò mới, không diễn giải thành 11 lỗi production.
Fixture đầu được chỉnh để giữ nguyên nhãn ghép sai trong standalone question;
nếu không, normalizer cũ đã bỏ topic không còn dùng, không tái hiện đúng lỗi.
Lượt focused trung gian 9 FAIL/259 PASS được giữ; cuối269 PASS bao gồm16 test
mới. Scoped Ruff từng phát hiện style/import, đã sửa trong đúng ba file trước
niêm phong; không dùng auto-fix toàn repo.

Live batch đầu **7/8, F08 FAIL** sau hai đề xuất, không trả số liệu sai. Giữ
nguyên response/labels/postcheck ở `context592/followup`. Chưa có đủ rejected
standalone query để kết luận chính xác predicate lỗi; không quy thành thiếu
context window. Sau đó bổ sung mã lỗi literal và hướng dẫn giữ nguyên letter
case/giá trị, rồi chạy một batch tám câu mới trên bản code đã cố định. Không
resend request uncertain, không chắp vá hai phiên vào một điểm số.

Full đầu dừng sau khi phát hiện F08, receipt ghi INTERRUPTED/NOT PASS. Chỉ dừng
cây process test do task tạo sau xác minh command line. DB test cũ được dọn;
full cuối dùng DB test mới để không thừa trạng thái fixture. Full cuối so exact
IDs/nguyên nhân với JUnit Context591 (3123 PASS/18 FAIL/17 SKIP), không chỉ tổng.

Môi trường development/local được kiểm trước: DB, MinIO, Qdrant đều localhost.
Regression/full dùng DB test riêng, Local Storage tạm và endpoint ngoài ở
127.0.0.1:1; không chạy migration hoặc fixture vào DB phát triển. Chỉ sao chép
một row defaults metadata không hoạt động, không credential vào DB test.

Live gọi `rag_service.ask` thật với actor có quyền và candidate snapshot server
xác minh. Cùng source `ks_rev_993a7ad91b32`, index `idx_rev_6bf0d6f86b1b`,
canonical hash, model Luna primary/Qwen fallback trong DB; thực thi Luna-only
như phép đo trước, 8 fact mappings kiểm đúng và 0 ID đổi. Không publish để đo.
Chấm exact entity/year/header/cell/value và citation, không gọi judge LLM.

## Từng ID của lượt cuối

| ID | Đúng nội dung/ô nguồn | Citations đúng |
| --- | --- | --- |
| F01 | PASS | 1 |
| F02 | PASS | 1 |
| F03 | PASS | 1 |
| F04 | PASS | 1 |
| F05 | PASS | 1 |
| F06 | PASS | 1 |
| F07 | PASS | 1 |
| F08 | PASS | 1 |

Model repair trace cuối (không chứa query/quote riêng):

```json
[
  {
    "id": "F01",
    "calls": 0,
    "repair": null
  },
  {
    "id": "F02",
    "calls": 0,
    "repair": null
  },
  {
    "id": "F03",
    "calls": 1,
    "repair": null
  },
  {
    "id": "F04",
    "calls": 1,
    "repair": null
  },
  {
    "id": "F05",
    "calls": 0,
    "repair": null
  },
  {
    "id": "F06",
    "calls": 0,
    "repair": null
  },
  {
    "id": "F07",
    "calls": 1,
    "repair": null
  },
  {
    "id": "F08",
    "calls": 1,
    "repair": null
  }
]
```

## Bằng chứng và giới hạn

- [Live summary](../../../backend/storage/context592/followup-final/summary.json).
- [Exact proof từng ca](../../../backend/storage/context592/followup-final/labels-final.json).
- [Postcheck](../../../backend/storage/context592/followup-final/postcheck.json).
- [Focused receipt](../../../backend/storage/context592/checks/guided-final-run.json).
- [Ruff](../../../backend/storage/context592/checks-final/ruff.json).
- [Full receipt](../../../backend/storage/context592/checks-final/full-acceptance-run.json).
- [Exact failure IDs/nguyên nhân](../../../backend/storage/context592/checks-final/full-acceptance-comparison.json).
- [JUnit](../../../backend/storage/context592/checks-final/full-acceptance.xml).

Sampling vẫn có thể khác giữa các lượt. Bộ tám câu thuộc tập phát triển, chưa
là holdout. Candidate service không phải published HTTP/browser E2E. FE checks,
benchmark64 hiện tại và load/concurrent-provider test thật NOT RUN; regression
concurrency/cancellation không chứng minh tải thật. Nhánh repair chỉ có live
coverage nếu trace ở trên ghi attempted; mock tests chứng minh contract riêng.

Hai DB test đã dọn. Storage tạm/artifact bị ignore được giữ: kiểm duyệt tự động
đã chặn xóa Storage đệ quy ở lượt trước, không tắt/bypass chính sách. Không đổi
source/config/index/vector/publication; toàn bộ code/test/FE có seal trước/sau.
Không sửa báo cáo Context591 để đổi điểm lịch sử.
