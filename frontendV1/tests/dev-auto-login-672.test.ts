import assert from "node:assert/strict";
import type { IncomingMessage, ServerResponse } from "node:http";
import { test, vi } from "vitest";
import {
  createDevAutoLoginHandler,
  DEV_AUTO_LOGIN_PATH,
  type DevAutoLoginConfig,
  isLoopbackUrl,
  isSameOriginRequest,
  resolveDevAutoLoginConfig,
} from "../dev/dev-auto-login.ts";

type Captured = {
  status: number;
  body: Record<string, unknown> | null;
  headers: Record<string, string>;
  passedThrough: boolean;
};

function fakeRequest(
  overrides: Partial<IncomingMessage> = {},
): IncomingMessage {
  return {
    url: DEV_AUTO_LOGIN_PATH,
    method: "POST",
    headers: {
      host: "127.0.0.1:3001",
      origin: "http://127.0.0.1:3001",
    },
    ...overrides,
  } as unknown as IncomingMessage;
}

function invoke(
  handler: ReturnType<typeof createDevAutoLoginHandler>,
  req: IncomingMessage,
): Promise<Captured> {
  return new Promise((resolve) => {
    const headers: Record<string, string> = {};
    let statusCode = 200;
    const res = {
      get statusCode() {
        return statusCode;
      },
      set statusCode(value: number) {
        statusCode = value;
      },
      setHeader(name: string, value: string) {
        headers[name.toLowerCase()] = value;
      },
      end(body?: string) {
        resolve({
          status: statusCode,
          body: body ? (JSON.parse(body) as Record<string, unknown>) : null,
          headers,
          passedThrough: false,
        });
      },
    } as unknown as ServerResponse;

    handler(req, res, () => {
      resolve({ status: -1, body: null, headers, passedThrough: true });
    });
  });
}

const enabledConfig: DevAutoLoginConfig = {
  enabled: true,
  accessKey: "local-secret",
  apiTarget: "http://127.0.0.1:8002",
  note: "test",
};

const tokenPayload = {
  access_token: "issued-token",
  token_type: "bearer",
  expires_in: 28800,
};

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

test("dev auto-login config: off by default and never on outside the dev server", () => {
  const off = resolveDevAutoLoginConfig({}, { devServer: true });
  assert.equal(off.enabled, false);

  const buildOnly = resolveDevAutoLoginConfig(
    { QNU_DEV_AUTO_LOGIN: "true", QNU_DEV_ACCESS_KEY: "k" },
    { devServer: false },
  );
  assert.equal(buildOnly.enabled, false);
  assert.match(buildOnly.note, /only runs in the Vite dev server/);

  const on = resolveDevAutoLoginConfig(
    { QNU_DEV_AUTO_LOGIN: "true", QNU_DEV_ACCESS_KEY: "k" },
    { devServer: true },
  );
  assert.equal(on.enabled, true);
  assert.equal(on.accessKey, "k");
  assert.equal(on.apiTarget, "http://127.0.0.1:8002");

  const missingKey = resolveDevAutoLoginConfig(
    { QNU_DEV_AUTO_LOGIN: "true" },
    { devServer: true },
  );
  assert.equal(missingKey.enabled, true);
  assert.equal(missingKey.accessKey, null);
});

test("dev auto-login guards: loopback target and same-origin only", () => {
  assert.equal(isLoopbackUrl("http://127.0.0.1:8002"), true);
  assert.equal(isLoopbackUrl("http://localhost:8002/"), true);
  assert.equal(isLoopbackUrl("http://[::1]:8002"), true);
  assert.equal(isLoopbackUrl("https://api.qnu.edu.vn"), false);
  assert.equal(isLoopbackUrl("file:///etc/passwd"), false);

  assert.equal(
    isSameOriginRequest("http://127.0.0.1:3001", "127.0.0.1:3001"),
    true,
  );
  assert.equal(
    isSameOriginRequest("http://evil.example", "127.0.0.1:3001"),
    false,
  );
  assert.equal(isSameOriginRequest(undefined, "127.0.0.1:3001"), false);
});

test("dev auto-login: unrelated paths pass through untouched", async () => {
  const fetchImpl = vi.fn();
  const handler = createDevAutoLoginHandler(enabledConfig, { fetchImpl });
  const result = await invoke(
    handler,
    fakeRequest({ url: "/platform/v1alpha1/auth/me" }),
  );

  assert.equal(result.passedThrough, true);
  assert.equal(fetchImpl.mock.calls.length, 0);
});

