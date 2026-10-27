# Ranh giới module

| Domain | Sở hữu dữ liệu | Phụ thuộc được phép |
|---|---|---|
| identity | actor, dev gate, SSO | platform |
| workspaces | workspace, membership, audit đơn vị | identity, platform |
| modelops | provider, key, defaults, allowlist theo workspace | workspaces (access), platform, ports |
| ocr | lượt xử lý OCR, trạng thái trang, artifact OCR (ảnh trang, raw, canonical, markdown, manifest) | modelops (public_api, knowledge (public_api chỉ đọc), workspaces (access), platform, ports |
| knowledge | kho, nguồn, revision, chunk, fact, index, publication | modelops (public_api), workspaces (access), ports, policies |
| rag | truy xuất, evidence, answer | knowledge (public_api, chỉ đọc), modelops, ports |
| assistants | cấu hình chatbot, runtime chat | rag (public_api), modelops, knowledge |
| tools / workflows | tool registry, DAG | assistants, knowledge, tools |
| evaluation | bộ đề, lần chạy, metric | rag, modelops |

## Quy tắc

- `public_api.py` là **cửa duy nhất** để domain khác gọi vào.
- `workspaces.access` là **cửa duy nhất** để kiểm quyền workspace; không tự so sánh
  `workspace_id` trong service.
- Không import `models.py` chéo domain (MVP cho phép `rag` đọc `knowledge.models`
  chỉ-đọc, có test cấm ghi).
- **Repository (kho tài liệu tập trung) đã bị loại bỏ** khỏi v1 theo ADR-007 và
  quyết định 2026-10-26. Không tạo lại domain `repository` hay cột `repository_*`.
- Từ Context637, nguồn file và revision bất biến thuộc trực tiếp `knowledge/`
  (`collections/`, `sources/`, `artifacts/`); mọi truy vấn đi qua
  `knowledge/policies/access.py` với `workspace_id` đã được resolver xác nhận.
- Từ Context640, `ocr/` sở hữu toàn bộ bằng chứng xử lý (`ocr_processing_runs`,
  `ocr_run_pages`, `ocr_run_artifacts`). Nó **đọc** revision qua
  `knowledge.public_api.resolve_revision_scope/read_revision_bytes` và **gọi** ModelOps
  qua `modelops.public_api.resolve_ocr_runtime`; không import `knowledge.models`,
  không tự mở storage bằng đường dẫn client gửi lên.
- `ocr/` không phụ thuộc `rag`/`assistants`; Compiler (batch sau) chỉ đọc snapshot
  `GET .../processing-runs/{run_id}/evidence`, không ghi ngược vào `ocr/`.

Nguồn file/revision thuộc Knowledge; upload trực tiếp vào collection đã triển khai (Context637). Workspace resolver là cổng kiểm quyền; provider/key quản lý tập trung, grants và defaults tách biệt. Bằng chứng OCR thuộc `ocr/` và chỉ được đọc qua public API (Context640).
