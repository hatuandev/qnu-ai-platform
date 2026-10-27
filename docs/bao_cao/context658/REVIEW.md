# Context658 — Vận hành, thử PDF thật và hybrid retrieval backendV1

Ngày hoàn tất kiểm tra: 2026-10-27. User cho phép triển khai mục 4–6, gửi dữ liệu
tới server AI đã chỉ định, chạy PDF hai trang trong môi trường riêng và dọn DB/
chỉ mục thử. Mã và artifact thử dùng nhãn nội bộ context655; số nhật ký658 được
chọn vì các phiên655–657 đã thuộc công việc frontend/SSO đồng thời.

## Kết quả triển khai

- [Operations](../../../backendV1/docs/operations.md): job/progress/usage thật,
  preview/acceptance và outbox phục hồi trên ARQ sẵn có; không reset trạng thái
  failed/uncertain hoặc tự gửi lại request model chưa rõ kết quả.
- Evidence backup theo workspace, SHA/inventory/snapshot/đọc lại ZIP; mặc định
  giữ vô thời hạn, chỉ xóa backup hết hạn sau preview/acceptance/audit. Không
  kèm bảng credential. Chưa có database/Qdrant disaster restore.
- [Hybrid/evaluation](../../../backendV1/docs/hybrid-evaluation.md): dense +
  PostgreSQL simple FTS → RRF → rerank động qua ModelOps; scope trước TopK và
  kiểm quyền/nguồn/config trước và sau HTTP. Search/answer nhận mode; assistant
  vẫn dense. Không cài dependency Haystack hoặc framework/worker mới.
- Compiler/review có tùy chọn JSON Schema; review yêu cầu từng ID làm khóa,
  giữ raw và vẫn kiểm refs/coverage ở backend. Prompt review gửi toàn bộ units
  có text/cell/header/span/bbox/identity thay vì gửi lặp cả tài liệu và bản nháp;
  input snapshot đầy đủ được giữ nguyên. Không sửa kết luận sai để ép thành công.

Migration `0014_operations` tạo hai bảng ops_ trong DB v1; ORM/ownership/head
được kiểm trong bộ test. OpenAPI **92 path/119 operation**, giữ đủ79 path cũ.
56 file Python thuộc batch được Ruff/format và kiểm UTF-8/LF. Hai file SSO thay
đổi đồng thời được ghi riêng và không sửa bởi batch này.

## Lượt thật đã hoàn tất

Nguồn `Muc hoc phi 2024.pdf`, hai trang, SHA256
`6f4ec683b0579f4ceffb42e56fa09e6fcfb3ddb240f05278a43dca7b4494e147`.
Nemotron/Qwen/BGE embedding/rerank giải quyết bằng ModelOps DB thử có credential
mã hóa; không ghi khóa vào env/source/docs. Dữ liệu và kết quả riêng nằm ở
storage đã Git-ignore. [Số liệu công khai](runtime-results.json) chỉ chứa metadata.

| Bước | Kết quả quan sát | Thời gian một lượt |
|---|---|---:|
| Render và Nemotron OCR | completed, hai trang, raw/canonical/Markdown giữ | 4,875s |
| Lưu hậu OCR | MD/JSON cùng text version; chỉ đổi xuống dòng để thử lưu | — |
| Compiler Qwen | completed, schema/citation kiểm ở BE | 19,266s |
| Review Qwen | completed, 21 source units/20 draft units | 39,250s |
| Publication/index riêng | API quyết định + BGE/Qdrant completed | index 1,375s |
| Hỏi đáp hybrid/rerank | answered, 3 nguồn, 4.590 chat token quan sát | generation 1,343s |
| Backup | completed, verify=true | 0,812s |
| Dọn | DB dropped, một vector collection thử đã xóa | — |

Review trả `needs_attention`, 6 findings: 5 ứng viên bỏ sót và một mục uncertain.
Đây là nhận xét của model, chưa được con người xác nhận. Publication trong bảng
chỉ là thao tác API thử riêng, không phải phê duyệt dữ kiện sử dụng chính thức.
Không kết luận OCR/chính tả/ngữ nghĩa đã chính xác từ trạng thái completed.

Ranh giới lượt thử: API qua TestClient, entry function worker thật, Postgres/
storage/render/model HTTP/Qdrant thật. Queue dispatch của lượt PDF riêng được
cô lập bằng queue fixture; transport Redis/ARQ được kiểm riêng trong integration
với provider loopback. Chưa thử triển khai process API/worker phục vụ thực tế.

## Thí nghiệm retrieval cùng snapshot

Ba câu **literal lookup proxy**, nhãn tạo từ source unit và citation membership,
trạng thái `draft_needs_human_check`; chưa phải gold độc lập/human/holdout. Một
retrieval chung cho mỗi query; B/C dùng chính cùng candidate IDs/hash, TopK=3,
candidateK=20. Mỗi chiến lược có3/3 completed,0error.

