/**
 * HTTP request functions for Authentication domain.
 */

import { v1Client, v1PublicClient } from "../v1-client";
import { authPaths } from "./endpoints";
import type {
  ActorResponse,
  DevLoginRequest,
  LogoutResponse,
  TokenResponse,
} from "./types";

export async function getMe(options?: {
  signal?: AbortSignal;
}): Promise<ActorResponse> {
  return v1Client.get<ActorResponse>(authPaths.me, options);
}

export async function loginDev(
  body: DevLoginRequest,
  options?: { signal?: AbortSignal },
): Promise<TokenResponse> {
  return v1PublicClient.post<TokenResponse>(authPaths.login, body, options);
}

export async function logout(options?: {
  signal?: AbortSignal;
}): Promise<LogoutResponse> {
  return v1Client.post<LogoutResponse>(authPaths.logout, {}, options);
}
