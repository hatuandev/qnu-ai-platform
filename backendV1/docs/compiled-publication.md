# Quản lý phiên bản và xuất bản bản biên soạn — backendV1

Mở rộng hiện hành: [metadata phục vụ retrieval](rag-policies.md) được đăng ký bất
biến cùng phiên bản và gắn vào bundle hash; metadata có nội dung phải được người
duyệt xác nhận đúng hash trước khi approve. Phiên bản không có metadata giữ hash cũ.

Bước 3 nối sau [Compiler v1](compiler-v1.md): đăng ký output Compiler thành phiên
bản của một tài liệu có định danh riêng → duyệt → xuất bản → thay thế/thu hồi.
Đây là vòng đời do QNU định nghĩa. Điểm tham khảo Kotaemon là tổ chức nguồn và
truy ngược citation; không coi repo đó là bằng chứng cho đúng workflow này.

## Ranh giới và dữ liệu

Workspace là biên giới quyền của **backendV1**, theo ngoại lệ AGENTS.md; không
áp dụng sang `backend/`. Router luôn qua `resolve_workspace_access` rồi collection
→ document → version. ID từ client chỉ là đối tượng cần kiểm tra.

Compiler run có trạng thái xử lý `completed/failed/...`. Trạng thái xuất bản được
lưu riêng trong phiên bản; `completed` không tự trở thành approved hoặc published.
Bốn bảng publication đã nằm trong baseline `0001_initial_schema`:

| Bảng | Nội dung |
|---|---|
| `kb_compiled_documents` | Định danh tài liệu, document_key/title và sequence thay đổi |
| `kb_compiled_versions` | Phiên bản tăng dần trong tài liệu, run gốc, các hash, provenance và lifecycle |
| `kb_publication_previews` | Preview gắn actor/action/reason, hash, sequence, bản đang hiệu lực và hạn dùng |
| `kb_publication_decisions` | Quyết định bất biến, before/after, actor/reason, idempotency và sequence |

Một collection có nhiều tài liệu. `document_key` do người có quyền chọn tường minh,
không suy hai topic giống nhau từ nội dung LLM. Muốn thay thế một tài liệu, thêm
phiên bản vào **đúng document_id**; tạo document_key khác không thay bản cũ.
Mỗi Compiler run chỉ đăng ký thành một phiên bản. FK tổ hợp giữ đúng scope.

Phiên bản giữ input/draft/Markdown/bundle SHA256, provider/model/prompt snapshot,
OCR run/generation/revision/source hash và canonical/manifest hash. Thay cấu hình
ModelOps về sau không sửa lịch sử. Không có credential hoặc endpoint tùy ý trong
DTO quyết định. Không có hành động sửa nội dung phiên bản đã đăng ký: muốn thay
nội dung, tạo Compiler run mới và đăng ký phiên bản mới.

## Quyền và trạng thái

| Thao tác | Vai trò workspace |
|---|---|
| Đăng ký tài liệu/phiên bản | admin, editor |
| Duyệt | admin, reviewer |
| Xuất bản hoặc thu hồi | admin |
| Đọc danh sách, lịch sử, bản nháp, bản đang xuất bản | admin, editor, reviewer, member |

Quản trị nền tảng dùng quyền hiện hữu trong resolver. Không bắt buộc người tạo và
người duyệt khác nhau trong bản này. Không gán quyền từ model/prompt/body request.
Quyền được kiểm lại lúc commit, nên preview không giữ được quyền đã bị thu hồi.

```text
draft → approved → published
published cũ → superseded     (khi bản approved khác được xuất bản)
approved | published → withdrawn
superseded | withdrawn → approved → published   (phục hồi bằng quyết định mới)
```

Partial unique index ở DB bảo đảm tối đa một bản `published` cho mỗi document.
Thay thế là một transaction: bản cũ superseded, bản mới published, decision và
audit cùng commit. Lịch sử ghi ID bị thay thế. Không tự tái kích hoạt bản cũ khi
thu hồi bản hiện hành; muốn phục hồi phải duyệt và xuất bản lại.

## API

Từ `0002_operational_readiness`, duyệt cần xác nhận review của con người theo
[hợp đồng review gate](publication-review-gate.md). Model không tự duyệt. Client
cũ không gửi `review_ack` nhận `409 publication_review_required`; không có bypass
ngầm. Bản đã duyệt bằng hợp đồng cũ cần thu hồi rồi duyệt lại trước lần xuất bản
hoặc thay thế tiếp theo. Thu hồi vẫn dùng được khi review thiếu/hỏng.

Tiền tố `P`:
`/platform/v1alpha1/workspaces/{workspace_id}/collections/{collection_id}/compiled-documents`.

| Method | Đường dẫn | Mục đích |
|---|---|---|
| POST | `P` | Tạo tài liệu và phiên bản 1 từ Compiler completed |
| GET | `P` | Danh sách tài liệu |
| GET | `P/{doc}` | Metadata tài liệu |
| POST | `P/{doc}/versions` | Đăng ký phiên bản tiếp theo từ Compiler completed |
| GET | `P/{doc}/versions` | Lịch sử phiên bản, mới trước |
| GET | `P/{doc}/versions/{ver}` | Metadata/version/provenance/hash |
| GET | `P/{doc}/versions/{ver}/draft` | Nội dung nguyên bản, kể cả withdrawn/superseded |
| POST | `P/{doc}/versions/{ver}/decision-preview` | Xem trước approve/publish/withdraw |
| POST | `P/{doc}/versions/{ver}/decisions` | Xác nhận đúng preview đã xem |
| GET | `P/{doc}/history` | Decision theo sequence tăng dần |
| GET | `P/{doc}/published` | Chỉ đọc bản hiện hành có quyết định và nguồn hợp lệ |

