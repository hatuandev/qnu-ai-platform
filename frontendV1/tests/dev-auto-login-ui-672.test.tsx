// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { clearAccessToken, getAccessToken } from "@/app/api/v1";
import {
  clearDevAutoLoginSuppression,
  isDevAutoLoginSuppressed,
  resetDevAutoLoginState,
} from "@/app/auth/v1/dev-auto-login";
import { V1SessionGate } from "@/app/auth/v1/gate";
import { useV1Auth, V1AuthProvider } from "@/app/auth/v1/provider";

vi.mock("@/app/auth/v1/oidc", () => ({
  loginWithSso: vi.fn(async () => undefined),
  logoutSso: vi.fn(async () => undefined),
}));

const actor = {
  username: "dev.admin",
  actor_id: "act_dev_admin",
  display_name: "Quản trị dev",
  email: "dev@qnu.edu.vn",
  user_type: "staff",
  role: "AI.Admin",
  roles: ["AI.Admin"],
  permissions: ["ai.access.admin"],
  authenticated: true,
};

type BridgeReply = { status: number; body: unknown } | "network-error";

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function stubBackend(options: {
  bridge: BridgeReply;
  me?: BridgeReply;
  onBridge?: () => void;
}) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/__qnu_dev/auto-login")) {
      options.onBridge?.();
      if (options.bridge === "network-error") throw new Error("offline");
      return jsonResponse(options.bridge.body, options.bridge.status);
    }
    if (url.includes("/auth/me")) {
      const me = options.me ?? { status: 200, body: { actor } };
      if (me === "network-error") throw new Error("offline");
      return jsonResponse(me.body, me.status);
    }
    throw new Error(`unexpected fetch: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderApp({ strict = false }: { strict?: boolean } = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  function Harness() {
    const { signOut } = useV1Auth();
    return (
      <div>
        <button type="button" onClick={() => void signOut()}>
          Đăng xuất
        </button>
        <V1SessionGate>
          <div>APP</div>
        </V1SessionGate>
      </div>
    );
  }

  const tree = (
    <QueryClientProvider client={queryClient}>
      <V1AuthProvider>
        <Harness />
      </V1AuthProvider>
    </QueryClientProvider>
  );

  return render(strict ? <StrictMode>{tree}</StrictMode> : tree);
}

beforeEach(() => {
  clearAccessToken();
  resetDevAutoLoginState();
  clearDevAutoLoginSuppression();
  window.sessionStorage.clear();
});

afterEach(() => {
  cleanup();
  clearAccessToken();
  resetDevAutoLoginState();
  clearDevAutoLoginSuppression();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

test("dev auto-login: enabled dev server signs in and verifies the actor", async () => {
  const fetchMock = stubBackend({
    bridge: {
      status: 200,
      body: {
        access_token: "issued-token",
        token_type: "bearer",
        expires_in: 60,
      },
    },
  });

  renderApp();

  expect(await screen.findByText("APP")).toBeTruthy();
  expect(getAccessToken()).toBe("issued-token");

  const bridgeCalls = fetchMock.mock.calls.filter(([input]) =>
    String(input).includes("/__qnu_dev/auto-login"),
  );
  expect(bridgeCalls).toHaveLength(1);
});

test("dev auto-login: StrictMode mount does not call the bridge twice", async () => {
  const onBridge = vi.fn();
  stubBackend({
    bridge: { status: 200, body: { access_token: "strict-token" } },
    onBridge,
  });

  renderApp({ strict: true });

  expect(await screen.findByText("APP")).toBeTruthy();
  await waitFor(() => expect(onBridge).toHaveBeenCalledTimes(1));
});

test("dev auto-login: disabled bridge never opens the app and explains the cause", async () => {
  const fetchMock = stubBackend({
    bridge: {
      status: 404,
      body: {
        code: "dev_bridge_disabled",
        message: "Tự đăng nhập local đang tắt.",
      },
    },
  });

  renderApp();

  expect(await screen.findByText("Không tự đăng nhập được")).toBeTruthy();
  expect(screen.queryByText("APP")).toBeNull();
  expect(getAccessToken()).toBeNull();
  expect(
    screen.getByText(
      /Đặt QNU_DEV_AUTO_LOGIN=true trong frontendV1\/\.env\.local/,
    ),
  ).toBeTruthy();
  expect(screen.getByRole("button", { name: /Thử lại/ })).toBeTruthy();
  expect(
    screen.getByRole("button", { name: /Đăng nhập thủ công/ }),
  ).toBeTruthy();
  expect(
    fetchMock.mock.calls.some(([input]) => String(input).includes("/auth/me")),
  ).toBe(false);
});

test("dev auto-login: wrong credential keeps the app closed and allows manual login", async () => {
  stubBackend({
    bridge: {
      status: 401,
      body: {
        code: "invalid_credentials",
        message: "Mật khẩu dev không đúng.",
      },
    },
  });

  renderApp();

  expect(await screen.findByText(/Access key local không đúng/)).toBeTruthy();
  expect(screen.queryByText("APP")).toBeNull();
  expect(getAccessToken()).toBeNull();

  fireEvent.click(screen.getByRole("button", { name: /Đăng nhập thủ công/ }));
  expect(await screen.findByText("Đăng nhập QNU AI Platform")).toBeTruthy();
});

test("dev auto-login: backend offline is reported instead of a fake session", async () => {
  stubBackend({ bridge: "network-error" });

  renderApp();

  expect(
    await screen.findByText(/Không gọi được cầu nối đăng nhập/),
  ).toBeTruthy();
  expect(screen.queryByText("APP")).toBeNull();
  expect(getAccessToken()).toBeNull();
});

test("dev auto-login: token rejected by /auth/me fails once without a retry loop", async () => {
  const onBridge = vi.fn();
  const fetchMock = stubBackend({
    bridge: { status: 200, body: { access_token: "rejected-token" } },
    me: { status: 401, body: { code: "invalid_token", detail: "expired" } },
    onBridge,
  });

  renderApp();

  expect(
    await screen.findByText(/BackendV1 từ chối token do cầu nối local cấp/),
  ).toBeTruthy();
  expect(getAccessToken()).toBeNull();
  expect(onBridge).toHaveBeenCalledTimes(1);
  expect(
    fetchMock.mock.calls.filter(([input]) =>
      String(input).includes("/__qnu_dev/auto-login"),
    ),
  ).toHaveLength(1);
});

test("dev auto-login: explicit logout is not undone automatically", async () => {
  const onBridge = vi.fn();
  stubBackend({
    bridge: { status: 200, body: { access_token: "logout-token" } },
    onBridge,
  });

  renderApp();

  expect(await screen.findByText("APP")).toBeTruthy();
  expect(onBridge).toHaveBeenCalledTimes(1);

  fireEvent.click(screen.getByRole("button", { name: "Đăng xuất" }));

  expect(await screen.findByText("Đăng nhập QNU AI Platform")).toBeTruthy();
  expect(getAccessToken()).toBeNull();
  expect(isDevAutoLoginSuppressed()).toBe(true);
  expect(onBridge).toHaveBeenCalledTimes(1);
  expect(
    screen.getByRole("button", { name: /Tự đăng nhập bằng cấu hình local/ }),
  ).toBeTruthy();
});

test("dev auto-login: production bundle never calls the bridge", async () => {
  vi.stubEnv("DEV", false);
  vi.stubEnv("PROD", true);
  const onBridge = vi.fn();
  stubBackend({
    bridge: { status: 200, body: { access_token: "should-not-be-used" } },
    onBridge,
  });

  renderApp();

  expect(await screen.findByText("Đăng nhập QNU AI Platform")).toBeTruthy();
  expect(onBridge).not.toHaveBeenCalled();
  expect(getAccessToken()).toBeNull();
});