| Chiến lược | Hit@3 | Annotated Recall@3 | MRR@3 | Annotated Precision@3 |
|---|---:|---:|---:|---:|
| Dense | 1,000 | 1,000 | 1,000 | 0,556 |
| Dense + FTS/RRF | 1,000 | 0,833 | 1,000 | 0,444 |
| Hybrid + rerank | 1,000 | 0,833 | 1,000 | 0,444 |

**Không có bằng chứng cải thiện trong mẫu này**; dense tiếp tục mặc định. Cần
corpus lớn, câu độc lập/paraphrase/negative năm và nhãn đã duyệt trước đổi mặc
định. Answer correctness/groundedness và p50/p95/chi phí là NOT RUN; không suy
latency dense độc lập từ thời gian retrieval chung. Không đổi scope hoặc nhãn
để làm đẹp điểm số.

## Kiểm chứng và các lỗi đã ghi nhận

Lệnh chạy từ `backendV1`, dùng `.venv/Scripts/python.exe -X utf8 -B` và harness
`scripts/run_isolated_tests.py`. Guard chặn network ngoài trong regression;
live script chỉ dùng PDF/server đã được user cho phép. Receipt/XML/log chi tiết
ở `backendV1/storage/context655/` (private/ignored).

- Baseline endpoint/mode: 4FAIL trước triển khai → boundaries23PASS.
- Operations/migration5PASS; hybrid7PASS; evaluation/metrics6PASS; hardening28PASS.
- Guard/regression48PASS; backup hậu OCR1FAIL tái hiện →5PASS sau sửa namespace.
- Full đầu bị ngắt; phần unit có1FAIL vì invariant vẫn chờ adapter placeholder
  ném NotImplementedError. Invariant nay gọi upstream lỗi và kiểm adapter trả
  lỗi thật, không retry hay ranking giả; không bỏ test an toàn.
- Full sau ngắt: **535PASS/0FAIL/0SKIP**,61file,591,67s. Sau các sửa cuối:
  regression47PASS, Compiler/schema42PASS, review projection39PASS.
- Full gate cuối trên mã ổn định: xem [receipt tổng hợp](verification.json).
- Full gate đó ghi **539PASS/1FAIL** tại
  `test_compiler_workflow_e2e_654::test_corrected_source_survives_review_edit_publish_index_and_citations`:
  projection thiếu metadata `documents.text_version`. Sửa code giữ metadata,
  không bỏ assertion; regression36PASS và trọn partition2 chạy lại58PASS.
  Hợp đủ5nhóm cuối: **540PASS/0FAIL/0SKIP**,61file,48ca mới của batch và2ca SSO
  đồng thời,0ca mất so490 trước đó. Các nhóm có67/58/84/100/231ca, mỗi DB đã dọn.
- Ruff/format56file PASS; UTF-8/LF/OpenAPI PASS; 475 file legacy khớp byte với
  seal đầu batch658. Đây không phủ nhận drift lịch sử đã ghi ở Context654.

Các lượt live thất bại vẫn giữ record riêng: sai schema/thiếu hoặc lặp ID,
refs thiếu, output truncated; một lượt bị gián đoạn khi chưa ghi receipt cuối.
Mỗi lượt sửa nguyên nhân dùng DB/run mới, không reset hoặc resend job uncertain.
Lượt tiếp tục sau gián đoạn trả lời được nhưng phát hiện backup bỏ sót namespace
`ocr-text`; lỗi có regression đỏ→xanh trước lượt thật hoàn tất.

Bốn DB harness bị ngắt đã kiểm sentinel/version legacy rồi dọn theo đúng tên;
không xóa wildcard DB hoặc vector collection khác. Các lần thử model và test DB
đều có receipt/drop audit; không giữ credential thử trong DB phục vụ.

Kiểm tra cuối37tên DB do receipt xác định:0còn; quan sát Qdrant có0collection v1.
Sau lượt model thật, thay đổi cuối chỉ khôi phục metadata nguồn trong prompt;
đã kiểm lại qua API/e2e/rerun nêu trên, không gọi lại model cho bổ sung metadata.

## Giới hạn và việc tiếp theo

Chỉ thay backendV1 và tài liệu liên quan. Chưa migrate/config/restart/deploy DB/
dịch vụ đang phục vụ, chưa reindex corpus phục vụ hoặc làm UI. Giữ các sửa chưa
commit của người dùng; không push/reset Git hoặc sửa legacy.

Backup là evidence archive, chưa có full DR/restore; chưa GC orphan/generation,
GIN cho FTS, streaming hoặc assistant retrieval settings. Review là báo cáo,
chưa thành publish gate và model vẫn có thể trả kết quả không hợp lệ. Những
trường hợp đó phải hiện lỗi; không tự biên soạn lại hoặc phê duyệt.

Tham khảo [Haystack DocumentJoiner](https://docs.haystack.deepset.ai/docs/documentjoiner)
cho RRF và [vLLM structured outputs](https://docs.vllm.ai/en/stable/features/structured_outputs/)
cho giao thức JSON Schema; triển khai trong các port/domain/worker sẵn có của QNU.
