import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { User as OidcUser } from "oidc-client-ts";
import {
  type AuthFetchInterceptorDeps,
  createAuthFetchInterceptor,
  isTrustedPlatformApiRequest,
  mergeRequestHeaders,
  resolveTrustedOrigins,
} from "./fetch-interceptor";
import {
  isLoopbackHostname,
  normalizeOidcScopes,
  parseOidcUser,
  resolveOidcAuthority,
  resolveOidcUrl,
} from "./oidc";

describe("Frontend Auth & Token Security Contract", () => {
  const currentOrigin = "https://ai.qnu.edu.vn";
  const customApiOrigin = "https://api-service.qnu.edu.vn";
  const config = {
    apiBaseUrl: `${customApiOrigin}/platform`,
    bffBaseUrl: "/bff",
  };

  // ============================================================================
  // 1. OIDC Authority Resolution & Environment Rules (Yêu cầu 2)
  // ============================================================================
  describe("1. OIDC Authority Resolution (resolveOidcAuthority)", () => {
    it("1. Production chấp nhận HTTPS production authority và loại bỏ trailing slash", () => {
      const auth = resolveOidcAuthority(
        "https://sso.qnu.edu.vn/",
        "https://sso.qnu.edu.vn",
        true,
      );
      assert.equal(auth, "https://sso.qnu.edu.vn");

      const authWithPath = resolveOidcAuthority(
        "https://sso.qnu.edu.vn/auth/",
        "https://sso.qnu.edu.vn",
        true,
      );
      assert.equal(authWithPath, "https://sso.qnu.edu.vn/auth");
    });

    it("2. Production từ chối HTTP authority", () => {
      assert.throws(
        () =>
          resolveOidcAuthority(
            "http://sso.qnu.edu.vn",
            "https://sso.qnu.edu.vn",
            true,
          ),
        /Production security violation: SSO authority must use HTTPS protocol/,
      );
    });

    it("3. Production từ chối loopback addresses (localhost, 127.0.0.1, ::1)", () => {
      assert.throws(
        () =>
          resolveOidcAuthority(
            "https://localhost:5000",
            "https://sso.qnu.edu.vn",
            true,
          ),
        /Production security violation: SSO authority must not point to loopback address/,
      );
      assert.throws(
        () =>
          resolveOidcAuthority(
            "https://127.0.0.1:5000",
            "https://sso.qnu.edu.vn",
            true,
          ),
        /Production security violation: SSO authority must not point to loopback address/,
      );
      assert.throws(
        () =>
          resolveOidcAuthority(
            "https://[::1]:5000",
            "https://sso.qnu.edu.vn",
            true,
          ),
        /Production security violation: SSO authority must not point to loopback address/,
      );
    });

    it("4. Development chấp nhận HTTP localhost", () => {
      const auth = resolveOidcAuthority(
        "http://localhost:5000/",
        "https://sso.qnu.edu.vn",
        false,
      );
      assert.equal(auth, "http://localhost:5000");
    });

    it("5. Development chấp nhận HTTP 127.0.0.1", () => {
      const auth = resolveOidcAuthority(
        "http://127.0.0.1:5000",
        "https://sso.qnu.edu.vn",
        false,
      );
      assert.equal(auth, "http://127.0.0.1:5000");
    });

    it("6. Development chấp nhận HTTP [::1]", () => {
      const auth = resolveOidcAuthority(
        "http://[::1]:5000",
        "https://sso.qnu.edu.vn",
        false,
      );
      assert.equal(auth, "http://[::1]:5000");
    });

    it("7. Development từ chối HTTP domain bên ngoài", () => {
      assert.throws(
        () =>
          resolveOidcAuthority(
            "http://external-sso.qnu.edu.vn",
            "https://sso.qnu.edu.vn",
            false,
          ),
        /Invalid SSO authority: HTTP is only permitted for loopback hosts/,
      );
    });

    it("8. URL tương đối, javascript:, data: và chuỗi không hợp lệ đều bị từ chối", () => {
      assert.throws(
        () =>
          resolveOidcAuthority(
            "/relative/auth",
            "https://sso.qnu.edu.vn",
            false,
          ),
        /Invalid SSO authority/,
      );
      assert.throws(
        () =>
          resolveOidcAuthority(
            "javascript:alert(1)",
            "https://sso.qnu.edu.vn",
            false,
          ),
        /only HTTP and HTTPS are permitted/,
      );
      assert.throws(
        () =>
          resolveOidcAuthority(
            "data:text/plain;base64,xxx",
            "https://sso.qnu.edu.vn",
            false,
          ),
        /only HTTP and HTTPS are permitted/,
      );
      assert.throws(
        () =>
          resolveOidcAuthority(
            "not-a-valid-url",
            "https://sso.qnu.edu.vn",
            false,
          ),
        /Invalid SSO authority/,
      );
    });

    it("isLoopbackHostname nhận diện chính xác localhost, 127.0.0.1 và ::1", () => {
      assert.equal(isLoopbackHostname("localhost"), true);
      assert.equal(isLoopbackHostname("127.0.0.1"), true);
      assert.equal(isLoopbackHostname("::1"), true);
      assert.equal(isLoopbackHostname("[::1]"), true);
      assert.equal(isLoopbackHostname("ai.qnu.edu.vn"), false);
      assert.equal(isLoopbackHostname("localhost.evil.com"), false);
    });
  });

  // ============================================================================
  // 2. Trusted-Origin Token Injection & Cross-Origin Isolation
  // ============================================================================
  describe("2. Trusted-Origin Token Injection & Cross-Origin Isolation", () => {
    it("Relative /platform/v1alpha1/... should be trusted", () => {
      const allowed = isTrustedPlatformApiRequest(
        "/platform/v1alpha1/assistants",
        config,
        currentOrigin,
      );
      assert.equal(allowed, true);
    });

    it("Absolute same-origin API should be trusted", () => {
      const allowed = isTrustedPlatformApiRequest(
        "https://ai.qnu.edu.vn/platform/v1alpha1/knowledge",
        config,
        currentOrigin,
      );
      assert.equal(allowed, true);
    });

    it("Trusted configured API origin should be trusted", () => {
      const allowed = isTrustedPlatformApiRequest(
        "https://api-service.qnu.edu.vn/platform/v1alpha1/models",
        config,
        currentOrigin,
      );
      assert.equal(allowed, true);
    });

    it("External malicious domain must NOT be trusted", () => {
      const allowed = isTrustedPlatformApiRequest(
        "https://evil.example/platform/collect",
        config,
        currentOrigin,
      );
      assert.equal(allowed, false);
    });

    it("URL with /platform/ only in query string must NOT be trusted", () => {
      const allowed = isTrustedPlatformApiRequest(
        "https://evil.example/?next=/platform/test",
        config,
        currentOrigin,
      );
      assert.equal(allowed, false);

      const sameOriginQuery = isTrustedPlatformApiRequest(
        "https://ai.qnu.edu.vn/?next=/platform/test",
        config,
        currentOrigin,
      );
      assert.equal(sameOriginQuery, false);
    });

    it("Similar hostname (ai.qnu.edu.vn.evil.com) must NOT be trusted", () => {
      const allowed = isTrustedPlatformApiRequest(
        "https://ai.qnu.edu.vn.evil.com/platform/collect",
        config,
        currentOrigin,
      );
      assert.equal(allowed, false);
    });

    it("Non-platform endpoints on trusted origin must NOT be intercepted", () => {
      assert.equal(
        isTrustedPlatformApiRequest("/api/public/info", config, currentOrigin),
        false,
      );
      assert.equal(
        isTrustedPlatformApiRequest("/healthz", config, currentOrigin),
        false,
      );
    });

    it("resolveTrustedOrigins includes currentOrigin and configured API origins", () => {
      const origins = resolveTrustedOrigins(config, currentOrigin);
      assert.equal(origins.has("https://ai.qnu.edu.vn"), true);
      assert.equal(origins.has("https://api-service.qnu.edu.vn"), true);
      assert.equal(origins.has("https://evil.example"), false);
    });
  });

  // ============================================================================
  // 3. Request Headers & Body Preservation
  // ============================================================================
  describe("3. Request Headers & Body Preservation", () => {
    it("Caller-supplied Authorization must NOT be overwritten", () => {
      const originalHeaders = new Headers({
        Authorization: "Bearer manual-api-key-123",
      });
      const initHeaders = new Headers({ "X-Custom": "header-val" });
      const merged = mergeRequestHeaders(originalHeaders, initHeaders);

      assert.equal(merged.get("Authorization"), "Bearer manual-api-key-123");
      assert.equal(merged.get("X-Custom"), "header-val");
    });

    it("Headers preservation merges case-insensitively and preserves caller keys", () => {
      const caller = {
        "x-api-key": "secret",
        "content-type": "application/json",
      };
      const merged = mergeRequestHeaders(caller, { "x-extra": "extra" });
      assert.equal(merged.get("x-api-key"), "secret");
      assert.equal(merged.get("content-type"), "application/json");
      assert.equal(merged.get("x-extra"), "extra");
    });
  });

  // ============================================================================
  // 4. OIDC Configuration Helpers
  // ============================================================================
  describe("4. OIDC Configuration Helpers (redirectUri & scopes)", () => {
    it("resolveOidcUrl resolves relative path using origin", () => {
      const resolved = resolveOidcUrl(
        "/signin-oidc",
        "/signin-oidc",
        "https://ai.qnu.edu.vn",
        true,
      );
      assert.equal(resolved, "https://ai.qnu.edu.vn/signin-oidc");
    });

    it("resolveOidcUrl accepts valid absolute HTTPS redirect in production", () => {
      const resolved = resolveOidcUrl(
        "https://ai.qnu.edu.vn/custom-callback",
        "/signin-oidc",
        "https://ai.qnu.edu.vn",
        true,
      );
      assert.equal(resolved, "https://ai.qnu.edu.vn/custom-callback");
    });

    it("resolveOidcUrl rejects HTTP redirect URI in production", () => {
      assert.throws(
        () =>
          resolveOidcUrl(
            "http://ai.qnu.edu.vn/signin-oidc",
            "/signin-oidc",
            "https://ai.qnu.edu.vn",
            true,
          ),
        /Production security violation: SSO redirect URI must use HTTPS protocol/,
      );
    });

    it("resolveOidcUrl allows HTTP for localhost in development", () => {
      const resolved = resolveOidcUrl(
        "http://localhost:3000/signin-oidc",
        "/signin-oidc",
        "http://localhost:3000",
        false,
      );
      assert.equal(resolved, "http://localhost:3000/signin-oidc");
    });

    it("resolveOidcUrl handles empty/whitespace values by falling back", () => {
      const resolved = resolveOidcUrl(
        "   ",
        "/signin-oidc",
        "https://ai.qnu.edu.vn",
        true,
      );
      assert.equal(resolved, "https://ai.qnu.edu.vn/signin-oidc");
    });

    it("normalizeOidcScopes deduplicates scopes and normalizes whitespace", () => {
      const raw =
        "openid   profile  email roles   openid  ai.api offline_access roles";
      const normalized = normalizeOidcScopes(raw);
      assert.equal(
        normalized,
        "openid profile email roles ai.api offline_access",
      );
    });

    it("normalizeOidcScopes throws when missing openid scope", () => {
      assert.throws(
        () => normalizeOidcScopes("profile email roles ai.api"),
        /Invalid SSO scope: 'openid' is required/,
      );
    });

    it("normalizeOidcScopes throws when missing ai.api scope", () => {
      assert.throws(
        () => normalizeOidcScopes("openid profile email roles offline_access"),
        /Invalid SSO scope: 'ai.api' resource scope is required/,
      );
    });

    it("normalizeOidcScopes falls back to canonical defaults when empty", () => {
      const normalized = normalizeOidcScopes("");
      assert.equal(
        normalized,
        "openid profile email roles ai.api offline_access",
      );
    });
  });

  // ============================================================================
  // 5. Claims Parsing & RBAC Strictness
  // ============================================================================
  describe("5. Claims Parsing & RBAC Strictness", () => {
    it("parseOidcUser strips wildcard '*' permission without elevating privileges", () => {
      const mockOidcUser = {
        access_token: "mock-token",
        expired: false,
        profile: {
          sub: "user-123",
          name: "Nguyễn Văn Test",
          email: "test@qnu.edu.vn",
          role: ["AI.User"],
          permission: ["*", "ai.access.read", "ai.chat.access"],
        },
      } as unknown as OidcUser;

      const actor = parseOidcUser(mockOidcUser);
      assert.ok(actor);
      assert.equal(actor.permissions.includes("*"), false);
      assert.deepEqual(actor.permissions, ["ai.access.read", "ai.chat.access"]);
      assert.deepEqual(actor.roles, ["AI.User"]);
    });

    it("parseOidcUser returns null for expired or null user", () => {
      const expiredUser = {
        expired: true,
        access_token: "token",
        profile: {},
      } as unknown as OidcUser;
      assert.equal(parseOidcUser(expiredUser), null);
      assert.equal(parseOidcUser(null), null);
    });
  });

  // ============================================================================
  // 6. Production Fetch Interceptor Full Lifecycle Tests (Yêu cầu 4: 16 Test Cases)
  // ============================================================================
  describe("6. Production Fetch Interceptor Lifecycle Tests (16 Scenarios)", () => {
    interface InterceptorTestContext {
      interceptor: (
        input: RequestInfo | URL,
        init?: RequestInit,
      ) => Promise<Response>;
      calls: Array<{
        url: string;
        headers: Headers;
        body: BodyInit | null | undefined;
        method: string;
      }>;
      getToken: () => string | null;
      getRenewCount: () => number;
      getRemoveCount: () => number;
      isRedirected: () => boolean;
      setCustomFetchHandler: (
        fn: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>,
      ) => void;
    }

    function createTestContext(
      overrides?: Partial<AuthFetchInterceptorDeps>,
    ): InterceptorTestContext {
      let currentToken: string | null = "valid-bearer-token-123";
      let renewCount = 0;
      let removeCount = 0;
      let redirected = false;
      const calls: Array<{
        url: string;
        headers: Headers;
        body: BodyInit | null | undefined;
        method: string;
      }> = [];

      let customFetchHandler:
        | ((input: RequestInfo | URL, init?: RequestInit) => Promise<Response>)
        | null = null;

      const mockOriginalFetch: typeof fetch = async (input, init) => {
        if (customFetchHandler) {
          return customFetchHandler(input, init);
        }
        const url =
          typeof input === "string"
            ? input
            : input instanceof URL
              ? input.href
              : input.url;
        const method =
          init?.method || (input instanceof Request ? input.method : "GET");
        const headers = new Headers(
          init?.headers ||
            (input instanceof Request ? input.headers : undefined),
        );
        let body = init?.body;
        if (body === undefined && input instanceof Request) {
          try {
            body = await input.clone().text();
          } catch {
            // ignore
          }
        }
        calls.push({ url, headers, body, method });
        return new Response(JSON.stringify({ success: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      };

      const interceptor = createAuthFetchInterceptor({
        originalFetch: mockOriginalFetch,
        getAccessToken: () => currentToken,
        setCachedAccessToken: (t) => {
          currentToken = t;
        },
        getUserManager: () => ({
          getUser: async () => ({
            access_token: currentToken || undefined,
            expired: false,
          }),
          signinSilent: async () => {
            renewCount++;
            await new Promise((r) => setTimeout(r, 10)); // simulate network delay
            currentToken = "new-renewed-token-456";
            return { access_token: "new-renewed-token-456" };
          },
          removeUser: async () => {
            removeCount++;
          },
        }),
        config,
        getLocation: () => ({ origin: currentOrigin, pathname: "/" }),
        onRedirectToSignIn: () => {
          redirected = true;
        },
        ...overrides,
      });

      return {
        interceptor,
        calls,
        getToken: () => currentToken,
        getRenewCount: () => renewCount,
        getRemoveCount: () => removeCount,
        isRedirected: () => redirected,
        setCustomFetchHandler: (fn) => {
          customFetchHandler = fn;
        },
      };
    }

    it("1. Relative /platform/v1alpha1/... được inject Bearer token", async () => {
      const ctx = createTestContext();
      await ctx.interceptor("/platform/v1alpha1/assistants");
      assert.equal(ctx.calls.length, 1);
      assert.equal(
        ctx.calls[0].headers.get("Authorization"),
        "Bearer valid-bearer-token-123",
      );
    });

    it("2. Absolute same-origin /platform/... được inject Bearer token", async () => {
      const ctx = createTestContext();
      await ctx.interceptor("https://ai.qnu.edu.vn/platform/v1alpha1/chat");
      assert.equal(ctx.calls.length, 1);
      assert.equal(
        ctx.calls[0].headers.get("Authorization"),
        "Bearer valid-bearer-token-123",
      );
    });

    it("3. Configured trusted API origin được inject Bearer token", async () => {
      const ctx = createTestContext();
      await ctx.interceptor(
        "https://api-service.qnu.edu.vn/platform/v1alpha1/models",
      );
      assert.equal(ctx.calls.length, 1);
      assert.equal(
        ctx.calls[0].headers.get("Authorization"),
        "Bearer valid-bearer-token-123",
      );
    });

    it("4. External origin không được inject Bearer token", async () => {
      const ctx = createTestContext();
      await ctx.interceptor("https://evil.example/platform/v1alpha1/steal");
      assert.equal(ctx.calls.length, 1);
      assert.equal(ctx.calls[0].headers.has("Authorization"), false);
    });

    it("5. Hostname giả như ai.qnu.edu.vn.evil.com không được inject Bearer token", async () => {
      const ctx = createTestContext();
      await ctx.interceptor(
        "https://ai.qnu.edu.vn.evil.com/platform/v1alpha1/hack",
      );
      assert.equal(ctx.calls.length, 1);
      assert.equal(ctx.calls[0].headers.has("Authorization"), false);
    });

    it("6. /platform/ chỉ xuất hiện trong query string không được inject Bearer token", async () => {
      const ctx = createTestContext();
      await ctx.interceptor(
        "https://ai.qnu.edu.vn/?redirect=/platform/v1alpha1/assistants",
      );
      assert.equal(ctx.calls.length, 1);
      assert.equal(ctx.calls[0].headers.has("Authorization"), false);
    });

    it("7. Caller đã truyền Authorization thì interceptor không ghi đè", async () => {
      const ctx = createTestContext();
      await ctx.interceptor("/platform/v1alpha1/assistants", {
        headers: { Authorization: "Bearer caller-api-key-999" },
      });
      assert.equal(ctx.calls.length, 1);
      assert.equal(
        ctx.calls[0].headers.get("Authorization"),
        "Bearer caller-api-key-999",
      );
    });

    it("8. Headers từ Request và RequestInit được giữ và merge đúng", async () => {
      const ctx = createTestContext();
      const req = new Request(
        "https://ai.qnu.edu.vn/platform/v1alpha1/assistants",
        {
          headers: { "X-Request-Meta": "from-request" },
        },
      );
      await ctx.interceptor(req, {
        headers: {
          "X-Init-Meta": "from-init",
          "Content-Type": "application/json",
        },
      });
      assert.equal(ctx.calls.length, 1);
      assert.equal(ctx.calls[0].headers.get("X-Request-Meta"), "from-request");
      assert.equal(ctx.calls[0].headers.get("X-Init-Meta"), "from-init");
      assert.equal(
        ctx.calls[0].headers.get("Content-Type"),
        "application/json",
      );
      assert.equal(
        ctx.calls[0].headers.get("Authorization"),
        "Bearer valid-bearer-token-123",
      );
    });

    it("9. POST/PUT/PATCH body được giữ nguyên ở lần gọi đầu", async () => {
      const ctx = createTestContext();
      const bodyPayload = JSON.stringify({ prompt: "Chào AI QNU" });
      await ctx.interceptor("/platform/v1alpha1/chat", {
        method: "POST",
        body: bodyPayload,
      });
      assert.equal(ctx.calls.length, 1);
      assert.equal(ctx.calls[0].body, bodyPayload);
      assert.equal(ctx.calls[0].method, "POST");
    });

    it("10. Sau 401, body vẫn được replay đúng ở lần retry", async () => {
      const ctx = createTestContext();
      let attempt = 0;
      const bodyPayload = JSON.stringify({ query: "Test retry" });

      ctx.setCustomFetchHandler(async (input, init) => {
        attempt++;
        const headers = new Headers(init?.headers);
        const body = init?.body;
        ctx.calls.push({
          url: String(input),
          headers,
          body,
          method: init?.method || "POST",
        });
        if (attempt === 1) {
          return new Response("Unauthorized", { status: 401 });
        }
        return new Response(JSON.stringify({ status: "success" }), {
          status: 200,
        });
      });

      const res = await ctx.interceptor("/platform/v1alpha1/chat", {
        method: "POST",
        body: bodyPayload,
      });

      assert.equal(res.status, 200);
      assert.equal(ctx.calls.length, 2);
      // First attempt with original token and payload
      assert.equal(ctx.calls[0].body, bodyPayload);
      assert.equal(
        ctx.calls[0].headers.get("Authorization"),
        "Bearer valid-bearer-token-123",
      );
      // Second attempt (retry) replayed body with new renewed token
      assert.equal(ctx.calls[1].body, bodyPayload);
      assert.equal(
        ctx.calls[1].headers.get("Authorization"),
        "Bearer new-renewed-token-456",
      );
    });

    it("11. Năm request 401 đồng thời chỉ gọi signinSilent đúng một lần", async () => {
      const ctx = createTestContext();
      const attemptMap = new Map<string, number>();

      ctx.setCustomFetchHandler(async (input, init) => {
        const url = String(input);
        const currentCount = attemptMap.get(url) || 0;
        attemptMap.set(url, currentCount + 1);

        const headers = new Headers(init?.headers);
        ctx.calls.push({ url, headers, body: init?.body, method: "GET" });

        if (currentCount === 0) {
          return new Response("Unauthorized", { status: 401 });
        }
        return new Response(JSON.stringify({ ok: true }), { status: 200 });
      });

      const promises = [
        ctx.interceptor("/platform/v1alpha1/item1"),
        ctx.interceptor("/platform/v1alpha1/item2"),
        ctx.interceptor("/platform/v1alpha1/item3"),
        ctx.interceptor("/platform/v1alpha1/item4"),
        ctx.interceptor("/platform/v1alpha1/item5"),
      ];

      const responses = await Promise.all(promises);
      for (const res of responses) {
        assert.equal(res.status, 200);
      }

      // Exactly ONE signinSilent call executed across 5 concurrent 401s
      assert.equal(ctx.getRenewCount(), 1);
    });

    it("12. Mỗi request chỉ retry tối đa một lần", async () => {
      const ctx = createTestContext();
      ctx.setCustomFetchHandler(async (input, init) => {
        const headers = new Headers(init?.headers);
        ctx.calls.push({
          url: String(input),
          headers,
          body: init?.body,
          method: "GET",
        });
        // Server continuously rejects even with new token
        return new Response("Still Unauthorized", { status: 401 });
      });

      const res = await ctx.interceptor("/platform/v1alpha1/protected");
      assert.equal(res.status, 401);
      // Initial call + exactly 1 retry = 2 calls total
      assert.equal(ctx.calls.length, 2);
    });

    it("13. Retry sử dụng access token mới", async () => {
      const ctx = createTestContext();
      let attempt = 0;
      ctx.setCustomFetchHandler(async (input, init) => {
        attempt++;
        const headers = new Headers(init?.headers);
        ctx.calls.push({
          url: String(input),
          headers,
          body: init?.body,
          method: "GET",
        });
        if (attempt === 1) {
          return new Response("Unauthorized", { status: 401 });
        }
        return new Response("OK", { status: 200 });
      });

      await ctx.interceptor("/platform/v1alpha1/models");
      assert.equal(
        ctx.calls[0].headers.get("Authorization"),
        "Bearer valid-bearer-token-123",
      );
      assert.equal(
        ctx.calls[1].headers.get("Authorization"),
        "Bearer new-renewed-token-456",
      );
      assert.equal(ctx.getToken(), "new-renewed-token-456");
    });

    it("14. Không gửi header nội bộ như X-Auth-Retry lên server", async () => {
      const ctx = createTestContext();
      let attempt = 0;
      ctx.setCustomFetchHandler(async (input, init) => {
        attempt++;
        const headers = new Headers(init?.headers);
        ctx.calls.push({
          url: String(input),
          headers,
          body: init?.body,
          method: "GET",
        });
        if (attempt === 1) return new Response("Unauthorized", { status: 401 });
        return new Response("OK", { status: 200 });
      });

      await ctx.interceptor("/platform/v1alpha1/assistants");
      assert.equal(ctx.calls.length, 2);
      assert.equal(ctx.calls[0].headers.has("X-Auth-Retry"), false);
      assert.equal(ctx.calls[1].headers.has("X-Auth-Retry"), false);
    });

    it("15. Silent renew thất bại: xóa token, gọi removeUser, redirect /sign-in, không lặp vô hạn", async () => {
      const ctx = createTestContext({
        getUserManager: () => ({
          signinSilent: async () => {
            // Renewal rejected (refresh token expired)
            return null;
          },
          removeUser: async () => {},
        }),
      });

      ctx.setCustomFetchHandler(async (input, init) => {
        const headers = new Headers(init?.headers);
        ctx.calls.push({
          url: String(input),
          headers,
          body: init?.body,
          method: "GET",
        });
        return new Response("Unauthorized", { status: 401 });
      });

      const res = await ctx.interceptor("/platform/v1alpha1/settings");
      assert.equal(res.status, 401);
      // No retry if silent renew fails
      assert.equal(ctx.calls.length, 1);
      assert.equal(ctx.getToken(), null);
      assert.equal(ctx.isRedirected(), true);
    });

    it("16. Request có caller-provided Authorization nhận 401 không được tự silent renew", async () => {
      const ctx = createTestContext();
      ctx.setCustomFetchHandler(async (input, init) => {
        const headers = new Headers(init?.headers);
        ctx.calls.push({
          url: String(input),
          headers,
          body: init?.body,
          method: "GET",
        });
        return new Response("Unauthorized", { status: 401 });
      });

      const res = await ctx.interceptor("/platform/v1alpha1/api-key-test", {
        headers: { Authorization: "Bearer custom-external-api-key" },
      });

      assert.equal(res.status, 401);
      assert.equal(ctx.getRenewCount(), 0);
      assert.equal(ctx.calls.length, 1);
      assert.equal(ctx.isRedirected(), false);
    });
  });
});
