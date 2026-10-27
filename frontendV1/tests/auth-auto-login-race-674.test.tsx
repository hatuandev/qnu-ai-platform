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
import { clearAccessToken, getAccessToken, setAccessToken } from "@/app/api/v1";
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

test("a slow dev bridge must not replace an SSO session established while it was pending", async () => {
  const probe = pendingBridge();
  await waitFor(() => expect(probe.calls()).toBe(1));

  act(() => {
    setAccessToken("synthetic-sso-session");
  });
  await waitFor(() => expect(auth.status).toBe("authenticated"));

  await act(async () => {
    probe.release(response({ access_token: "synthetic-dev-admin-session" }));
  });
  expect(getAccessToken()).toBe("synthetic-sso-session");
});

test("an explicit logout must win against an already pending dev login response", async () => {
  const probe = pendingBridge();
  await waitFor(() => expect(probe.calls()).toBe(1));

  await act(async () => {
    await auth.signOut();
  });
  expect(getAccessToken()).toBeNull();

  await act(async () => {
    probe.release(response({ access_token: "synthetic-dev-admin-session" }));
  });
  expect(getAccessToken()).toBeNull();
});

test("an unmounted auth provider must not install a late token into the global session", async () => {
  const probe = pendingBridge();
  await waitFor(() => expect(probe.calls()).toBe(1));

  probe.tree.unmount();
  await act(async () => {
    probe.release(response({ access_token: "synthetic-stale-session" }));
  });
  expect(getAccessToken()).toBeNull();
});

test("a manual key login while the bridge is pending keeps the manual token", async () => {
  const probe = pendingBridge();
  await waitFor(() => expect(probe.calls()).toBe(1));

  await act(async () => {
    await auth.signIn("synthetic-key");
  });
  expect(getAccessToken()).toBe("synthetic-manual-session");
  await act(async () => {
    probe.release(response({ access_token: "synthetic-dev-admin-session" }));
  });
  expect(getAccessToken()).toBe("synthetic-manual-session");
});

test("auto-login never starts while the SSO callback page owns the token exchange", async () => {
  setSsoCallbackActive(true);
  const probe = pendingBridge();
  // Give the provider a couple of renders to (wrongly) start the bridge.
  await act(async () => {
    await Promise.resolve();
  });
  expect(probe.calls()).toBe(0);
  expect(getAccessToken()).toBeNull();

  // Once the callback page leaves, the bridge may run again.
  await act(async () => {
    setSsoCallbackActive(false);
  });
  await waitFor(() => expect(probe.calls()).toBe(1));
  await act(async () => {
    probe.release(response({ access_token: "synthetic-dev-admin-session" }));
  });
  expect(getAccessToken()).toBe("synthetic-dev-admin-session");
});

test("a retry supersedes the previous attempt instead of racing it", async () => {
  const probe = pendingBridge();
  await waitFor(() => expect(probe.calls()).toBe(1));

  // A second explicit retry shares the in-flight promise; the older ticket must
  // not be able to install a token after the attempt counter moved on.
  act(() => {
    auth.retryAutoLogin();
  });
  await act(async () => {
    probe.release(response({ access_token: "synthetic-dev-admin-session" }));
  });
  // Exactly one request was made (single-flight) and it installed once.
  expect(probe.calls()).toBe(1);
  expect(getAccessToken()).toBe("synthetic-dev-admin-session");
});
