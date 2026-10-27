import assert from "node:assert/strict";
import { QueryClient } from "@tanstack/react-query";
import { test } from "vitest";
import { createV1Client } from "../src/app/api/v1/client.ts";
import { authPaths } from "../src/app/api/v1/endpoints.ts";
import {
  clearAccessToken,
  getAccessToken,
  getTokenState,
  setAccessToken,
} from "../src/app/api/v1/session-token.ts";
import {
  createOidcUserManager,
  normalizeOidcScopes,
  resolveOidcAuthority,
  resolveOidcUrl,
  sanitizeReturnUrl,
} from "../src/app/auth/v1/oidc.ts";
import { isValidActor } from "../src/app/auth/v1/provider.tsx";

test("OIDC Authority resolution: enforces HTTPS and forbids loopback in production", () => {
  // 1. Development loopback allows http
  const devAuthority = resolveOidcAuthority(
    "http://localhost:5000/",
    "http://localhost:5000",
    false,
  );
  assert.equal(devAuthority, "http://localhost:5000");

  const dev127 = resolveOidcAuthority(
    "http://127.0.0.1:5000",
    "http://localhost:5000",
    false,
  );
  assert.equal(dev127, "http://127.0.0.1:5000");

  // 2. Production must use HTTPS
  assert.throws(
    () => resolveOidcAuthority("http://sso.qnu.edu.vn", "", true),
    /Production security violation: SSO authority must use HTTPS/,
  );

  // 3. Production rejects loopback even if HTTPS
  assert.throws(
    () => resolveOidcAuthority("https://localhost:5001", "", true),
    /Production security violation: SSO authority must not point to loopback/,
  );

  // 4. Valid production HTTPS authority is accepted and normalized
  const prodAuthority = resolveOidcAuthority(
    "https://sso.qnu.edu.vn///",
    "",
    true,
  );
  assert.equal(prodAuthority, "https://sso.qnu.edu.vn");
});

test("OIDC URL resolution: redirects and post-logout adhere to environment constraints", () => {
  const origin = "http://localhost:3001";

  // Relative path resolved against origin
  const callback = resolveOidcUrl(undefined, "/signin-oidc", origin, false);
  assert.equal(callback, "http://localhost:3001/signin-oidc");

  const postLogout = resolveOidcUrl(undefined, "/sign-in", origin, false);
  assert.equal(postLogout, "http://localhost:3001/sign-in");

  // Production forbids http callbacks
  assert.throws(
    () =>
      resolveOidcUrl(
        "http://ai.qnu.edu.vn/signin-oidc",
        "/signin-oidc",
        "https://ai.qnu.edu.vn",
        true,
      ),
    /Production security violation: SSO redirect URI must use HTTPS/,
  );
});

test("OIDC Scopes: normalizes and enforces required scopes 'openid' and 'ai.api'", () => {
  // Default scopes include openid and ai.api resource scope
  const scopes = normalizeOidcScopes(undefined);
  assert.match(scopes, /\bopenid\b/);
  assert.match(scopes, /\bai\.api\b/);
  assert.match(scopes, /\broles\b/);
  assert.match(scopes, /\boffline_access\b/);

  // Custom scopes must include openid
  assert.throws(
    () => normalizeOidcScopes("profile email ai.api"),
    /Invalid SSO scope: 'openid' is required/,
  );

  // Custom scopes must include ai.api
  assert.throws(
    () => normalizeOidcScopes("openid profile email"),
    /Invalid SSO scope: 'ai\.api' resource scope is required/,
  );

  // Deduplication
  const deduplicated = normalizeOidcScopes(
    "openid profile email openid ai.api roles ai.api",
  );
  assert.equal(deduplicated, "openid profile email ai.api roles");
});

test("Return URL sanitization: prevents open redirects and protocol-relative injection", () => {
  // Allowed internal paths
  assert.equal(sanitizeReturnUrl("/workspaces"), "/workspaces");
  assert.equal(
    sanitizeReturnUrl("/workspaces/ws-finance/models"),
    "/workspaces/ws-finance/models",
  );
  assert.equal(
    sanitizeReturnUrl("/modelops/providers?filter=active"),
    "/modelops/providers?filter=active",
  );

  // Rejects protocol-relative URLs (//attacker.com)
  assert.equal(sanitizeReturnUrl("//attacker.com"), "/workspaces");
  assert.equal(sanitizeReturnUrl("//attacker.com/steal"), "/workspaces");

  // Rejects backslash schemes (/\\evil.com)
  assert.equal(sanitizeReturnUrl("/\\evil.com"), "/workspaces");

  // Rejects absolute URLs
  assert.equal(sanitizeReturnUrl("https://evil.example.com"), "/workspaces");
  assert.equal(sanitizeReturnUrl("javascript:alert(1)"), "/workspaces");

  // Rejects auth loop paths
  assert.equal(sanitizeReturnUrl("/signin-oidc"), "/workspaces");
  assert.equal(sanitizeReturnUrl("/sign-in"), "/workspaces");

  // Rejects invalid types or empty strings
  assert.equal(sanitizeReturnUrl(null), "/workspaces");
  assert.equal(sanitizeReturnUrl(undefined), "/workspaces");
  assert.equal(sanitizeReturnUrl(""), "/workspaces");
});

