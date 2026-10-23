# Context600 — Triển khai Wiki 4–6

Ngày22/10/2026. Mã triển khai trên kiến trúc hiện có; chưa thay dữ liệu vận hành.
Kết quả gate và benchmark cuối được ghi riêng trong [VALIDATION_REPORT](VALIDATION_REPORT.md).
Focused829/FE22 PASS; full3339PASS/18FAIL nền/17SKIP. Baseline58/60→cuối59/60,
gainsP10/P15 nhưng lossP07 thiếu điều kiện nguồn. Mã đã triển khai; chưa nghiệm
thu toàn nhiệm vụ hoặc toàn RAG. Retry P07 riêng PASS không xóa loss lượt chính.

## Phạm vi file/hàm

| File | Thay đổi và lý do |
|---|---|
| `backend/app/modules/knowledge/services/wiki_links.py` | `build_page_links`, `validate_page_links`, `expand_linked_pages`: projection theo snapshot, outgoing/backlinks cùng một tập cạnh, evidence exact source có locator/span/hash, version/hash riêng; BFS có giới hạn. |
| `.../wiki_snapshot.py` | `snapshot_records`, `load_snapshot_pages`, `read_collection_map`: lọc collection/epoch/binding/index/vector/publication trước dựng map; kiểm epoch cuối GET; lỗi DB503, stale409, không ghi dữ liệu. |
| `.../wiki_reuse.py` | `find_reusable_wiki`, `rebind_wiki`: kiểm bundle cũ và fingerprint tương thích, rebind ID/render/hash cho revision mới, gọi compiler0 lần; giữ nguyên bundle cũ và trace reuse. CPU chạy ngoài event loop. |
| `.../wiki_consistency.py` | `check_source`, `comparable_values`, `check_snapshot_consistency`: kiểm toàn vẹn/context/duplicate/year role/source limitation, so giá trị theo scope; chỉ gợi ý khi identity chưa được duyệt. Tái dùng Quality Gate hiện có. |
| `.../chunk_set_service.py` | Chọn reuse tương thích trước gọi `build_revision_wiki`; giữ khóa source, unique revision/config, seal và transaction hiện có. Không sửa pointer publication. |
| `.../wiki_views.py` | Trả phiên bản/hash/năm; `read_revision_review` cho revision đang xem, gồm staging/historical có quyền, không compile từ GET. |
| `backend/app/modules/knowledge/wiki_router.py` | Ba GET mới: map, map/review và knowledge-pages/review; view/review được kiểm ở server, router mỏng. |
| `.../wiki_schemas.py` | Độ sâu0–2, tổng node1–6 và lượt duyệt cạnh0–128; mặc định1/3/32. Không tăng lượt model hiện có. |
| `backend/app/modules/rag/wiki_context.py` | Kiểm text/span canonical, scope hiện hành trước cache, key có snapshot/graph/policy/provider/assistant; expand chỉ co-mention có chứng cứ, lọc năm/relevance trước mở. |
| `frontend/src/features/knowledge/components/knowledge-wiki-navigation.tsx` | Trang liên quan/backlinks, nguồn/năm/revision và deep link; Advanced Review tải khi mở và có quyền, phân loại thông báo tiếng Việt. |
| `.../knowledge-wiki-panel.tsx` | Tích hợp vào panel hiện có; anchor từng trang, số revision, giữ Xem nguồn và bố cục. |
| `frontend/src/services/knowledge-api.ts`, `types/knowledge-wiki.ts` | GET có auth; kiểm collection/binding/revision response trước dùng. Không thêm mutation hay submit giả. |
| Bốn `backend/tests/test_wiki_*_600.py` | 45 regression mới: nguồn/năm/mã/alias/span/graph/budget, ASGI/quyền, cache, update/remove/rollback/concurrency/late job; gồm9 ca chặn prefix/tách Unicode. |
| Hai test frontend wiki | 7 ca mới; adapter import test panel cũ cho component mới, giữ các assertion gốc. Reader canonical cũ được chạy kèm. |

## Wiki4 — phạm vi quan hệ

`source_reference` là quan hệ cấu trúc giữa trang dẫn xuất và nguồn; `co_mention`
chỉ xác nhận chuỗi nguyên văn có trong bằng chứng ở cả hai đầu. Mỗi đầu giữ
binding/source/index/hash và các scope/condition/exception riêng. Evidence dùng
ID nguồn, span codepoint, locator/trang và quote canonical; không cite wiki làm fact.

