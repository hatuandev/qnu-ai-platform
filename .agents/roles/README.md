# Vai trò agent lập trình QNU

Các file dưới đây là hợp đồng vai trò có thể đọc/nạp thủ công trong coding assistant. Chúng không đăng ký dịch vụ, không tạo agent runtime cho chatbot và không bảo đảm IDE tự khám phá agent. Chỉ cấu hình tích hợp riêng cho host khi có yêu cầu và đã xác minh định dạng hỗ trợ.

| Vai trò | Khi dùng | Skill liên quan |
|---|---|---|
| [qnu-rag-architect](qnu-rag-architect.md) | Thiết kế một thay đổi RAG, review tác động | RAG, evaluation |
| [qnu-document-evidence-engineer](qnu-document-evidence-engineer.md) | OCR, bảng, canonical, provenance và publication | Ingestion, backend |
| [qnu-retrieval-engineer](qnu-retrieval-engineer.md) | Scope, retrieval, fusion, rerank, context | RAG, evaluation, ModelOps khi cần |
| [qnu-independent-verifier](qnu-independent-verifier.md) | Kiểm chứng độc lập diff và hành vi | Evaluation, gate theo phạm vi |
| [qnu-security-reviewer](qnu-security-reviewer.md) | Auth/tenant/secret/egress/tool side effect | ModelOps, backend và security rules |

Một agent có thể nhận vai trò cho task nhỏ. Chỉ giao nhiều agent khi host hỗ trợ và việc điều phối được phép; chia ownership file rõ, không để các agent sửa cùng vùng. Trước tác vụ biến đổi dữ liệu phức tạp phải nêu phương pháp/phạm vi, không dùng phân vai để vượt quyền người dùng.

Ví dụ nạp thủ công: "Đọc `.agents/roles/qnu-independent-verifier.md`, review diff hiện tại của module RAG và báo các lỗi tái hiện được; không sửa implementation hay gọi model thật."

Mọi vai trò dùng [handoff chung](handoff.md), root AGENTS.md và skill theo nhiệm vụ. Verifier/security/architect mặc định chỉ đọc; nhãn này là chỉ dẫn, không phải rào sandbox. Quyền thực vẫn do host và người dùng cấp.
