# NHẬT KÝ LÀM VIỆC — PHIÊN #151
**Ngày thực hiện**: 20/09/2026  
**Tiêu đề**: Triển Khai Chặng 2: Domain Record Normalization, Data Quality Gate & Record-Aware Atomic Chunking

---

## 1. Bối Cảnh & Mục Tiêu

Tiếp nối Chặng 1 đã hoàn thành việc loại bỏ trùng lặp bảng và tái dựng bảng đa trang, Chặng 2 hiện thực hóa các yêu cầu trọng tâm của [`docs/ke_hoach/10_ke_hoach_chuan_hoa_markdown_qdrant_va_chat_luong_rag.md`](../ke_hoach/10_ke_hoach_chuan_hoa_markdown_qdrant_va_chat_luong_rag.md):
1. **Domain Record Normalization (P0.4)**: Chuyển đổi bảng Canonical thành các bản ghi nghiệp vụ nguyên tử (`AdmissionProgramRecord`, `CertificateConversionRecord`, `HistoricalAdmissionRecord`, `ImplementationTaskRecord`).
2. **Data Quality Gate (P0.7)**: Bộ kiểm định tự động phát hiện mâu thuẫn số liệu chéo bảng (như mã ngành Trí tuệ nhân tạo `7480107` vs `7480207`) $\rightarrow$ sinh issue `blocking` để đưa vào `review_pending` cho con người xác minh (Zero Hallucination).
3. **Record-Aware Atomic Chunking (P0.5)**: Cắt chunk theo từng thực thể nghiệp vụ nguyên tử (1 ngành = 1 chunk, 1 nhiệm vụ = 1 chunk), sinh `embedding_text` tự nhiên thay vì embed thô các ký tự bảng `|`.
4. **Structured Facts (P0.6)**: Nạp trực tiếp facts chính xác vào `knowledge_facts` để phục vụ truy vấn số liệu tuyệt đối.

---

## 2. Các Thay Đổi Kỹ Thuật Đã Triển Khai (Chặng 2 — P0.3 đến P0.6)

### 2.1. Bộ Chuẩn Hóa Văn Bản Có Kiểm Soát (`text_normalizer.py`)
- [`text_normalizer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/text_normalizer.py):
  * `normalize_encoding()`: Đảm bảo 100% Unicode NFC, loại bỏ BOM, null bytes, ký tự thay thế `\ufffd`.
  * `normalize_whitespace()`: Thu gọn khoảng trắng thừa nhưng bảo tồn ngắt đoạn tự nhiên `\n\n`.
  * `join_wrapped_paragraph_lines()`: Nối các dòng câu bị ngắt gãy vật lý trong PDF mà không có dấu kết thúc câu.
  * `is_administrative_heading()`: Nhận diện tiêu đề số La Mã (`I. MỤC ĐÍCH`), điều khoản pháp lý (`Điều 1.`), văn bản hành chính (`KẾ HOẠCH...`).

### 2.2. Bộ Bóc Tách Bản Ghi Nghiệp Vụ (`record_normalizer.py`)
- [`record_normalizer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/record_normalizer.py):
  * `AdmissionsRecordNormalizer`: Bóc tách đủ danh mục ngành (`AdmissionProgramRecord` với mã ngành 7 số, chỉ tiêu, các bộ 3 môn tổ hợp), bảng quy đổi IELTS/VSTEP (`CertificateConversionRecord`), điểm chuẩn và chỉ tiêu 2024–2025 (`HistoricalAdmissionRecord`).
  * `ImplementationPlanRecordNormalizer`: Bóc tách các nhiệm vụ (`ImplementationTaskRecord` với `task_code`, `category` forward-filled từ tiêu đề nhóm, đơn vị chủ trì, phối hợp, tiến độ, sản phẩm).

### 2.3. Cổng Kiểm Soát Chất Lượng Tri Thức (`quality_gate.py`)
- [`quality_gate.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/quality_gate.py):
  * `DataQualityGate`: Tự động đánh giá tài liệu và sinh `DocumentQualityReport`.
  * `CrossTableConflictValidator`: Phát hiện mâu thuẫn số liệu giữa bảng chính và phụ lục trong cùng tài liệu (ví dụ mã ngành Trí tuệ nhân tạo `7480107` ở bảng chính vs `7480207` ở phụ lục) $\rightarrow$ sinh issue `blocking` (`CONFLICTING_PROGRAM_CODE`), đánh dấu `passed = False` để kích hoạt Human-in-the-loop.

### 2.4. Record-Aware Atomic Chunking & Structured Facts
- [`chunker.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/chunker.py):
  * `AdmissionsRecordChunker`: 1 ngành = 1 atomic chunk kèm `entity_key = program:...`, sinh nội dung tự nhiên diễn giải tổ hợp và chỉ tiêu.
  * `ImplementationTaskChunker`: 1 nhiệm vụ = 1 atomic chunk kèm `entity_key = task:...`, đầy đủ thông tin đơn vị và tiến độ.
- [`facts.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/facts.py):
  * Bổ sung `extract_facts_from_domain_records()` đưa trực tiếp mã ngành, chỉ tiêu, tổ hợp, đơn vị chủ trì vào `knowledge_facts`.

---

## 3. Các Tệp Đã Tạo & Chỉnh Sửa

| Tệp | Hành Động | Mô Tả |
| :--- | :--- | :--- |
| [`normalization/text_normalizer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/text_normalizer.py) | `NEW` | Chuẩn hóa Unicode NFC, reflow câu ngắt gãy, nhận diện heading hành chính. |
| [`normalization/record_normalizer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/record_normalizer.py) | `NEW` | Bóc tách typed records: Tuyển sinh (ngành, điểm chuẩn, IELTS/VSTEP) và Kế hoạch nhiệm vụ. |
| [`normalization/quality_gate.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/quality_gate.py) | `NEW` | Cổng kiểm soát chất lượng, phát hiện mâu thuẫn mã ngành chéo bảng chặn publish. |
| [`normalization/__init__.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/__init__.py) | `MODIFY` | Export toàn bộ models, validators và normalizers. |
| [`chunker.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/chunker.py) | `MODIFY` | Bổ sung `AdmissionsRecordChunker` và `ImplementationTaskChunker` (Atomic Chunks). |
| [`facts.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/facts.py) | `MODIFY` | Bổ sung `extract_facts_from_domain_records` nạp facts có cấu trúc. |
| [`tests/test_domain_records_and_quality_gate.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_domain_records_and_quality_gate.py) | `NEW` | Bộ 8 unit tests kiểm thử trích xuất records, phát hiện mâu thuẫn và atomic chunking. |

---

## 4. Kết Quả Kiểm Thử (Verification)

- **Backend**:
  * `uv run ruff check .` $\rightarrow$ **All checks passed! (0 lỗi)**.
  * `pytest tests/test_table_reconstructor.py tests/test_domain_records_and_quality_gate.py` $\rightarrow$ **16/16 passed in 0.92s (100%)**.
- **Frontend**:
  * `npm run lint` $\rightarrow$ **165 files 0 lỗi**.
  * `npm run typecheck` $\rightarrow$ **0 lỗi**.
