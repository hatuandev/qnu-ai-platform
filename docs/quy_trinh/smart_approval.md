# Automatic Ingestion và đối chiếu nâng cao

Luồng mặc định: upload → chuẩn hóa QNU Markdown/JSON → policy `automatic-content-v1` → AUTO_READY / READY_WITH_LIMITATIONS / NEEDS_ATTENTION → nạp vector staging → xuất bản riêng theo quyền và parity/CAS.

Source unknown/literal chưa diễn giải giữ raw, không fact số. Certificate nội dung ghim nguồn, revision, bảng, manifest, graph, facts và chất lượng; proposal chưa áp dụng không thay nội dung có hiệu lực. Không retroactive cấp certificate cho bản cũ. Thay đổi ngữ nghĩa vẫn theo lifecycle revision nháp.

Smart Approval là chế độ nâng cao: hợp đồng `qnu-smart-approval-v1`, policy `2026-10-19.1`.

## Luồng người dùng

Trong hộp thoại Kiểm Duyệt Nguồn Tri Thức, **Chấp thuận (Approve)** gửi một yêu cầu có xác thực tới `POST .../revisions/{revision_id}/smart-approval`. Không cần nhập ghi chú kỹ thuật nếu không hiệu đính. Khi có blocker, không ghi quyết định; xem danh sách ngắn và mở **Xem chi tiết đối chiếu** khi cần. Thao tác đối chiếu thủ công, bỏ đề xuất, yêu cầu sửa, nhập checkpoint và từ chối vẫn nằm trong phần nâng cao.

`dry_run=true` kiểm tra mà không lưu. `approved=false` là chưa chấp thuận, kể cả khi HTTP 200. HTTP 409 cho biết nguồn/hash/quyết định không còn phù hợp. Client không gửi actor hoặc kết quả kiểm tra để cấp quyền.

## Chính sách

Standard Document Policy xác minh khách quan manifest, evidence, target, canonical pair và hash. Bằng chứng đúng vị trí không tự chứng minh phạm vi ngữ nghĩa; thiếu căn cứ vẫn NEEDS_REVIEW. Không dùng confidence hoặc từ điển từ khóa để tự duyệt.

### Fixture acceptance

`backend/app/modules/knowledge/services/policies/semantic_fixture_v1.json` là đặc tả chấp nhận fixture đã đối soát theo Context555–557, không phải từ điển parser. Đây là ngoại lệ cụ thể được yêu cầu ở Context558. Chỉ đúng binding/revision/hash DOCX/hash MD/hash JSON/projection version/proposal hash và digest toàn bộ annotations/context review mới được dùng. Các digest khóa cả điều kiện, ngoại lệ, evidence và reference role. Đổi scope, target hoặc provenance sẽ mất quyền tự xác minh. Không chọn chính sách từ tên file.

Oracle fixture bảo toàn: A03 chỉ workflow hồ sơ thiết bị nhóm A/kế hoạch 2027, tối đa 15 ngày khi đủ điều kiện, không sửa c10/c11/c12 hay số liệu SV; A10 chỉ AM-0007; A11 chỉ c11 Ước tính; A12 giữ chuỗi 0012/00027/AM-0007. Sáu reference assessment giữ related, direct/protective/conditional và điều kiện riêng. Các xác minh này không xác nhận một hồ sơ thực tế đã đủ điều kiện hưởng ngoại lệ.

CT-05 có chú giải riêng: chưa đo do tạm ngừng; trạng thái dẫn xuất not_stated, giữ raw, không suy 0. CT-06 được nguồn xác nhận chưa công bố nghĩa. Dấu / ở Bảng 9 chưa đủ căn cứ dùng chú giải riêng CT-06. Giới hạn nguồn không được biến thành số hoặc fact khẳng định. Chính sách xuất bản có giới hạn vẫn tắt; luồng này không bật nó.

Quality Gate có version cùng policy. Mất bảng, nội dung quan trọng, sai hash hoặc thiếu căn cứ vẫn chặn. Page chưa rõ chỉ thành warning khi footnote còn locator Word và unit neo tham chiếu thật trong canonical pair đã kiểm chứng. Không miễn trừ mọi warning theo tên loại.

## Audit và tính nhất quán

Một transaction dưới source row lock: kiểm tra actor/quyền và idle; kiểm tra revision, tệp gốc, canonical pair, proposal; dựng lại base và kiểm tra ô; validation; guard duyệt cũ trên bản sao; ghi sidecar bất biến/readback; ghi source decision và receipt; commit. Lỗi/cancel rollback DB. Object đã lưu nhưng commit lỗi có thể còn là sidecar không được tham chiếu, không có hiệu lực phục vụ.

Receipt giữ actor thật, thời gian, source/revision, các hash, policy/version, kết quả kiểm tra và bulk acceptance. Snapshot v3 khóa certificate máy và quyết định bulk; không tạo 18 context_decisions giả danh người đã đọc từng mục. V1/v2 giữ nguyên cách tính hash. Replay kiểm tra lại certificate theo oracle. Nhiều yêu cầu cùng actor/cùng nội dung chỉ có một quyết định; actor/nội dung khác hoặc source đã đổi trả conflict.

Luồng không gọi ModelOps, không reparse, không tạo index/vector/chunk/fact DB, không đổi epoch hoặc kích hoạt vector generation. Chấp thuận nguồn vẫn dùng hành vi source revision hiện có; xuất bản/lập chỉ mục là bước riêng.
