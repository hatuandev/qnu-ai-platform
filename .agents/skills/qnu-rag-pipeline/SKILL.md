---
name: qnu-rag-pipeline
description: >-
  Use this skill when configuring, tuning, debugging, or extending the Hybrid RAG engine on QNU AI Platform.
  Covers Qdrant vector indexing, PostgreSQL FTS lexical search, Reciprocal Rank Fusion (RRF k=60),
  Cross-Encoder Reranking with Graceful Fallback, Structured Fact Layer, and Citation Guardrails.
---

# Hướng Dẫn Vận Hành & Tối Ưu Hybrid RAG Pipeline

Tài liệu hướng dẫn chuyên sâu về "Trái tim" hỏi đáp thông minh của **QNU AI Platform** ([app/modules/rag/](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/backend/app/modules/rag)).

---

## 1. Kiến Trúc Luồng Hybrid Retrieval Đa Tầng

```mermaid
graph TD
    Query[Câu hỏi người dùng] --> Cache{Semantic Cache?}
    Cache -- Trùng khớp >=0.95 --> FastReturn[Trả câu trả lời ngay lập tức]
    Cache -- Chưa có trong cache --> ConcurrentSearch[Song song 2 luồng tìm kiếm]
    
    ConcurrentSearch --> DenseSearch[Qdrant: BGE-M3 Dense Vector 1024d]
    ConcurrentSearch --> SparseSearch[Postgres: Lexical Full-Text Search]
    
    DenseSearch --> RRF[Reciprocal Rank Fusion - RRF k=60]
    SparseSearch --> RRF
    
    RRF --> RerankCheck{BGE-Reranker Online?}
    RerankCheck -- Có --> CrossEncoder[BAAI/bge-reranker-v2-m3: Top 5]
    RerankCheck -- Không / Timeout --> FallbackRRF[Graceful Fallback: Giữ nguyên RRF]
    
    CrossEncoder --> FactLayer[Structured Fact Layer: Bảng Điểm chuẩn / Học phí]
    FallbackRRF --> FactLayer
    
    FactLayer --> CitationGuard[Citation Guard: Kiểm tra độ bám sát Ngữ cảnh]
    CitationGuard -- Đạt chuẩn --> Composer[AnswerFormatPlanner: Sinh bảng/checklist/đoạn văn]
    CitationGuard -- Thiếu căn cứ --> PoliteRefusal[No-Answer Policy: Trả số Hotline Tuyển sinh QNU]
```

---

## 2. Các Thành Phần & Quy Tắc Tinh Chỉnh

### 1. Vector Indexer ([vector_indexer.py](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/backend/app/modules/rag/vector_indexer.py))
- **Mô hình Embedding**: `BAAI/bge-m3` (độ dài vector: 1024 chiều).
- **Khoảng cách**: Cosine Distance.
- **Index Batching**: Đẩy từng lô 32 chunks để tối ưu băng thông mạng và RAM của Qdrant.
- **Payload Filter**: Luôn gắn bộ lọc theo `collection_id`, `tenant_id`, và `is_active=true` để bảo vệ dữ liệu đa người thuê (Multi-tenancy).

### 2. Reciprocal Rank Fusion ([fusion.py](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/backend/app/modules/rag/fusion.py))
- Công thức chuẩn:
  $$RRF(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{1}{k + r_m(d)}$$
- Hằng số $k = 60$ theo chuẩn công nghiệp, giúp cân bằng hoàn hảo giữa kết quả tìm kiếm ngữ nghĩa và tìm kiếm từ khóa chính xác.

### 3. Cross-Encoder Reranker ([reranker.py](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/backend/app/modules/rag/reranker.py))
- Tái xếp hạng Top-K (mặc định lấy 8 chunks ban đầu, rerank chọn ra 5 chunks tốt nhất).
- **Nguyên tắc Chịu Lỗi**: Bắt buộc bọc khối gọi API trong `try/except`. Nếu microservice reranker bị offline hoặc chậm quá 3 giây, tự động fallback lấy top từ danh sách RRF mà không làm gián đoạn câu trả lời của người dùng.

### 4. Structured Fact Layer ([facts.py](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/backend/app/modules/rag/facts.py))
- Đối với câu hỏi về điểm chuẩn, chỉ tiêu, mã ngành: Ưu tiên tra cứu thẳng vào bảng `knowledge_facts`.
- Dữ liệu dạng sự thật sẽ được render thành **Bảng Markdown** chuẩn, tuyệt đối không để LLM đoán số liệu.

### 5. Citation Guard ([citation_guard.py](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/backend/app/modules/rag/citation_guard.py))
- Trích dẫn bắt buộc phải có: `title`, `section` (Điều/Khoản), `page_number` và trích đoạn ngắn `quote`.
- **No-Answer Policy**:
  - Tuyển sinh: Cung cấp Hotline Tuyển sinh ĐH Quy Nhơn `0256.3846.156` hoặc Email `tuyensinh@qnu.edu.vn`.
  - Quy chế học vụ: Hướng dẫn liên hệ Phòng Đào tạo (P.108 Nhà A1).