List/history hỗ trợ `limit=1..100`, `offset>=0`. Đăng ký và commit decisions bắt buộc
`Idempotency-Key` (1–128 ký tự ASCII chữ/số/`_.:-`). Tạo mới trả 201, replay đăng ký
trả 200 cùng version. Quyết định trả 200; cùng key/body trả receipt cũ, không áp lại.
Key trùng nhưng body/path khác trả 409. Dùng key mới không vượt được preview đã dùng.

Tạo tài liệu (thay ID mẫu bằng run đã hoàn tất):

```json
{
  "document_key": "chi-tieu-tuyen-sinh",
  "title": "Chỉ tiêu tuyển sinh",
  "compilation_run_id": "cmp_<id>"
}
```

Thêm phiên bản vào tài liệu đã có:

```json
{"compilation_run_id": "cmp_<run_moi>"}
```

Preview quyết định:

```json
{"action": "approve", "reason": "Đã xem bản nháp và đối chiếu nguồn."}
```

Preview trả `id`, `preview_sha256`, actor, action/reason, bundle hash, sequence,
bản đang hiệu lực và `expires_at`. Chưa áp trạng thái hoặc tạo decision ở bước này.
Xác nhận qua POST decisions, có Idempotency-Key riêng:

```json
{"preview_id": "pprev_<id>", "preview_sha256": "<sha256_trong_preview>"}
```

Preview mặc định sống 300 giây, cấu hình bởi `PUBLICATION_PREVIEW_TTL_SECONDS`
(1–3600). Preview chỉ dùng cho chính actor/document/version/action đã ghim. Hash
không khớp, hết hạn, trạng thái/sequence/bản active thay đổi đều bị chặn; client
phải tải lại và chủ động xem trước quyết định mới. Body không nhận status, actor,
scope override, cờ model tự duyệt hoặc source hash tự khai.

## Kiểm tra nguồn và serving

Đăng ký/duyệt/xuất bản/đọc nội dung đối chiếu:

- Compiler completed và đúng collection/workspace; snapshot/binding nguồn không đổi.
- Input snapshot, draft JSON, Markdown, canonical và manifest đều đọc qua BlobStore,
  kiểm size/SHA256; tệp gốc vẫn đọc được và khớp revision hash.
- Citation map và bảng nguồn trùng canonical; bundle/provenance khớp phiên bản.
- Duyệt/xuất bản/read published yêu cầu từng nguồn vẫn là revision hiện hành.
- Publish cần **receipt duyệt** khớp bundle và state_version, không chỉ cờ approved.
  Read published cần receipt publish khớp phiên bản/hash/state.

Nguồn có revision mới sau duyệt làm publish/read published trả 409
`publication_source_stale`. Không ghi trạng thái giả hoặc tự chuyển sang nguồn mới.
Metadata/lịch sử giữ nguyên; bản cũ vẫn được đọc qua route version khi bytes còn
nguyên vẹn. Thu hồi không buộc đọc artifact/nguồn, để admin vẫn có thể chặn bản bị
mất/hỏng/stale; không xóa nguồn hoặc output để thu hồi.

`GET .../published` là ranh giới dành cho bước indexing sau này. Không dùng list
version hoặc route draft làm đầu vào indexing/RAG. Response có `document`,
`version`, `decision`, `content`. **`version.status` là trạng thái hiệu lực**;
`content` giữ nguyên output Compiler, nên các cờ `publication_status=draft` và
`requires_review=true` trong đó vẫn mô tả trạng thái lúc Compiler tạo output.
Không sửa bytes gốc để thể hiện quyết định xuất bản mới.

Read nội dung trả ETag và `Cache-Control: private, no-store`. Published ETag gồm
bundle + decision + sequence; endpoint kiểm quyền/trạng thái/nguồn mỗi lần gọi.
Không có cache công khai hoặc tự làm embedding/index/publication cho dữ liệu cũ.

## Storage Windows

Luồng upload/artifact dùng LocalBlobStore hiện hữu. Sửa trường hợp writer cùng đích
gặp sharing violation: 64 khóa stripe cố định trong process, I/O vẫn ở `to_thread`;
đọc bị PermissionError được thử tối đa 6 lần với tổng chờ tối đa 155ms. Sau replace
bị từ chối, chỉ coi ghi thành công khi đọc được **toàn bộ bytes khớp**. Khác bytes,
quyền bị từ chối lâu dài hoặc lỗi staging vẫn báo lỗi và giữ file đã commit.
Không coi cơ chế này là khóa phân tán hoặc bảo đảm chống mọi lỗi filesystem.

## Vận hành và phạm vi

Baseline chỉ tạo bảng v1, chưa áp trên DB phục vụ trong đợt này. Downgrade
từ chối xóa bằng chứng. Không có hành động tự seed decision hoặc publish dữ liệu có
sẵn. Kiểm thử dùng DB tạm tự dọn, source PDF và OCR/chat giả lập; lifecycle không
gọi LLM. Chưa có UI, full-text/vector index hoặc RAG v1 ở bước này.

[Báo cáo Context646](../../docs/bao_cao/context646/REVIEW.md).
