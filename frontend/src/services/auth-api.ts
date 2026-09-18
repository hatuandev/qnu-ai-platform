import type { AuthStatusResponse } from "@/types/auth";
import { BASE_URL } from "./http-client";

/**
 * Service API cho phân hệ xác thực Dev Access Gate (Mật khẩu đơn giản)
 */
export async function loginWithPassword(accessKey: string): Promise<AuthStatusResponse> {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify({ access_key: accessKey }),
  });

  if (!res.ok) {
    let errorDetail = "Mật khẩu truy cập không chính xác";
    try {
      const errorJson = await res.json();
      if (errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export async function logout(): Promise<{ status: string; message: string }> {
  const res = await fetch(`${BASE_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });

  if (!res.ok) {
    throw new Error("Đăng xuất thất bại");
  }

  return res.json();
}

export async function getAuthStatus(): Promise<AuthStatusResponse> {
  try {
    const res = await fetch(`${BASE_URL}/auth/me`, {
      method: "GET",
      credentials: "include",
    });

    if (res.ok) {
      return res.json();
    }
    return { authenticated: false };
  } catch {
    return { authenticated: false };
  }
}