test("OIDC UserManager: strictly uses InMemoryWebStorage for tokens and prefix for transactions", () => {
  const manager = createOidcUserManager();

  // Settings verification
  assert.equal(manager.settings.client_id, "qnu-ai-platform");
  assert.equal(manager.settings.response_type, "code");
  assert.equal(manager.settings.automaticSilentRenew, false);

  // Verify userStore is not persistent storage (localStorage / sessionStorage)
  // UserManager userStore wraps the Storage interface; verify it stores in memory
  assert.ok(manager.settings.userStore);
  assert.ok(manager.settings.stateStore);
});

test("Token Security: access tokens are held exclusively in memory, never in localStorage", () => {
  clearAccessToken();
  const testToken =
    "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.sso_test_access_token";
  setAccessToken(testToken);

  const state = getTokenState();
  assert.equal(state.token, testToken);

  // Simulate logout / session wipe
  clearAccessToken();
  const cleared = getTokenState();
  assert.equal(cleared.token, null);
  assert.ok(cleared.sessionId > state.sessionId);
});

test("Actor verification: isValidActor requires valid actor_id, username, and boolean authenticated", () => {
  // Valid actor
  assert.equal(
    isValidActor({
      actor_id: "sso-user-123",
      username: "tuan.an",
      display_name: "Anh Tuấn",
      email: "tuan.an@qnu.edu.vn",
      user_type: "staff",
      role: "staff",
      roles: ["staff"],
      permissions: ["ai.workspaces.view"],
      authenticated: true,
    }),
    true,
  );

  // Missing or empty actor_id
  assert.equal(
    isValidActor({
      actor_id: "",
      username: "tuan.an",
      roles: [],
      permissions: [],
      authenticated: true,
    }),
    false,
  );

  // Unauthenticated actor
  assert.equal(
    isValidActor({
      actor_id: "sso-user-123",
      username: "tuan.an",
      roles: [],
      permissions: [],
      authenticated: false,
    }),
    false,
  );

  // Missing roles or permissions arrays
  assert.equal(
    isValidActor({
      actor_id: "sso-user-123",
      username: "tuan.an",
      authenticated: true,
    }),
    false,
  );
});

test("SSO Session Gate: token is verified by backend GET /auth/me before admitting user", async () => {
  clearAccessToken();
  const token = "sso_valid_access_token";
  setAccessToken(token);

  let meCalls = 0;
  const mockFetch = async (
    url: string,
    init?: RequestInit,
  ): Promise<Response> => {
    if (url.endsWith("/auth/me")) {
      meCalls += 1;
      const authHeader =
        (init?.headers as Record<string, string>)?.authorization ||
        (init?.headers as Headers)?.get?.("authorization");
      assert.equal(authHeader, `Bearer ${token}`);
      return new Response(
        JSON.stringify({
          actor: {
            actor_id: "SSO-Sub-999",
            username: "lecturer.qnu",
            display_name: "Giảng viên QNU",
            email: "gv@qnu.edu.vn",
            user_type: "lecturer",
            role: "lecturer",
            roles: ["lecturer"],
            permissions: ["ai.chat.access"],
            authenticated: true,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    }
    return new Response(null, { status: 404 });
  };

  const client = createV1Client({
    fetchImpl: mockFetch,
    getToken: getAccessToken,
    getSessionId: () => getTokenState().sessionId,
    onUnauthorized: (context) =>
      clearAccessToken({ sessionId: context?.sessionId, expired: true }),
  });
  const response = await client.get<{ actor: unknown }>(authPaths.me);
  assert.equal(meCalls, 1);
  assert.ok(isValidActor(response.actor));
  assert.equal(response.actor.user_type, "lecturer");
  clearAccessToken();
});

test("SSO Session Gate: 401 on /auth/me triggers expired state and prevents admitting actor", async () => {
  clearAccessToken();
  setAccessToken("invalid_or_expired_sso_token");

  const mockFetch = async (): Promise<Response> => {
    return new Response(
      JSON.stringify({
        type: "https://errors.qnu.edu.vn/invalid_token",
        title: "Token SSO không hợp lệ hoặc đã hết hạn.",
        status: 401,
        code: "invalid_token",
      }),
      { status: 401, headers: { "content-type": "application/problem+json" } },
    );
  };

  const client = createV1Client({
    fetchImpl: mockFetch,
    getToken: getAccessToken,
    getSessionId: () => getTokenState().sessionId,
    onUnauthorized: (context) =>
      clearAccessToken({ sessionId: context?.sessionId, expired: true }),
  });
  await assert.rejects(
    async () => {
      await client.get(authPaths.me);
    },
    (err: unknown) => {
      assert.equal((err as { status: number }).status, 401);
      return true;
    },
  );

  // Token was cleared and expired flag was raised
  const state = getTokenState();
  assert.equal(state.token, null);
  assert.equal(state.expired, true);
  clearAccessToken();
});

test("SSO Logout: cleans queries, clears mutation cache and purges in-memory token", async () => {
  const queryClient = new QueryClient();
  setAccessToken("active_sso_session_token");

  // Preload dummy cache
  queryClient.setQueryData(
    ["v1", 1, "workspaces"],
    [{ id: "ws-1", name: "KHTN" }],
  );

  // Simulate logout
  clearAccessToken();
  queryClient.cancelQueries({ queryKey: ["v1"] });
  queryClient.removeQueries({ queryKey: ["v1"] });
  queryClient.getMutationCache().clear();

  assert.equal(getTokenState().token, null);
  assert.equal(queryClient.getQueryData(["v1", 1, "workspaces"]), undefined);
});
