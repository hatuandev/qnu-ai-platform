const studentGuideSteps = [
  {
    title: "Kiểm tra thông tin sinh viên",
    description:
      "Từ trang Tổng quan, mở Đăng ký phòng và kiểm tra mã sinh viên, họ tên, lớp, khoa, email trường và số điện thoại. Nếu mã sinh viên hoặc họ tên chưa đúng, hãy liên hệ Phòng Công tác sinh viên để cập nhật dữ liệu UIS.",
  },
  {
    title: "Tạo và nộp hồ sơ đăng ký",
    description:
      "Chọn đợt đăng ký đang mở, bổ sung thông tin liên hệ, khai báo đối tượng ưu tiên và tải minh chứng nếu có. Bạn có thể lưu nháp để hoàn thiện sau; hãy kiểm tra cam kết và bấm Nộp hồ sơ trước hạn. Mỗi đợt chỉ được nộp một hồ sơ.",
  },
  {
    title: "Theo dõi kết quả xét duyệt",
    description:
      "Mở Lịch sử đăng ký để xem trạng thái hồ sơ và ghi chú của cán bộ. Khi hồ sơ có trạng thái Yêu cầu bổ sung, cập nhật đúng nội dung được yêu cầu rồi nộp lại trong thời gian đợt đăng ký còn mở.",
  },
  {
    title: "Chọn và xác nhận phòng",
    description:
      "Sau khi hồ sơ được duyệt và cổng chọn phòng mở, vào Chọn phòng để xem loại phòng, số chỗ còn lại và mức phí. Chọn phòng phù hợp và kiểm tra lại chỗ ở đã được ghi nhận trên Tổng quan sinh viên.",
  },
  {
    title: "Thanh toán và nộp biên lai",
    description:
      "Vào Thanh toán, quét mã QR hoặc chuyển khoản đúng số tiền và đúng nội dung hệ thống cung cấp. Sau đó tải ảnh hoặc PDF biên lai lên và theo dõi trạng thái đối soát; không tự sửa nội dung chuyển khoản.",
  },
  {
    title: "Theo dõi thông báo và yêu cầu hỗ trợ",
    description:
      "Kiểm tra Thông báo thường xuyên để không bỏ lỡ hạn bổ sung, chọn phòng hoặc thanh toán. Nếu gặp lỗi, vào Hỗ trợ sinh viên, mô tả rõ vấn đề và cung cấp mã sinh viên cùng ảnh chụp màn hình khi cần.",
  },
] as const;

export function StudentUserGuide() {
  return (
    <div className="space-y-3 text-sm">
      <div className="rounded-lg border bg-muted/20 p-3">
        <p className="font-semibold text-foreground">
          Quy trình dành cho sinh viên
        </p>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
          Thực hiện lần lượt các bước dưới đây và luôn kiểm tra thời hạn của
          từng đợt đăng ký.
        </p>
      </div>

      <ol className="space-y-2.5">
        {studentGuideSteps.map((step, index) => (
          <li
            key={step.title}
            className="grid grid-cols-[2rem_minmax(0,1fr)] gap-3 rounded-lg border p-3"
          >
            <span
              aria-hidden="true"
              className="flex size-8 items-center justify-center rounded-md bg-primary/10 text-xs font-bold text-primary"
            >
              {index + 1}
            </span>
            <div className="min-w-0 space-y-1">
              <p className="font-semibold leading-5 text-foreground">
                {step.title}
              </p>
              <p className="text-xs leading-relaxed text-muted-foreground">
                {step.description}
              </p>
            </div>
          </li>
        ))}
      </ol>

      <div
        role="note"
        className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs leading-relaxed text-foreground"
      >
        Không chia sẻ tài khoản, mật khẩu hoặc mã xác thực. Hệ thống chỉ sử dụng
        email trường để định danh và gửi thông tin chính thức cho sinh viên.
      </div>
    </div>
  );
}
