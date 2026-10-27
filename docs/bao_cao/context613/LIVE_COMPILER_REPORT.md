# Context613 — Thử compiler với ba DOCX thật

## Kết quả

**Đã vượt qua điểm chặn tổng hợp và tạo được bản Markdown cùng manifest, nhưng nội dung vẫn `needs_attention`, chưa APPROVED.** Không thay nguồn, Quality Gate, model mặc định, chỉ mục hoặc publication.

| Thành phần cuối | Kết quả |
|---|---:|
| Nguồn DOCX | 3, canonical381proof của parser602 |
| Thực thể giữ lại | 92 |
| Assertion giữ lại | 145 |
| Section nội dung | 25 |
| Nhóm tổng hợp nguồn | 14 |
| Nhóm quan hệ bổ sung | 2 |
| Quan hệ ứng viên trong bundle | 9, gồm5 từ tổng hợp nhóm và4 bổ sung |
| Markdown | 58.898byte UTF-8 |
| Đọc lại bundle qua service | Khớp chính xác |
| Publication | unpublished |
| machine_complete | false |

Job cuối trong DB thử là `kc_ac5d5ad35e284b5f924770ae87c36d35`. Bản trước khi đối chiếu liên nguồn là `kc_856d7b406cab430b97e8ffbc79e2da18`; bản cũ được đọc lại và giữ nguyên, không ghi đè checkpoint.

## Tái sử dụng và lượng gọi model

Đọc-only namespace thử Context611 trên MinIO local, kiểm288object theo checksum:91completed inference output và197event/audit. Dựng lại đúng96logical request identities của lần cũ, trong đó5JSON/schema rejection có diagnostic đã lưu. Replay không có inference hoặc network attempt.

Trong DB/Storage thử613, các packet được namespace lại theo request/hash mới, kiểm binding và chạy lại các guard cơ học hiện tại. Tái sử dụng21packet/12topic batch như **ứng viên thử có provenance**, giữ cả10packet chưa complete. Đây không phải API migration hay việc xác nhận protocol mới đã chạy các lượt inference cũ. Không tự nhập cache ứng viên chưa đạt vào production.

| Lượt mới trong phiên | Số model calls |
|---|---:|
| Tổng hợp nguồn/kiểm tra/chiều quan hệ | 36 |
| Probe đối chiếu đầu tiên trước khi chốt protocol tìm kiếm | 1 |
| Đối chiếu liên nguồn theo protocol cuối | 17 |
| **Tổng thực tế trong phiên** | **54** |

Tổng53 trong receipt cuối chỉ cộng36+17 của hai giai đoạn tạo bundle cuối; báo cáo chi phí vẫn tính thêm probe1. Không che hoặc gộp probe thành0. **Không gửi lại96lượt cũ.**

Cả54response quan sát đều `finish_reason=stop`,0fallback. Usage thực:263.475input/45.158output; output lớn nhất2.475. Tất cả wire requests gửi đúng `ollama/gpt-oss:120b`, `reasoning_effort=medium`, output8.192. Upstream không echo mức effort/reasoning breakdown, nên chỉ chứng minh app đã gửi tham số đúng, không chứng minh độc lập server thi hành mức medium.

Primary trong ModelOps vẫn `gh/gpt-6-luna`; thử nghiệm chọn GPT-OSS trong process riêng. Không đổi catalog, endpoint, timeout hoặc credential. Provider chưa có profile dung lượng được xác nhận cho alias GPT-OSS; lượt thử dùng override server context24K/output8.192 và ghi `conservative_server_fallback_unverified`, không tự nhận đã biết context thật.

## Đối chiếu liên nguồn và phần chưa kiểm tra

Tìm kiếm sơ bộ xác định31cặp có nhãn trùng/gần nhau. Giai đoạn kiểm chứng giới hạn12cặp trong budget36calls; thực dùng17calls. Trong12cặp đã hỏi, các cặp không có quan hệ được model trả mảng rỗng, không chuyển thành fact chắc chắn rằng quan hệ không tồn tại.

Còn19cặp chưa được kiểm trong lượt này. Đây là khoảng coverage được công bố qua `total_candidates` và số candidate đã đưa đi, không được báo thành0pending toàn bộ. `machine_complete=false` cũng chịu kiểm tra này. Không tiếp tục gọi model để làm xanh kết quả.

Bốn quan hệ mới vẫn chưa đủ duyệt: ba có verdict supported nhưng cờ temporal_roles=false; một verdict unresolved; các hướng quan hệ có hai issue. Việc relation tồn tại trong bundle `review_only` không làm nó thành dữ liệu có hiệu lực. Các cặp phát hiện bằng nhãn không chứng minh identity, scope hoặc supersession.

## Các vấn đề nội dung còn giữ

| Kiểm tra | Kết quả |
|---|---:|
| Packet đạt đủ check | 11/21 |
| Verdict assertion của reviewer | 131supported /13unresolved /1contradicted |
| Lỗi scope cơ học | 5 |
| Proof còn trong missed ledger | 17 lượt tham chiếu |
| Section có verdict chưa supported | 2 |
| Relation có verdict chưa supported | 1 |
| Issue kiểm chiều quan hệ | 2 |
| Giá trị nguồn unknown giữ nguyên | 32 |

Các nhóm số trên có thể chồng lấp; không cộng thành tổng số lỗi duy nhất. Chữ supported cũng chưa đủ nếu các cờ scope/time/condition không đạt.

Đối soát giá trị, trạng thái, source refs, scope, điều kiện, ngoại lệ và entity có bằng chứng giữa145ứng viên đầu vào và bản cuối cho kết quả khớp hoàn toàn sau khi bỏ ID namespace dẫn xuất. Không cắt dữ kiện để vừa cap. Xem [đối soát sơ bộ](RECONCILIATION_REPORT.md) về sai mức đào tạo, vai trò chỉ số và absence claim.

## Môi trường và giới hạn kiểm chứng

Thực gọi ModelOps qua provider hiện có; pipeline compiler, StageCheckpoints, registry, StorageDriver, service finish/read và actor admin thử thực chạy trong DB local thuộc phiên. Data fixtures dùng raw DOCX đúnghash và canonical đã lưu; không chạy parser mới, không chứng nhận lại full source Quality Gate, không kiểm chatbot64câu hoặc browser/publication E2E.

Harness thử explicit candidate import và tách hai giai đoạn để tránh lặp chi phí. Trước/sau đối chiếu bản cũ qua service; lời gọi mới giữ intent/checkpoint riêng. Không được gọi đây là toàn bộ upload→parser→compiler mới từ đầu hay migration resume production. Regression riêng đã kiểm pipeline mới từ source fixture và đọc lại manifest lớn.

Các lượt setup/preflight không gọi model. Một intent mới dùng lại key cũ đã bị409 trước inference; giữ receipt từ chối, sau đó dùng mã thử riêng. Không resend một intent inference uncertain.

## Bằng chứng local

`backend/storage/context613`: `independent-assessment.json`, `offline-audit`, `cache-replay`, `prior-objects`, `live`, `live-cross`, `live-cross-validation`. Bundle/wire/checkpoint/audit nằm trong artifact thử, không đưa corpus lên Git.

Xuất để xem thử, có thông báo chưa duyệt: [Markdown](../../../backend/storage/context613/exports/compiled-topic.md), [manifest JSON](../../../backend/storage/context613/exports/compiled-topic.json), [lưu ý](../../../backend/storage/context613/exports/EXPORT_NOTICE.md). Các tệp này là bản đọc từ bundle đã lưu, không thay canonical nguồn và không được serving tự động.
