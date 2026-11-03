# Phiên 838 — Ngân sách tự động cho Compiler và hỏi đáp trực tiếp

Compiler và API hỏi đáp trực tiếp chuyển yêu cầu không chỉ định mức sang ModelOps. Giao diện hỏi đáp để trống ngân sách theo mặc định. Giá trị người gọi đặt vẫn được kiểm tra. Giữ cơ chế chia phần hiện có của Compiler và ngân sách tạm tính khi thiếu metadata.

Phần còn lại gồm chế độ tự động cho cấu hình trợ lý đã lưu và API tích hợp, đồng bộ metadata tự động khi thêm model, và học có giới hạn từ phản hồi provider. Chưa gọi provider thật.
