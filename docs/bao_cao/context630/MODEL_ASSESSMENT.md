# Context630 — Qwen3.8-27B, GPT-OSS 120B và Nemotron Parse

Đối chiếu nguồn chính thức ngày 2026-10-25. **Chưa có phép đo đối chứng trên QNU để kết luận model nào tốt hơn cho Compiler/RAG.** Không đổi model hoặc chạy A/B trong lượt sửa PDF này.

| Điểm so sánh | Qwen3.8-27B | GPT-OSS 120B |
|---|---|---|
| Kiến trúc | Dense 27B | MoE, tổng 117B; 5,1B kích hoạt mỗi token |
| Đầu vào | Văn bản, ảnh/video | Văn bản |
| Context gốc công bố | 262.144 token, có cơ chế mở rộng | 128K |

Nguồn: [Qwen model card](https://huggingface.co/Qwen/Qwen3.8-27B), [OpenAI GPT-OSS](https://openai.com/index/introducing-gpt-oss/), [GPT-OSS model card](https://huggingface.co/openai/gpt-oss-120b). Đây là thông số model, không phải context đã đo trên server của người dùng.

**Đánh giá cho QNU:** Qwen đáng ưu tiên trong lượt A/B tài liệu tiếp theo nhờ khả năng vision và context dài. Chưa thể suy chất lượng trích nguồn, phạm vi năm, JSON hoặc suy luận quan hệ từ số tham số. Cũng không suy Qwen nhanh hơn: dense và MoE khác nhau, còn phụ thuộc GPU, quantization, KV cache và cách phục vụ. Bảng benchmark Qwen công bố chưa có cột GPT-OSS 120B cùng phép thử.

Nếu thử sau, giữ cùng canonical evidence, câu hỏi, tiêu chí nguồn/năm/điều kiện và Quality Gate; ghi đúng model, quantization, reasoning và capacity thực tế. Tách lỗi parser khỏi lỗi model. Lượt hiện tại không thay model để cải thiện điểm số bằng cách đổi điều kiện đo.

## Nemotron-3.5-Parse

Đây là model chuyên bóc tách ảnh tài liệu, trả văn bản, nhãn layout, bbox và thứ tự đọc. Phù hợp làm một adapter extraction/OCR để so sánh với Paddle; không tự thay thế lớp canonical QNU, kiểm chứng nguồn hoặc Compiler. [NVIDIA model card](https://huggingface.co/nvidia/Nemotron-3.5-Parse).

Theo hướng dẫn hiện tại của NVIDIA, serving bằng vLLM cần plugin của model và vLLM `>=0.25.0,<0.33`; không chỉ dùng ví dụ triển khai tự sinh ở đầu trang. Khi có endpoint của người dùng, cần kiểm tra API/đầu ra thực tế trước khi tích hợp. Chưa cài đặt, restart hoặc cấu hình Nemotron trong lượt này.
