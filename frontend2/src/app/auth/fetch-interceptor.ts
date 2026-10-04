/**
 * Global Fetch Interceptor for QNU AI Platform — Automatic SSO Bearer Token Injection
 *
 * Intercepts all outgoing window.fetch calls targeting '/platform/*' API endpoints,
 * automatically injecting the active QNU SSO access token (Bearer Token) and 'credentials: "include"'.
 */

import { getAccessToken, getUserManager } from "@/app/auth/oidc";

let isInterceptorInstalled = false;

export function installAuthFetchInterceptor(): void {
  if (isInterceptorInstalled || typeof window === "undefined") {
    return;
  }
  isInterceptorInstalled = true;

  const originalFetch = window.fetch;

  window.fetch = async (
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : (input as Request).url;

    // Chỉ can thiệp các lệnh gọi API Backend thuộc nền tảng QNU AI Platform
    if (url.includes("/platform/") || url.startsWith("/platform")) {
      const headers = new Headers(init?.headers);
      const token = getAccessToken();

      if (
        token &&
        !headers.has("Authorization") &&
        !headers.has("authorization")
      ) {
        headers.set("Authorization", `Bearer ${token}`);
      }

      const modifiedInit: RequestInit = {
        ...init,
        headers,
        credentials: init?.credentials ?? "include",
      };

      const response = await originalFetch(input, modifiedInit);

      // Xử lý 401 khi token đã hết hạn: cố gắng kích hoạt silent renew ngầm
      if (response.status === 401 && token) {
        try {
          const mgr = getUserManager();
          mgr.signinSilent().catch(() => {
            // Silent renew thất bại (hết hạn hoàn toàn hoặc chưa cấp quyền offline_access)
          });
        } catch {
          // ignore silent renew failure
        }
      }

      return response;
    }

    return originalFetch(input, init);
  };
}
