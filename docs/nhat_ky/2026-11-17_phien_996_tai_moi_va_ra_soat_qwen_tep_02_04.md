# Phiên 996 — Tải mới và rà soát tệp 02–04 bằng Qwen

## Phạm vi

Tải mới đúng ba tệp DOCX của bộ tuyển sinh vào kho thử `col_dd63b9a487cf`. Đối chiếu SHA-256 của phiên bản nhận qua API với tệp cục bộ. Chạy bóc tách, chính sách soát chính tả tự động, chuẩn bị nội dung chế độ tự động và rà soát bằng `qwen3.8-27b-q4`. Dùng API và hàm worker của Backend V1 hiện hành qua runner cục bộ. Model lấy từ ModelOps của môi trường phát triển. Các lượt rà soát được chạy lần lượt.

| Tệp | Bản nội dung chuẩn bị | Lượt rà soát |
| --- | --- | --- |
| 02 `Phuong huong tuyen sinh 2024_DHQN_final.docx` | `cmp_98319f8bd578` | `rvw_e1ff0068dbbd` |
| 03 `Du_lieu_RAG_Truong_Dai_hoc_Quy_Nhon_2026.docx` | `cmp_bb02c081b7e3` | `rvw_bfa5caaabfee` |
| 04 `Cam_nang_tuyen_sinh_Dai_hoc_Quy_Nhon_2025_day_du.docx` | `cmp_fbe67d7cb390` | `rvw_8c02e65f4a4b` |

Ba lượt bóc tách và chuẩn bị nội dung đều hoàn tất. Chính sách soát chính tả trả phạm vi `skipped` cho cả ba bản Word. Tệp 03 thực hiện thêm một lượt AI bổ sung, dùng 1.716 token trong bước chuẩn bị. Hai tệp còn lại lưu bản giữ nguyên nguồn và bỏ qua AI bổ sung theo kế hoạch tự động.

Runner ban đầu đọc sai đường dẫn của artifact và nhận 404 khi cả ba bản chuẩn bị đã lưu. Sau khi sửa sang endpoint `/draft.json`, tiếp tục từ ba mã bản nháp đã lưu; không tạo lại nguồn hay bản biên soạn.

## Rà soát

| Tệp | Kết quả | Số phần | Lượt gọi Qwen | Token vào / ra | Thời gian đo | Mục cần đối chiếu |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 02 | `completed`, `needs_attention` | 20/20 | 7 | 101.838 / 14.830 | 191,17 giây | 1 |
| 03 | `completed`, `no_issues_detected` | 1/1 | 1 | 44.162 / 14.341 | 360,72 giây | 0 |
| 04 | `completed`, `no_issues_detected` | 26/26 | 25 | 384.566 / 250.171 | 2.393,41 giây | 0 |

Lượt 02 phủ đủ 631 mục nguồn và 637 mục bản nháp. Có 11 phần đối chiếu ô bảng bằng phép so khớp nguyên văn, 1 phần tiêu đề xác minh cục bộ và 1 phần ghi giới hạn đối chiếu cho đoạn tham chiếu toàn bộ bảng 235 ô. Lượt 03 phủ đủ 74 mục nguồn và 76 mục bản nháp. Bản 03 có AI bổ sung nên luồng hiện hành rà soát một lượt toàn bản. Tệp 02 và 04 dùng prompt rà soát theo phần v4.

Lượt 04 phủ đủ 1.402 mục nguồn và 1.418 mục bản nháp. Một phần tiêu đề được xác minh cục bộ. Cả 25 phản hồi Qwen kết thúc `stop`, không có timeout hay sự kiện chia/gọi lại phần. Lượt gọi lớn nhất theo từng chiều ghi nhận 16.629 token vào và 10.986 token ra. Tổng toàn lượt là 634.737 token đo được, khác với ngân sách của một request.

## Kiểm chứng và giới hạn

- Upload, bóc tách, chuẩn bị và đọc báo cáo hoàn tất 3/3. Runner tiếp tục từ bản chuẩn bị đã lưu, kết thúc exit 0. Dùng `uv run --env-file ../.env python $qnuBatchScript` từ `backendV1` với script phiên trong thư mục tạm. Kiểm trạng thái phần đã lưu và số token từ phản hồi provider. Báo cáo Markdown và JSON từng tệp đã xuất vào thư mục tạm.
- Các báo cáo ghi độ phủ và phát hiện của lượt chạy. Chưa chấm ngữ nghĩa độc lập, chưa đo tốc độ A/B trên cùng bộ snapshot, chưa phát hành, lập chỉ mục hoặc chạy RAG. Không đổi mặc định ModelOps hoặc xóa dữ liệu.