test("dev auto-login: disabled bridge answers 404 without calling the backend", async () => {
  const fetchImpl = vi.fn();
  const handler = createDevAutoLoginHandler(
    { ...enabledConfig, enabled: false },
    { fetchImpl },
  );
  const result = await invoke(handler, fakeRequest());

  assert.equal(result.status, 404);
  assert.equal(result.body?.code, "dev_bridge_disabled");
  assert.equal(fetchImpl.mock.calls.length, 0);
});

test("dev auto-login: missing key or remote target is a configuration error", async () => {
  const fetchImpl = vi.fn();
  const noKey = await invoke(
    createDevAutoLoginHandler(
      { ...enabledConfig, accessKey: null },
      { fetchImpl },
    ),
    fakeRequest(),
  );
  assert.equal(noKey.status, 500);
  assert.equal(noKey.body?.code, "dev_bridge_misconfigured");

  const remoteTarget = await invoke(
    createDevAutoLoginHandler(
      { ...enabledConfig, apiTarget: "https://api.example.com" },
      { fetchImpl },
    ),
    fakeRequest(),
  );
  assert.equal(remoteTarget.status, 500);
  assert.equal(remoteTarget.body?.code, "dev_bridge_misconfigured");
  assert.equal(fetchImpl.mock.calls.length, 0);
});

test("dev auto-login: rejects foreign host, cross-origin and non-POST calls", async () => {
  const fetchImpl = vi.fn();
  const handler = createDevAutoLoginHandler(enabledConfig, { fetchImpl });

  const foreignHost = await invoke(
    handler,
    fakeRequest({
      headers: {
        host: "192.168.1.20:3001",
        origin: "http://192.168.1.20:3001",
      },
    }),
  );
  assert.equal(foreignHost.status, 403);
  assert.equal(foreignHost.body?.code, "dev_bridge_forbidden");

  const crossOrigin = await invoke(
    handler,
    fakeRequest({
      headers: { host: "127.0.0.1:3001", origin: "http://evil.example" },
    }),
  );
  assert.equal(crossOrigin.status, 403);
  assert.equal(crossOrigin.body?.code, "dev_bridge_forbidden");

  const getCall = await invoke(handler, fakeRequest({ method: "GET" }));
  assert.equal(getCall.status, 405);
  assert.equal(getCall.body?.code, "dev_bridge_method_not_allowed");

  assert.equal(fetchImpl.mock.calls.length, 0);
});

test("dev auto-login: success returns only the token, never the access key", async () => {
  const fetchImpl = vi.fn(async () => jsonResponse(tokenPayload));
  const handler = createDevAutoLoginHandler(enabledConfig, { fetchImpl });

  const result = await invoke(handler, fakeRequest());

  assert.equal(result.status, 200);
  assert.deepEqual(result.body, tokenPayload);
  assert.equal(result.headers["cache-control"], "no-store");
  assert.equal(JSON.stringify(result.body).includes("local-secret"), false);

  assert.equal(fetchImpl.mock.calls.length, 1);
  const [url, init] = fetchImpl.mock.calls[0] as unknown as [
    string,
    RequestInit,
  ];
  assert.equal(url, "http://127.0.0.1:8002/platform/v1alpha1/auth/login");
  assert.equal(init.method, "POST");
  assert.deepEqual(JSON.parse(String(init.body)), {
    access_key: "local-secret",
  });
});

test("dev auto-login: upstream failures map to explicit codes", async () => {
  const cases: Array<{
    response: Response | Error;
    status: number;
    code: string;
  }> = [
    {
      response: jsonResponse({ code: "invalid_credentials" }, 401),
      status: 401,
      code: "invalid_credentials",
    },
    {
      response: jsonResponse({ code: "dev_gate_disabled" }, 403),
      status: 403,
      code: "dev_gate_disabled",
    },
    {
      response: jsonResponse({ code: "SIGNING_KEY_MISSING" }, 503),
      status: 503,
      code: "backend_not_ready",
    },
    { response: jsonResponse({}, 500), status: 502, code: "backend_error" },
    {
      response: new Error("ECONNREFUSED"),
      status: 502,
      code: "backend_unreachable",
    },
    {
      response: jsonResponse({ detail: "no token" }, 200),
      status: 502,
      code: "invalid_login_response",
    },
  ];

  for (const item of cases) {
    const fetchImpl = vi.fn(async () => {
      if (item.response instanceof Error) throw item.response;
      return item.response;
    });
    const result = await invoke(
      createDevAutoLoginHandler(enabledConfig, { fetchImpl }),
      fakeRequest(),
    );
    assert.equal(result.status, item.status, `status for ${item.code}`);
    assert.equal(result.body?.code, item.code);
    assert.equal(result.body?.access_token, undefined);
  }
});