Cùng tên không gộp node. Cùng mã, khác tên có thể sinh candidate alias nếu cả tên
và mã còn nguyên văn trong unit nguồn; không tự kết luận identity. Candidate
không vào map phổ thông hoặc BFS. Khác mã giữa các năm cũng không chứng minh
cùng/khác một thực thể. Không thêm dictionary ngành/năm/từ khóa benchmark.

Projection được dựng lại từ bundle hợp lệ, có `qnu-wiki-links/v1` và SHA; không
cần sidecar ghi vào index đóng băng. Giới hạn2048 trang/8192 cạnh/100000 reference
và tổng reference cạnh; vượt trả lỗi budget, không ghi partial-ready graph.
RAG vẫn có budget chars/context/calls/time hiện có, visited set và depth/node/edge.

## Wiki5 — vòng đời và tương thích

Nguồn không đổi phải khớp toàn fingerprint: binding, raw/canonical, metadata,
normalizer/parser, unit/context graph, fact/semantic hash và policy. Kiểm seal
chunk-set cũ trước reuse. Revision mới có page IDs/render/hash mới; reuse ghi
revision/hash bundle gốc và fingerprint, calls/model_calls mới bằng0.

Nguồn đổi chỉ biên soạn lại nguồn đó theo pipeline hiện có; không gọi compiler
cho toàn collection. Chưa tối ưu reuse từng packet khi canonical thay đổi.
Không suy bản mới nhất có hiệu lực từ upload time/tên file. Job cũ chỉ tạo
derivative của revision cũ, không thể chuyển active pointer bằng mã mới này.
Remove/rollback đổi snapshot; cache/map cũ bị loại hoặc trả lỗi stale.

Nguồn không wiki và wiki v1 cũ vẫn được đọc bằng pipeline cũ. Bundle unavailable
không thành trang giả. Hỏng integrity không tự regenerate để che lỗi. Không đổi
schema DB, worker, vector generation, model/provider/fallback hoặc Quality Gate.

## Wiki6 — giới hạn diễn giải

Blocker toàn vẹn/quyền tách khỏi warning, source limitation, candidate,
provider/infrastructure và stale/not compiled. Kiểm scope so giá trị đòi có
năm dữ liệu verified, metric, đơn vị, mã và conditions tương ứng; khác năm/
điều kiện không tự thành mâu thuẫn. Identity xuyên nguồn chưa được duyệt chỉ
được thông báo cần đối chiếu, không coi là một fact đã xác nhận.

Kiểm cấu trúc không chứng minh đã hiểu mọi mâu thuẫn ngữ nghĩa. Không thêm
approval semantic hoặc suy quan hệ áp dụng/sửa đổi/thay thế/hết hiệu lực từ tên
hay co-mention. Các quan hệ đó chưa có bằng chứng tương ứng vẫn không được dùng
làm tiền đề. Không gọi LLM khi GET, không tự sửa facts/publication, không buộc
người dùng phổ thông duyệt candidate để dùng nguồn đã đạt gate.

Review diff đã đối chiếu với ranh giới serving thực tế. Phát hiện và xử lý: tách
thu hồi quyền thật khỏi việc context budget làm thiếu block; giữ hành vi bỏ
section cache không đầy đủ của595 và báo stale409 khi binding/index đã bị thu
hồi. Không sửa assertion backend cũ để che regression. Thêm guard canonical
text/span trước rank, epoch cuối GET và giới hạn reference projection.

Probe review riêng tái hiện co-mention sai khi title là prefix của từ/mã dài
hơn, trước sửa:1FAIL đúng assertion. Bổ sung ranh giới chữ/số/combining mark và
ký tự nối mã, không normalize Unicode hoặc fuzzy match. Tên chưa chứng minh
nguyên vẹn chỉ còn candidate. Vì có thay đổi sau full đầu, full được chạy lại
trên mã chốt; không dùng full trước sửa literal để thay gate cuối.

Không thay source-dependency audit/agreement để chữa một câu bằng heuristic.
Trace P07 và retry trên cùng mã được giữ riêng; guard semantic còn false-negative
và việc xử lý tổng quát chưa được chứng minh. Các quan hệ ngữ nghĩa chưa có proof
vẫn chỉ candidate; kiểm tự động hiện tại không phát hiện chắc chắn mọi tuyên bố
thay thế/hết hiệu lực hoặc mọi điều kiện bị bỏ trong đáp án. Đây là giới hạn thực
tế, không được trình bày thành kiểm tra ngữ nghĩa đã đạt.
