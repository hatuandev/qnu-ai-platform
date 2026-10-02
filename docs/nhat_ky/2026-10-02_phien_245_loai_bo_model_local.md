# NHẬT KÝ LÀM VIỆC: LOẠI BỎ MODEL LOCAL, CHUYỂN SANG PROVIDER API

- **Thời gian**: 2026-10-02
- **Kỹ sư / Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**:
  - Xóa toàn bộ runtime AI chạy local khỏi QNU AI Platform.
  - Chỉ sử dụng model được phân giải động qua provider và API key trong ModelOps DB.

## 1. Thay đổi kiến trúc

- Xóa adapter local vLLM/Ollama, Docling và EasyOCR; bỏ SentenceTransformers khỏi pipeline embedding.
- Xóa dependency `docling`, `easyocr`, `sentence-transformers` cùng chuỗi phụ thuộc Torch/Transformers khỏi lockfile.
- Chuẩn hóa InferenceService và ModelRuntimeResolver: mọi provider runtime phải có API key hợp lệ; hết hạn mức sẽ xoay khóa rồi chuyển provider dự phòng.
- Chuyển embedding/reranker sang Cloudflare Workers AI API. Tên `BGE-M3` còn xuất hiện trong cấu hình Cloudflare là model cloud, không chạy local.
- Chuyển OCR scan sang Gemini/Mistral API; giữ PyMuPDF cho trích xuất lớp text số vì đây là parser native, không phải model AI local.
- Migration `20261002_remove_local_models` xóa provider local và loại các bước local khỏi combo chain, model combo và vision adapter trong PostgreSQL.
- Hai giao diện quản trị đã bỏ lựa chọn, badge, icon và nội dung hướng dẫn liên quan model local.

## 2. Dọn dữ liệu và cache

- PostgreSQL sau migration: `0` provider local và không còn local entry trong System Model Defaults.
- Xóa cache BGE-M3: `4.564.396.159` byte.
- Xóa cache EasyOCR: `113.702.468` byte.
- Xóa cache Docling: `530.003.106` byte.
- Tổng dung lượng giải phóng: khoảng `5,21 GB`.

## 3. Xác minh

- Ruff phạm vi runtime/test/migration thay đổi: đạt.
- 69 test trọng điểm ModelOps, OCR, RAG và key rotation: đạt.
- Build `frontend`: đạt.
- Build `frontend2`: đạt.
- Full suite: 498 đạt; các lỗi còn lại thuộc luồng xuất artifact, lọc facts và quyền dọn thư mục tạm đã tồn tại ngoài phạm vi chuyển đổi model local.
- Full Ruff còn 32 lỗi trong các script chẩn đoán/scratch cũ; phạm vi mã nguồn đã sửa không có lỗi.

## 4. Trạng thái

- **HOÀN THÀNH** chuyển runtime sang provider API key.
- Cloudflare BGE-M3/BGE-Reranker, Gemini, Mistral, OpenAI và các provider custom tiếp tục được cấu hình động qua `/models`.
