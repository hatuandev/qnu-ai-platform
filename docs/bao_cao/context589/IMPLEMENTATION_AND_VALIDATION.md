# Context589 — Trang tri thức trích nguyên văn và kiểm PDF thật

## Quyết định sản phẩm và phạm vi

Người dùng chọn “LLM chọn nội dung, server trích nguyên văn có nguồn”. Giữ Luna
chính, Qwen dự phòng, timeout Luna 30 giây; không đổi model/config DB, hạ Quality
Gate, publish, restart, deploy, commit hoặc push. Giữ các thay đổi Context587–588.

Compiler v3 chỉ gọi ModelOps để chọn nhóm source/entity/concept và IDs. Server
dựng từng trích đoạn từ unit canonical, kèm heading/header/context liên kết rõ.
Trang nguồn giữ đủ unit không phải container. Không sinh lại số, mã, ký hiệu,
điều kiện hoặc ngoại lệ bằng prose của model. Unknown giữ nguyên.

## Nguyên nhân và cách sửa

Context588 giới hạn text nhưng bỏ sót metadata lặp: 23.891 ký tự text thành
107.136 ký tự JSON, analysis dùng 35.591 prompt tokens. Đã chia gói theo toàn
request, chia sẻ metadata, dùng handles riêng từng request và giữ nguyên unit.
Cận trên UTF-8 có framing/output reserve là giới hạn bảo thủ, không phải token
quan sát. Model/provider vẫn giải quyết động qua ModelOps.

Các revision thử 6–11 giữ nguyên cùng index staging. Những lượt v2 đã thất bại
vì prose nêu số/mã nhưng refs của đúng section chưa chứng minh, JSON/shape sai
hoặc số refs chưa đủ. NV-34 có trong canonical; lỗi là thiếu liên kết bằng chứng
ở phần diễn giải, không phải parser làm mất dòng. Có một full probe RAM đạt
16 trang/32 lượt, nhưng không dùng nó thay kết quả persistence. Revision 11 vẫn
unavailable/0 trang sau 20 phản hồi Luna thành công; actual HTTP GET trả đúng
trạng thái unavailable. Không biến probe chọn lọc thành nghiệm thu.

Theo quyết định mới, v3 bỏ bước viết lại dữ liệu. Kiểm khi đọc bundle dựng lại
text và tập refs từ nguồn, không chỉ so hash. V2/policy cũ giữ chế độ generated;
không cập nhật wiki của revision/index cũ. Trang mới có tối đa 512 trích đoạn,
20 refs/phần; thiếu context hoặc không vừa giới hạn thì chặn, không cắt nguồn.
Vai trò năm chỉ là gợi ý điều hướng có quote riêng, không phải phê duyệt ngữ nghĩa.

Đã tái hiện lỗi tích hợp: wiki_enabled chuyển cả câu hỏi ô dữ liệu sang nhánh
prose. Regression trước sửa 1 FAIL/3 PASS. Sửa giữ nhánh fact-first/đối soát tọa
độ; câu hỏi diễn giải dùng điều hướng wiki, cấu hình evidence bật rõ vẫn giữ hiệu
lực. 147 test trọng tâm sau sửa đạt. Trang dài mở theo phần hoàn chỉnh có đủ
context và ghi rõ partial/total; không cắt chuỗi giữa điều kiện hoặc nguồn.

## Kiểm PDF thực tế

- Revision 12 `ks_rev_993a7ad91b32`; index `idx_rev_6bf0d6f86b1b`.
- PDF 648.851 bytes; canonical 51.531 ký tự, hash không đổi so với Context588.
- Source pair fidelity PASS, READY_WITH_LIMITATIONS, 0 blocker.
- 11 trang ready: 1 nguồn, 2 thực thể, 8 khái niệm; 431 trích đoạn.
- Đủ cả 327 đơn vị nguồn; 1.915 lượt tham chiếu khớp exact canonical spans.
  Text của mọi phần là phép ghép nguyên văn có nguồn; NV-34 được giữ đúng nguồn.
- Biên soạn thực tế: 7 phản hồi Luna, 39.313 prompt tokens/3.303 completion
  tokens; prompt lớn nhất 6.308; 0 fallback. Không cần sửa prose nhiều lượt.
- API HTTP GET local 200/ready, đúng identity và page IDs đã lưu.
- Staging 327 chunks/415 facts. Tổng namespace 2.943 points gồm lịch sử cũ;
  0 retrievable, active publication index vẫn null. Không publish.
- Lượt này không có temporal role annotation do model trả về: năm vẫn hiện
  nguyên văn trong header/nguồn; không tuyên bố đã kiểm semantic year-role tự động.

[Bản xem trang đã lưu](../../../backend/storage/context589/extractive/REVIEW.md).
Nội dung nguồn, model outputs, câu hỏi/gold và bằng chứng chi tiết nằm trong
Storage bị ignore; không đưa corpus hoặc prompt riêng vào tài liệu theo dõi Git.

