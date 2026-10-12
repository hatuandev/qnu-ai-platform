# Phiên #366 — Xác định runner PowerShell ẩn terminal

Ngày: 2026-10-12. Đối chiếu ảnh người dùng cung cấp với runner thực tế; chỉ chẩn đoán, chưa sửa/chạy/kill/restart dịch vụ.

Các dòng riêng lẻ Dang khoi chay Backend, Doi Backend khoi dong trong 2 giay, Dang khoi chay Frontend Studio khớp make.ps1:101–106, không phải recipe trong Makefile. make.ps1:102 và106 đều dùng Start-Process powershell -WindowStyle Hidden: cả cửa sổ BE và FE bị ẩn chủ động. Không có diff local make.ps1; Hidden cũng tồn tại trong commit c3fbfd3. Không thể kết luận dịch vụ health chỉ từ thông báo launcher.

Đính chính #365: chỉ đọc Makefile và worker script đã bỏ sót make.ps1. make.bat/Makefile mở cmd window, nhưng make.ps1 dev/dev1/dev2 dùng Hidden. Worker vẫn có chủ ý chạy nền/log riêng và PID guard không restart process cũ.

Hướng đề xuất: đổi hai launcher dev trong make.ps1 sang WindowStyle Normal khi người dùng yêu cầu khôi phục terminal hiển thị; worker giữ nền trừ khi người dùng muốn console riêng. Không cần sửa OCR, DB, frontend source hoặc reset dữ liệu. Chưa triển khai vì yêu cầu hiện tại là giải thích triệu chứng bằng ảnh.

Chỉ cập nhật journal/index/context/snapshot/work log; không tests ứng dụng vì không thay đổi runtime.
