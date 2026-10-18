# Phiên503 — Sơ đồ luồng xử lý RAG hiện tại

## Phạm vi

User yêu cầu vẽ luồng RAG hiện tại. Chỉ tạo artifact/tài liệu; không sửa runtime,
DB/config, nguồn/vector, không gọi inference, restart, deploy hoặc Git.
Đọc PROJECT_CONTEXT và đối chiếu mã thay vì lấy mô tả cũ làm hiện trạng.

Skill: diagram-design và qnu-rag-pipeline. Marker `.diagram-design` chọn profile
`qnu-teal`; đọc profile đã có, không sửa marker/profile/skill. Chọn flowchart tĩnh,
không có semantic pattern chuyên biệt phù hợp hơn; chia ba hình để mỗi hình
không quá9 node/12 connector. Canvas1280×720, typography presentation.

## Kết quả

- Artifact: [Luồng RAG hiện tại](../diagrams/rag-current-2026-10-16.html).
- Hình01: hội thoại → guard/snapshot → score tool / evidence / fact_hybrid.
  Có hỏi làm rõ và trả sớm cho act tiếp nối đã tái xác minh.
- Hình02: enumeration → glossary/cache → facts/table → hybrid → generate →
  numeric/visible audit → trả kết quả hoặc canonical prose recovery.
- Hình03: canonical snapshot/topic → BM25 + heading children → rerank/packing →
  chọn passage IDs → binding/verifier/coverage → trả có nguồn hoặc không công bố
  đáp án chưa chắc. Có nhánh repack một lần sau context overflow ở proposal.
- Ghi rõ: Hybrid lexical là PostgreSQL FTS, không phải BM25; BM25 ở evidence/
  recovery. Các K khác nhau. Không DAG và không tenant/workspace như biên dữ liệu.
- Nguồn đối chiếu: assistant_rag_chat.py; rag/service.py; retriever.py;
  evidence_pipeline.py; prose_fallback.py; prose_selection.py; response_audit.py;
  evidence_claims.py; evidence_verification.py. Đây là sơ đồ mã, không xác nhận
  runtime WebUI đã reload mã cuối.

## Giản lược có nêu rõ

Gộp guard/snapshot, expansion/fusion/rerank, binding/verifier/audit. Row anchors
được kiểm tra ở hơn một vị trí trong code nhưng gộp một ô đối soát bảng/dòng.
Ingestion, cache write, logging, provider retry/fallback nằm trong chú thích,
không tạo thêm sơ đồ hạ tầng. Nhánh Evidence opt-in có mô tả riêng; không nhầm
với canonical prose fallback. Không khẳng định mọi assistant đều chạy fact_hybrid.

## Kiểm chứng

- `.\backend\.venv\Scripts\python.exe .agents/skills/diagram-design/scripts/self_check.py docs/diagrams/rag-current-2026-10-16.html`
  (cwd root): **PASS**, exit0. Accessible SVG/single-file safety,3 hình tĩnh,
  không JavaScript, mỗi title/desc có ID riêng.
- Playwright từ dependency bundle render file cục bộ: **PASS**, exit0; đã xem
  cả3 ảnh QA, sửa một label che đường return ở hình03 rồi render/xem lại.
  Ảnh nội bộ `backend/storage/rag503-qa-0.png`..`rag503-qa-2.png`, không phải
  bản export giao người dùng. Không tạo SVG/PNG export riêng khi chưa được hỏi.
- Browser measurements:3SVG, font Geist và Instrument Serif loaded; không text
  vượt viewBox, không tên/sublabel dài quá312px. Font dự phòng offline ghi trên trang.
- Tool open_in_codex trả **queued** cho browser tab file HTML; không tuyên bố
  người dùng đã nhìn thấy tab.
- UTF-8/no-BOM/LF trên các file batch, liên kết mới503 và whitespace: **PASS**.
  Quét link toàn lịch sử WORK_LOG phát hiện link cũ phiên216 thiếu tệp; ngoài
  phạm vi, không sửa hoặc coi toàn bộ lịch sử link đã PASS.
- **NOT RUN**: pytest, FE build, benchmark/inference, UI chatbot. Không chạy test
  ứng dụng cho thay đổi sơ đồ thuần tài liệu; số đo phiên502 chỉ là lịch sử được dẫn.

Đã bổ sung link sơ đồ vào quy trình03, nhật ký/index, WORK_LOG, PROJECT_CONTEXT
và snapshot503; không đổi hành vi quy trình.