## Kiểm thử

Baseline riêng của task: 3.026 PASS/18 FAIL/17 SKIP +23 subtests PASS, exit 1.
DB test có owner nonce; DB/MinIO/Qdrant kiểm local, test dùng LocalStorage riêng
và endpoint hạ tầng 127.0.0.1:1. Không migration/seed DB dùng chung hoặc test với
credentials LLM thật. Full suite còn lỗi nền luôn báo FAIL.

- Full trước v3: 3.070 PASS/18 FAIL/17 SKIP, exact IDs/causes khớp baseline;
  44 test mới PASS, không thiếu ID; source code seals trước/sau khớp.
- Focused v3 tương thích: 109 PASS, exit 0.
- Full v3 trước sửa routing: 3.082 PASS/18 FAIL/17 SKIP +23 subtests PASS;
  56 test mới PASS, không lỗi mới, không thay cause/thiếu ID, exit 1.
- Focused routing và scope/provenance: 147 PASS, exit 0. Ruff 15 file PASS.
- Full `full-integration-final` bị ngắt khoảng 77% khi turn bị gián đoạn;
  không có JUnit/result hoàn tất, không được coi là PASS. Code vẫn khớp seal.
- Full cuối `full-integration-handoff`: 3.086 PASS/18 FAIL/17 SKIP +23 subtests PASS, exit 1.
  Exact 18 IDs/cause khớp baseline, 60 test mới PASS, không lỗi mới hoặc thiếu ID;
  code seals trước/sau khớp. Full suite vẫn FAIL vì 18 lỗi nền.
- Frontend build/browser chatbot E2E hiện tại NOT RUN; không sửa FE trong batch này.
- Đã dọn DB test có owner nonce; Storage tạm được giữ do chính sách bảo vệ,
  không tắt policy hoặc thử xóa qua đường khác.

## Benchmark và giới hạn

Đúng frozen64 của Context588, cùng câu hỏi/rubric/gold spans, source/model/timeout;
chỉ remap 33 fact IDs theo unit/cột/header/raw value/mã giống hệt. Snapshot wiki
thực sự enabled. Đã chạy candidate service thật, không HTTP chatbot đã publish.
Không chấm lại gold để làm điểm tăng, không ghép điểm probe vào bộ chính.

Turn bị gián đoạn sau 39 kết quả, lúc đó đang chờ P06. Đã giữ bản gốc và receipt;
P06 không có response lưu được, tính chưa hoàn tất/không PASS. Đã tiếp tục từ P07,
khôi phục đúng session và lịch sử của các kết quả đã nhận; không gửi lại yêu cầu
đang uncertain. P01 provider 502; P03 WikiReadAction extra_forbidden; các lỗi
này giữ FAIL, không chuyển thành từ chối đúng hay đổ cho context window.

| Phạm vi | Kết quả |
|---|---:|
| Câu tri thức, P06 bị gián đoạn tính không đạt | 50/60 — 83,33% |
| Câu có đáp án | 40/50 — 80% |
| Câu âm/thiếu dữ liệu | 10/10 |
| Hội thoại thường | 4/4, không retrieval/model |
| Trích dẫn khớp nguồn | 98/98 |

**Chưa đạt mục tiêu 85%, chưa APPROVED toàn luồng.** Có 63/64 kết quả thực thi;
P06 trong bộ chính không nhận được response đã lưu nên không báo bộ chính complete64 hoặc PASS; lượt bổ sung báo riêng bên dưới. Thời
gian P06 không được bịa hoặc trộn vào thống kê độ trễ. Ngay cả nếu P06 đạt, tỷ
lệ câu có đáp án vẫn chưa đạt ngưỡng 43/50; gián đoạn không giải thích mọi lỗi.

| Câu | Kết quả và nguyên nhân đã quan sát |
|---|---|
| P01 | FAIL: đã mở trang, provider HTTP 502/provider_request_failed; service ALL_PROVIDERS_UNAVAILABLE. |
| P03, P13, P14 | FAIL: mở trang thành công, lượt điều hướng tiếp sai WikiReadAction (`extra_forbidden`). Không có đáp án. |
| P05 | FAIL: từ chối dù nguồn có căn cứ về phạm vi cột ước tính/ghi nhận. |
| P06 | Bộ chính bị gián đoạn, tính không đạt trong điểm bảo thủ; lượt bổ sung phiên mới PASS, báo riêng. |
| P07, P11 | FAIL: yêu cầu năm/đợt không cần thiết (`YEAR_REQUIRED`), chưa đáp ứng điều kiện/so sánh được hỏi. |
| P09, P10 | FAIL: `ROW_ANSWER_SOURCE_INVALID`; giữ lỗi, không biến thành câu trả lời unknown giả. |

So với Context588 55/60: cải thiện F04; giảm ở P01/P03/P06/P11/P13/P14;
P05/P07/P09/P10 vẫn lỗi. Đối chiếu theo ID/criteria/span, không chỉ tổng điểm.
Không kết luận quan hệ nhân quả từ một lượt sampling khác hoặc coi đây là ablation.

