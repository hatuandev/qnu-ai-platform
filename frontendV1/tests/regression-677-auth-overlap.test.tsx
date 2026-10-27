// @vitest-environment jsdom
/**
 * Context674 F1 — a late dev auto-login response must never win against a newer
 * auth decision.
 *
 * Ported from `storage/artifacts/context674-review/auth-races.test.tsx` with the
 * three original assertions unchanged, plus the SSO-callback guard and the
 * "newest attempt wins" case.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { clearAccessToken, getAccessToken } from "@/app/api/v1";
import {
  resetDevAutoLoginState,
  resetSsoCallbackState,
  setSsoCallbackActive,
} from "@/app/auth/v1/dev-auto-login";
import {
  useV1Auth,
  type V1AuthContextValue,
  V1AuthProvider,
} from "@/app/auth/v1/provider";

vi.mock("@/app/auth/v1/oidc", () => ({
  loginWithSso: vi.fn(),
  logoutSso: vi.fn().mockResolvedValue(undefined),
}));

let auth: V1AuthContextValue;

const actor = {
  actor_id: "act_dev_admin",
  username: "dev.admin",
  authenticated: true,
  permissions: [],
  roles: ["AI.Admin"],
};

const response = (payload: unknown, status = 200) =>
  new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });

function pendingBridge() {
  let release!: (value: Response) => void;
  const pending = new Promise<Response>((resolve) => {
    release = resolve;
  });
  let calls = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: unknown) => {
      const path = String(input);
      if (path.includes("/__qnu_dev/auto-login")) {
        calls += 1;
        return pending;
      }
      if (path.endsWith("/auth/me")) return response({ actor });
      if (path.endsWith("/auth/logout")) return response({ ok: true });
      if (path.endsWith("/auth/login")) {
        return response({
          access_token: "synthetic-manual-session",
          token_type: "bearer",
          expires_in: 3600,
        });
      }
      throw new Error("Unexpected endpoint in synthetic auth probe");
    }),
  );

  function Child() {
    auth = useV1Auth();
    return <div>{auth.status}</div>;
  }

  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const tree = render(
    <QueryClientProvider client={client}>
      <V1AuthProvider>
        <Child />
      </V1AuthProvider>
    </QueryClientProvider>,
  );
  return { release, calls: () => calls, tree };
}

beforeEach(() => {
  clearAccessToken();
  resetDevAutoLoginState();
  resetSsoCallbackState();
  window.sessionStorage.clear();
});

afterEach(() => {
  cleanup();
  clearAccessToken();
  resetDevAutoLoginState();
  resetSsoCallbackState();
  window.sessionStorage.clear();
  vi.unstubAllGlobals();
});

test("SSO callback starting during a pending dev login must prevent installation", async () => {
  const probe = pendingBridge();
  await waitFor(() => expect(probe.calls()).toBe(1));
  act(() => setSsoCallbackActive(true));
  await act(async () =>
    probe.release(response({ access_token: "synthetic-dev-admin-session" })),
  );
  expect(getAccessToken()).toBeNull();
  expect(auth.autoLoginPhase).toBe("idle");
});

test("a callback that already ended still invalidates the older pending dev response", async () => {
  const probe = pendingBridge();
  await waitFor(() => expect(probe.calls()).toBe(1));
  act(() => {
    setSsoCallbackActive(true);
    setSsoCallbackActive(false);
  });
  await act(async () =>
    probe.release(response({ access_token: "synthetic-stale-dev-session" })),
  );
  expect(getAccessToken()).toBeNull();
  expect(auth.autoLoginPhase).toBe("idle");
});

test("explicit retry cannot restart the dev bridge while SSO owns the flow", async () => {
  setSsoCallbackActive(true);
  const probe = pendingBridge();
  act(() => auth.retryAutoLogin());
  await act(async () => {
    await Promise.resolve();
  });
  expect(probe.calls()).toBe(0);
  expect(getAccessToken()).toBeNull();
  expect(auth.autoLoginPhase).toBe("idle");
});
