# Context600 — Wiki liên kết, revision và đối chiếu

Ngày22/10/2026. Phạm vi: Wiki4–6 theo yêu cầu đính kèm; mã và kiểm thử, giữ dữ
liệu vận hành và Quality Gate. **Chưa nghiệm thu toàn nhiệm vụ** vì loss P07
thiếu điều kiện nguồn ở lượt chính. Không dùng điểm trên85% để bỏ qua lỗi này.

## Thay đổi và lý do

- Projection liên kết có version/hash từ bundle cùng snapshot; outgoing/backlinks
  một tập cạnh. Co-mention giữ literal proof ở cả hai đầu, không hợp nhất identity.
  Alias nhập nhằng chỉ candidate; nguồn/năm/mã/điều kiện và locator giữ riêng.
- RAG lọc snapshot/publication/collection và canonical text/span trước rank,
  BFS có budget/visited, cache tái kiểm quyền/revision. Thu hồi pointer trả409;
  budget thiếu closure bỏ cả section. Không thêm model call để mở graph.
- Reuse toàn nguồn không đổi khi fingerprint/binding/policy/context đầy đủ; rebind
  page ID/revision/hash, calls0 và trace. Nội dung đổi biên soạn riêng nguồn đó;
  không overwrite bundle cũ hoặc active pointer. Không partial-packet reuse.
- Review read-only: integrity/blocker, warning, source limitation, candidate,
  provider/infrastructure và stale; scope conflict không gộp năm/đơn vị/điều kiện.
  Giữ checker chất lượng hiện có, không auto-approve semantic/fact/publication.
- UI Trang liên quan/backlinks, nguồn/năm/revision và Xem nguồn; Đối chiếu nâng
  cao theo quyền, GET không compile/gọi model/ghi dữ liệu. API kiểm scope response.

9 file app backend,4 test backend,6 file frontend thay đổi/thêm. Chi tiết hàm,
compatibility và giới hạn ở [triển khai](../bao_cao/context600/IMPLEMENTATION_REPORT.md).
Tái dùng kiến trúc hiện có; không framework/worker/graph DB mới hoặc mã GPL.

## Kiểm chứng đã chạy

- Trước sửa: Git sạch, đọc AGENTS/context/rules và skill phù hợp; baseline đủ64
  trên mã cũ58/60,48/50 positive,10/10 negative,4/4 social; P10/P15FAIL,
  135/135 citations,0runtime,167Luna/0fallback. Không lấy điểm lịch sử597/599.
- Tái hiện DB thật trước sửa: cache vẫn trả3 trang sau thu hồi pointer; revision
  không đổi gọi compiler2lần. Cả hai FAIL đúng assertion rồi được sửa. Review sau
  full đầu còn literal-prefix sai,1FAIL tái hiện rồi thêm9ca/sửa ranh giới Unicode.
- Chốt focused829PASS,45ca mớiPASS; Ruff13PASS, FE22PASS, Biome6PASS, build+TSPASS.
- Full mã chốt3339PASS/18FAIL/17SKIP,+23subtestsPASS; exit1, toàn suiteFAIL.
  Exact18 ID/cause khớp599,0mới/thiếu/đổi tên. Full đầu trước literal3330PASS/
  18FAIL/17SKIP giữ riêng; chạy lại vì có app change. Không sửa18assertion nền.
- PostgreSQL/ASGI thật trong DBnonce riêng: đa nguồn2024/25/26,2027cột,year role,
  mã0/Unicode,alias,footnote/table,unknown,injection,budget,foreign/unpublished/
  revoked và create/update/remove/rollback/concurrency/latejob. Compiler selector
  mock; chặn network/model thật trong pytest. Reader bind_quote trên canonical.
- Real read-only candidate projection:11pages/10links/327refs,0blocker,
  52limitations/10warnings,1237,4ms,0model usage. Không thay fixture xuyên nguồn.
- Final đủ64:59/60=98,33%,49/50 positive,10/10 negative,4/4 social;0runtime,
  152/152 citations. GainsP10/P15, lossP07.150Luna/0fallback,
  929770input/38091outputtokens; service p50=596,86/p95=50672,60/max=68563,84ms.
- P07 thiếu tiền đề; cùng đoạn nguồn được source-review đánh required nhưng
  agreement cuối not_required nên không latch/repair. Context metadata tương
  đương baseline, audit code không đổi; drafts/targets khác, chưa causal ablation.
- Retry P07 đúng1lượt riêng cùng mã PASS,5/5citations,82944,82ms,
  12Luna/156174input/4771output/0fallback. Không thay điểm59/60. Đây là biến động,
  chưa phải sửa lỗi. Không ép mọi điều kiện/call lặp để đạt.
- Authenticated browser desktop/mobile/light/dark và published HTTP E2E NOT RUN;
  IAB bị chuyểnSSO. Không bypass đăng nhập hoặc tự publish để kiểm.

[Lệnh,45 test IDs và17SKIP](../bao_cao/context600/TEST_EVIDENCE.md),
[đủ64 ID](../bao_cao/context600/BENCHMARK_BY_ID.md),
[gate/exact18 lỗi nền/trace P07](../bao_cao/context600/VALIDATION_REPORT.md).
Receipts/raw responses/usage/seals giữ ở backend/storage/context600, được ignore;
không đưa corpus/prompt riêng/credential vào Git. Chi phí tiền/cache hit rate/
retrieval ablation chưa đo, không ước tính thành số thật.

## Cô lập và dọn tài nguyên

DB49tables `qnu_test_context600_a0f0c693aabe` có owner nonce/comment, tạo schema
chỉ DB riêng;0credential/provider rows,1defaults metadata bất hoạt. Network audit
hook chặn dịch vụ thật; endpoint test127.0.0.1:1. Đã verifyowner và DROP đúng DB,
kiểm lại không còn. Không migrate DB vận hành. Storage runtime riêng1234files/
19234687bytes,0reparsepoints đã verify absolute path; xóa đệ quy bị policy chặn,
giữ lại và không retry bằng cách khác. Usage/evidence phải giữ để audit.

Final và retry postcheckPASS: nguồn/canonical12revisions,model/profile/config,
index/epoch/vector generation,2943points/0retrievable/activeIndexNULL giữ;
0testthreads/messages/gaps. Final source/model seals6nhóm khớp trước task.
Mã19path đúng scope giữ nguyên trong full/benchmark. Không restart/reindex/
publish/deploy/commit/push; không thay LLM key/config hoặc Quality Gate.

## Giới hạn và việc chưa hoàn thành

Mã/fixture xuyên nguồn, lifecycle và consistency đã được kiểm chứng. Gate không
regression toàn RAG chưa đạt: P07 có thể bỏ tiền đề dù citations hợp lệ. Cần sửa
semantic dependency false-negative bằng contract/bằng chứng tổng quát có kiểm
soát, tái hiện cả permission/unknown/exception và chạy lại bộ nguyên vẹn sau sửa;
chưa có giải pháp được chứng minh trong batch này. Không coi retryPASS là fix.
Không tự approve identity/alias/applicability/replacement; structural checker
không chứng minh mọi semantic conflict hoặc điều kiện trong answer. Partial-packet
reuse, authenticated visual E2E và published HTTP E2E còn ngoài phần đã kiểm.

[Bộ5 báo cáo](../bao_cao/context600/AUDIT_AND_BASELINE.md),
[thiết kế](../bao_cao/context600/DESIGN.md),
[hướng dẫn](../bao_cao/context600/USER_GUIDE.md),
[workflow17](../quy_trinh/17_lien_ket_revision_va_doi_chieu_wiki.md).