Snapshot có wiki enabled. P01/P03/P13/P14 có action đọc trang thành công, không
budget rejection; cả bốn sau đó lỗi trước khi hoàn tất điều hướng/trả lời. Vì vậy
không có bằng chứng wiki đã cải thiện đáp án trong bộ này. Không dùng chỉ số
`cases_opening_pages=0` ở bước hoàn tất để phủ nhận bốn action mở trang đã diễn ra.

Usage benchmark quan sát 86 phản hồi Luna thành công, 388.887 prompt/17.192
completion tokens, prompt lớn nhất 8.959, 0 fallback. Đây là số ghi log thành
công, không bao gồm mọi request thất bại chưa có response. Không có thông báo
vượt context được ghi nhận; không đổi context/model để che lỗi hợp đồng.

Toàn Context589 compiler/probes, gồm cả lượt bị từ chối: 262 phản hồi đã ghi,
1.260.508 prompt/200.662 completion tokens, 0 fallback được chấp nhận. Không
tính trùng bundle/index receipts, không cộng embedding, không ước lượng tiền giả.
V3 nghiệm thu chỉ chiếm 7 lượt trong tổng này; giữ lại lịch sử thất bại.

Postcheck PASS cho an toàn và tính bất biến: source bytes/canonical, model/config,
timeout 30s, old source/index versions, ngoài phạm vi và vector payload giữ đúng
seal; 0 test threads/messages/gaps còn lại. Giữ revision/index mới có chủ đích và
audit usage; không xuất bản. Không dùng postcheck này thay kết quả chất lượng FAIL.

### P06 bổ sung sau gián đoạn — báo riêng

Để kiểm chứng đủ 64 câu độc lập, đã chạy P06 một lần trong conversation mới,
cùng snapshot/model/cấu hình/gold. Không resend conversation cũ hoặc ghi đè
record P06 bị gián đoạn. Lượt bổ sung PASS: giữ đủ nhóm A/kế hoạch 2027, tối đa
15 ngày làm việc từ hạn ban đầu, thông báo kiểm định trùng đợt khóa và quyết
định gia hạn; không tác động chỉ tiêu SV hoặc nhóm B. 5/5 citations khớp nguồn,
5 phản hồi Luna ghi log/0 fallback, 27.911 prompt và 1.425 completion tokens.

Nếu tính lượt bổ sung này, điểm **tham khảo** là 51/60 (85%), nhóm câu có đáp án
41/50 (82%), âm 10/10 và hội thoại 4/4. Đây không phải một lượt frozen64 không
gián đoạn. Bộ chính vẫn giữ 50/60 và P06 chưa hoàn tất. Có kết quả thực thi cho
đủ 64 câu duy nhất qua các đoạn chạy, nhưng **vẫn chưa đạt tiêu chí câu có đáp án
ít nhất 43/50**. Không đổi gold hoặc hạ tiêu chí để báo đạt.

## Bàn giao

Trạng thái: **trích nguyên văn/persistence/API/vector staging đạt; chất lượng
chatbot chưa nghiệm thu**. Chưa chuyển sang ưu tiên 4–6 hoặc xuất bản.

Việc kế tiếp là sửa chung hợp đồng/luồng điều hướng của reader và cách bảo toàn
nhánh trả lời đã kiểm chứng, rồi kiểm lại trên cùng nguồn/model/gold. Giữ riêng
lỗi provider với lỗi thiếu chứng cứ hoặc chưa xác định năm. P05/P09/P10 là khoảng
hở cũ cần đối soát ở nhánh trả lời, không có bằng chứng rằng parser đã làm mất
nội dung cần cho các câu này. Không tạo revision/vector mới chỉ để thử reader.

Lệnh từ root: `backend/.venv/Scripts/python.exe -X utf8` với các helper task-owned
trong `.antigravity-bridge/validation/context589_*`; Pytest chạy cwd `backend`
với DB test riêng và JUnit theo từng ID. Ruff có phạm vi 15 file, exit 0.
Các receipt private giữ command/cwd/exit code, before/after seals và nguyên nhân.

Kiểm duyệt tự động trước đó đã chặn xóa cây Storage tạm để bảo vệ dữ liệu.
DB test đã xóa đúng owner marker; thư mục `backend/storage/context589-runtime-b8f58e0ebaff`
được giữ nguyên. Không bypass, không tắt chính sách bảo vệ để hoàn thành dọn dẹp.

Không tuyên bố APPROVED toàn luồng chỉ vì trang trích nguyên văn đã đạt. Kết quả
benchmark và kiểm thử đầy đủ được ghi riêng cùng các giới hạn còn lại. Chưa làm
ưu tiên 4–6, chưa hợp nhất thực thể xuyên nguồn hoặc biên soạn lại kho cũ.
