# Phiên 817 — So MinerU và Nemotron trên PDF 2699

Ngày 2026-11-02. User yêu cầu thêm một bài test trên PDF cung cấp để chọn OCR ít lỗi; sau đó xác nhận tiếp tục chờ MinerU hoàn tất.

## Phạm vi và phương pháp

- PDF 29 trang scan, SHA256 `84a19db7fcb5e20bf13092088639eecd22cf955169021335d0b56e4bf8e41d77`, kiểm lại sau chạy. Giữ file gốc và raw trong artifact riêng, không thêm corpus vào Git.
- Nemotron lấy runtime/credential qua ModelOps được cấp, alias nemotron-parse, không đổi cấu hình. Một request/trang, concurrency2, output8192; render đích176DPI fit ảnh1664×2048, DPI thực142,258/175,107.
- MinerU gửi nguyên PDF qua API đã được user chỉ định, standard/auto, parser báo4.1.3; một create/upload. Hai lượt chạy tuần tự, không retry inference.
- Chốt gold ảnh trước đọc output:20đoạn/13trang/664từ/3053ký tự; trợ lý chép, chưa chấm độc lập. Giữ dấu, NFC/casefold/khoảng trắng/loại markup/unescape ký hiệu; không sửa chính tả. CER/WER chỉ đại diện mẫu.

## Kết quả thật

- Cả hai completed29/29, không trang rỗng. MinerU1663,89s, parser1654,583s; Nemotron batch inference+parse19,812s sau render. Boundary/pipeline khác, không phải benchmark tốc độ checkpoint có kiểm soát.
- MinerU7lỗi ký tự/CER0,229%,7lỗi từ/WER1,054%; Nemotron15lỗi ký tự/CER0,491%,16lỗi từ/WER2,410%.
- ProbeMinerU22/22, Nemotron21/22. Caption tên người ký có ở footnote lồng trong block image và Markdown MinerU; không kết luận thiếu do đọc sai tầng JSON.
- 26bảng MinerU rộng8cột,4mẫu số hàng khớp ảnh;5kiểm tra ghép hàng đạt. Nemotron26unsupported trong parser hiện tại (23grid_mismatch,3unbalanced_row); chẩn đoán chữ cùng hàng4/5, không promote bảng lỗi thành canonical. Không đồng nhất lỗi bảng với mất hết chữ.
- Chất lượng không hoàn hảo: MinerU còn nhầm dấu/từ; chưa nghiệm thu toàn bộ ô/nối trang, CER toàn file hay chữ trên con dấu. Giữ cảnh báo mất vùng ký tên PDF363 ở816.

## Kiểm chứng và giới hạn

`tmp/ocr817/run.py --resume-preflight` exit0: lần đầu assertion transport chặn trước request; sau xác minh openai_compatible thì chạy attempt1, không resend. `selfcheck.py`10PASS; `compare.py`, `inspect_outputs.py`exit0. Đã sửa script offline về caption/footnotes và colspan/rowspan, không đổi gold/model output. 31tệp MinerU kiểm hash,104bbox hợp lệ hình thức,28ảnh tồn tại. Console cp1252 và tên inspect.py trùng stdlib đã xử lý trong script test; không gọi lại model.

Artifact `tmp/ocr817/REPORT.md`, raw/MD/JSON/ZIP, receipts, gold manifest và metrics. Không sửa app/DB/ModelOps/publication/index; không restart/commit/push. App build/unit NOT RUN vì chỉ test ad hoc và docs.

Kết luận: ưu tiên MinerU cho yêu cầu ít lỗi trên hai PDF đã thử, giữ rà soát sau OCR; tích hợp/chuyển mặc định chưa thực hiện. Không tuyên bố tổng quát cho mọi tài liệu.
