import { DevAutoLoginError } from "@/app/auth/v1/dev-auto-login";

/**
 * Turns a dev-bridge failure into an actionable message.
 *
 * These strings name the file and variable to check, never a credential value.
 */
export function describeDevAutoLoginError(error: unknown): string {
  if (error instanceof DevAutoLoginError) {
    switch (error.code) {
      case "dev_bridge_disabled":
        return "Tự đăng nhập local đang tắt. Đặt QNU_DEV_AUTO_LOGIN=true trong frontendV1/.env.local rồi khởi động lại dev server.";
      case "dev_bridge_forbidden":
        return "Dev server từ chối yêu cầu vì không cùng origin hoặc không phải host loopback. Mở ứng dụng qua http://127.0.0.1:3001.";
      case "dev_bridge_misconfigured":
        return "Cầu nối thiếu QNU_DEV_ACCESS_KEY hoặc QNU_API_PROXY_TARGET không trỏ tới backend loopback. Kiểm tra frontendV1/.env.local.";
      case "dev_bridge_method_not_allowed":
        return "Cầu nối chỉ nhận POST. Tải lại trang để thử lại.";
      case "invalid_credentials":
        return "Access key local không đúng. QNU_DEV_ACCESS_KEY phải trùng DEV_ACCESS_PASSWORD của backendV1.";
      case "dev_gate_disabled":
        return "BackendV1 đang tắt dev access gate. Đặt DEV_AUTH_ENABLED=true hoặc đăng nhập qua QNU SSO.";
      case "backend_not_ready":
        return "BackendV1 chưa ký được token. Kiểm tra SECRET_KEY tối thiểu 32 byte.";
      case "backend_unreachable":
        return "Cầu nối không kết nối được backendV1 ở cổng 8002. Khởi động backend rồi thử lại.";
      case "network_unreachable":
        return "Không gọi được cầu nối đăng nhập của dev server. Tải lại trang hoặc kiểm tra dev server còn chạy ở http://127.0.0.1:3001.";
      case "invalid_login_response":
        return "BackendV1 trả phản hồi đăng nhập thiếu access_token. Kiểm tra lại endpoint /auth/login.";
      default:
        return error.message;
    }
  }
  return error instanceof Error
    ? error.message
    : "Không tự đăng nhập được bằng cấu hình local.";
}
