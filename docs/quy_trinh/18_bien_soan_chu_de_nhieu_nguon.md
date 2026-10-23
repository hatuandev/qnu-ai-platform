# Biên soạn chủ đề nhiều nguồn và quản lý dẫn xuất

Đợt3–4 bổ sung API quản trị cho compiler theo chủ đề. Ingestion phổ thông và
chatbot hiện tại giữ luồng cũ; bản compiler không tự thành fact có hiệu lực.
Không bắt người upload tài liệu xử lý mọi proposal trước nạp vector nguồn đã đạt
Quality Gate.

## Luồng

Preview nguồn hiện hành → source-set hash → request có idempotency → lưu intent
→ hai lượt chọn topic/kiểm phần bị loại → draft theo source → binding/independent
review → đối soát coverage có giới hạn → synthesis giữ nguồn/năm → kiểm độc lập
sections/relations và dựng lại chiều quan hệ → Storage
immutable/read-back → commit registry → người có quyền review quyết định.

Chỉ nhận source IDs trong collection do server kiểm, mới nhất của mỗi binding,
ready, raw/canonical/manifest còn khớp. Không nhận URL/secret/provider do model
chọn. Metadata ngày ban hành không tự trở thành năm dữ liệu; scope metadata và
condition nghiệp vụ giữ vai trò khác nhau. Source limitation/unknown không thành0.

Topic selection giữ ledger tất cả proof; hai lượt bất đồng hoặc bỏ sót phân loại
thì giữ cho extraction/review, chỉ loại khi cả hai khai báo không liên quan.
References dùng handle ngắn riêng trong request; server khôi phục proof có exact
revision/hash/offset. ID chưa được cấp bị từ chối. Phần tổng hợp có coverage
assertion; khám phá relation trong từng nhóm không bảo đảm mọi cặp xuyên nguồn.

ModelOps/defaults/capability/egress/quota hiện có quyết định tuyến thực thi. Toàn
request được đo ngân sách, giữ64calls/600s, không tự tăng context hoặc lặp vô hạn.
Provider/storage/JSON/budget errors là lỗi thực thi, không phải “không có tài liệu”.

Policy hiện hành `qnu-compilation-review/v3` yêu cầu scope nguyên tử có literal
anchor; section giữ một nguồn và data/effective profile tương thích. Navigation
metadata không chứng minh văn bản là dự thảo/chính thức. Ngày phiên bản là event
nếu nguồn không chứng minh role khác; so sánh các role năm cần đủ assertions.

Coverage giữ review gốc và hai lượt phân loại: thiếu fact, context hỗ trợ, không
liên quan hoặc chưa rõ. Bất đồng vai trò vẫn chặn; context chỉ liên kết các
assertions cùng nguồn đã đồng thuận. Association chưa xác minh chỉ là candidate,
không có hiệu lực. Thiếu fact chỉ repair một gói, không replay toàn nguồn.

Directed relations có quy ước subject → object. Supersedes là mới/thay thế →
cũ/bị thay thế, không suy chỉ từ ngày mới hơn. Reviewer riêng nhận endpoint
membership, không nhận chiều đề xuất; hướng dựng từ nguồn phải khớp đề xuất.
Không tự đảo relation để khớp. Bound qualifiers được mở rộng nguyên văn từ IDs
đã chọn để kiểm điều kiện; không tạo điều kiện mới hoặc bỏ qualifier thật.

## Vòng đời và quyền

`ready_for_review` chỉ báo machine ledger đạt; `needs_attention` không được
approval. Read/review phải kiểm quyền server, version/proposal hash, source-set,
artifact hash và lineage. Nguồn/pointer/epoch đổi trả stale, không cung cấp bundle
cũ cho sử dụng. Thu hồi giữ lịch sử và chặn reuse ở các dẫn xuất phụ thuộc.

Intent được commit trước inference; storage ghi/hash/read-back trước DB pointer.
Job gián đoạn có receipt uncertain, retry cùng key không tự gọi model. Concurrency
được kiểm bằng collection lock và optimistic version ở decision. Audit riêng
automated_verification và user_decision, không giả từng issue đã có người duyệt.

Registry trong metadata hiện có chỉ do service quản lý; API metadata thông thường
không nhập hoặc sửa được registry. Không có bảng/migration/worker mới. Storage
orphan sau rollback giữ theo policy; chưa thêm GC tự động hoặc xóa chứng cứ.

Artifacts policy cũ vẫn đọc/reject/revoke theo lịch sử, nhưng không cấp approval
mới bằng policy cũ. Machine verdict phải khớp ledger đã tính lại. Cache bao gồm
topic/source/config/policy để không dùng kết quả trước khi thay hợp đồng.

Approved chỉ là quyết định cho bản dẫn xuất, không publication, không sửa nguồn,
không ghi facts/embeddings hoặc repoint active index. Compiler chưa tích hợp vào
context chatbot; UI/serving rollout thuộc các đợt sau.

## Sử dụng và kiểm chứng

[Hướng dẫn API](../bao_cao/context603/USER_GUIDE.md) ·
[Triển khai/giới hạn](../bao_cao/context603/IMPLEMENTATION_REPORT.md) ·
[Kết quả kiểm chứng](../bao_cao/context603/VALIDATION_REPORT.md).

Bổ sung604: [Bảo vệ scope/coverage/hướng](../bao_cao/context604/IMPLEMENTATION_REPORT.md)
· [Kiểm chứng và blocker còn lại](../bao_cao/context604/VALIDATION_REPORT.md)
· [Đối soát24 proof](../bao_cao/context604/RECONCILIATION_24.md).

P10 được giữ ngoài phạm vi Context603 theo yêu cầu. Kết quả benchmark602 là lịch
sử, không dùng test compiler mới để ghi thành điểm chatbot mới.

## Bổ sung606 — Giá trị nguồn và kết quả kiểm chứng

Trong hợp đồng gửi model của topic compiler, `value_state=source_unspecified`
nghĩa là nguồn chưa xác định giá trị được hỏi; giữ `value=null` và bằng chứng
chứng minh giới hạn đó. `verdict=unresolved` nghĩa là nhận định chưa đủ căn cứ
để kiểm chứng. Một giới hạn nguồn đúng phạm vi có thể được supported mà giá trị
vẫn chưa xác định; không tự chuyển nó thành0 hoặc thành một ngày đầy đủ.

Server chuyển `unknown` nội bộ sang `source_unspecified` trước inference, khôi
phục trước khi kiểm/persist. Dữ liệu và hash cũ không bị migrate. Chỉ đổi trường
value_state có cấu trúc, không đổi trích nguyên văn hoặc `temporal.role=unknown`.
Cache bao gồm wire version và hướng dẫn thực tế. Schema/reference/scalar checks
và quyền approval vẫn giữ; đổi nhãn không tự làm một review thành hợp lệ.

Packet chừa dung lượng đầu ra bằng cap4primary mặc định, vẫn giữ các dependency
proofs và ngân sách toàn request. Không tăng64calls/600s hoặc bỏ proof khi vượt
budget. Empty draft review không được tự tạo assertion/check; nội dung cần nhưng
bị bỏ sót phải giữ trong missed_evidence_ids cho coverage, không tự cho PASS.

[Triển khai606](../bao_cao/context606/IMPLEMENTATION_REPORT.md) ·
[Kiểm chứng và blocker606](../bao_cao/context606/VALIDATION_REPORT.md) ·
[Đối soát nguồn606](../bao_cao/context606/RECONCILIATION.md).
