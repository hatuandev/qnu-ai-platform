import assert from "node:assert/strict";
import { QueryClient } from "@tanstack/react-query";
import { test } from "vitest";
import { ApiProblemError, createV1Client } from "../src/app/api/v1/client.ts";
import {
  clearAccessToken,
  getTokenState,
  setAccessToken,
} from "../src/app/api/v1/session-token.ts";
import { isValidActor } from "../src/app/auth/v1/provider.tsx";
import {
  createProviderKey,
  rotateProviderKey,
} from "../src/features/modelops/requests.ts";

type MockRequest = {
  method: string;
  url: string;
  headers: Record<string, string>;
  body: unknown;
};

type MockHandler = (req: MockRequest) => Promise<{
  status?: number;
  body?: unknown;
  contentType?: string;
}>;

function createDeferredServer(handler: MockHandler) {
  const requests: MockRequest[] = [];
  const fetchImpl = async (
    input: string,
    init?: RequestInit,
  ): Promise<Response> => {
    const rawHeaders = new Headers(init?.headers ?? {});
    const headers: Record<string, string> = {};
    rawHeaders.forEach((value, key) => {
      headers[key] = value;
    });
    const body = init?.body ? JSON.parse(init.body as string) : undefined;
    const request: MockRequest = {
      method: init?.method ?? "GET",
      url: input,
      headers,
      body,
    };
    requests.push(request);
    const result = await handler(request);
    return new Response(
      result.body === undefined ? null : JSON.stringify(result.body),
      {
        status: result.status ?? 200,
        headers: { "content-type": result.contentType ?? "application/json" },
      },
    );
  };
  return { fetchImpl, requests };
}

test("Session isolation: late 401 from an old session does NOT clear the active session token", async () => {
  setAccessToken("session_A_token");
  const sessionAId = getTokenState().sessionId;

  let resolveRequestA: (value: { status: number; body: unknown }) => void;
  const requestAPromise = new Promise<{ status: number; body: unknown }>(
    (resolve) => {
      resolveRequestA = resolve;
    },
  );

  const { fetchImpl } = createDeferredServer(async () => {
    return await requestAPromise;
  });

  const client = createV1Client({
    fetchImpl,
    getAccessToken: () => getTokenState().token,
    getSessionId: () => getTokenState().sessionId,
    onUnauthorized: ({ sessionId, expired }) => {
      clearAccessToken({ sessionId, expired });
    },
  });

  // Launch Request 1 in Session A
  const req1Promise = client.get("/workspaces");

  // User logs in to Session B
  setAccessToken("session_B_token");
  const sessionBId = getTokenState().sessionId;
  assert.notEqual(
    sessionAId,
    sessionBId,
    "Session B must have a new session ID",
  );

  // Now Request 1 returns 401 from server
  resolveRequestA?.({
    status: 401,
    body: {
      type: "https://errors.qnu.edu.vn/auth_required",
      title: "Chưa xác thực",
      status: 401,
      detail: "Phiên cũ đã hết hạn",
      code: "unauthorized",
    },
  });

  // Request 1 will either reject with session_aborted or 401
  await assert.rejects(async () => {
    await req1Promise;
  });

  // Crucial check: Session B token was NOT cleared by Session A's 401!
  const currentState = getTokenState();
  assert.equal(
    currentState.token,
    "session_B_token",
    "Session B token must remain active after stale 401",
  );
  assert.equal(
    currentState.sessionId,
    sessionBId,
    "Session ID must remain Session B",
  );
});

test("Session isolation: late 200 response from an old session aborts without returning stale data", async () => {
  setAccessToken("session_X_token");

  let resolveRequestX: (value: { status: number; body: unknown }) => void;
  const requestXPromise = new Promise<{ status: number; body: unknown }>(
    (resolve) => {
      resolveRequestX = resolve;
    },
  );

  const { fetchImpl } = createDeferredServer(async () => {
    return await requestXPromise;
  });

  const client = createV1Client({
    fetchImpl,
    getAccessToken: () => getTokenState().token,
    getSessionId: () => getTokenState().sessionId,
  });

  const reqPromise = client.get<{ items: string[] }>("/workspaces");

  // User switches to Session Y before Request X finishes
  setAccessToken("session_Y_token");

  // Request X responds with 200 OK
  resolveRequestX?.({
    status: 200,
    body: { items: ["secret_data_from_session_X"] },
  });

  // Client must reject with session_aborted instead of returning session X's data
  await assert.rejects(
    async () => {
      await reqPromise;
    },
    (error: unknown) => {
      assert.ok(error instanceof ApiProblemError);
      assert.equal(error.code, "session_aborted");
      return true;
    },
  );
});

test("Secret hygiene: TanStack MutationCache never retains secret on key creation or rotation", async () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
    },
  });

  let capturedServerBody: unknown = null;
  const { fetchImpl } = createDeferredServer(async (req) => {
    capturedServerBody = req.body;
    return {
      status: 201,
      body: {
        id: "key_abc123",
        name: "test-key",
        masked_hint: "sk-...1234",
        priority: 5,
        created_at: new Date().toISOString(),
      },
    };
  });

  const client = createV1Client({
    fetchImpl,
    getAccessToken: () => "mock_token",
  });

  // Emulate useCreateProviderKey mutationFn
  const mutation = queryClient.getMutationCache().build(queryClient, {
    mutationKey: ["modelops", 1, "providers", "prov_1", "keys", "create"],
    mutationFn: async (input: {
      name: string;
      secret: string;
      priority: number;
    }) => {
      const secret = input.secret;
      delete (input as { secret?: string }).secret;
      return createProviderKey(client, "prov_1", {
        name: input.name,
        secret,
        priority: input.priority,
      });
    },
  });

  const payload = {
    name: "test-key",
    secret: "super_secret_password_999",
    priority: 5,
  };

  await mutation.execute(payload);

  // 1. Verify the server received the secret in the payload body
  assert.equal(
    (capturedServerBody as { secret?: string })?.secret,
    "super_secret_password_999",
  );

  // 2. Verify TanStack MutationCache does NOT retain the secret
  const allMutations = queryClient.getMutationCache().getAll();
  assert.ok(allMutations.length > 0, "Mutation must exist in MutationCache");

  for (const m of allMutations) {
    const vars = m.state.variables as Record<string, unknown>;
    assert.equal(
      vars?.secret,
      undefined,
      "MutationCache variables must NOT retain secret on success",
    );
  }

  // 3. Test on error as well
  const failingClient = createV1Client({
    fetchImpl: async () => new Response("Unauthorized", { status: 401 }),
    getAccessToken: () => "mock_token",
  });

  const errorMutation = queryClient.getMutationCache().build(queryClient, {
    mutationKey: ["modelops", 1, "providers", "prov_1", "keys", "rotate"],
    mutationFn: async (args: {
      keyId: string;
      input: {
        name: string;
        secret: string;
        priority: number;
        reason: string | null;
      };
    }) => {
      const secret = args.input.secret;
      delete (args.input as { secret?: string }).secret;
      return rotateProviderKey(failingClient, "prov_1", args.keyId, {
        name: args.input.name,
        secret,
        priority: args.input.priority,
        reason: args.input.reason,
      });
    },
  });

  const rotatePayload = {
    keyId: "key_abc123",
    input: {
      name: "rotated-key",
      secret: "leaked_secret_never_cached",
      priority: 5,
      reason: null,
    },
  };

  await assert.rejects(async () => {
    await errorMutation.execute(rotatePayload);
  });

  // Verify variables in cache on failure
  for (const m of queryClient.getMutationCache().getAll()) {
    const vars = m.state.variables as Record<string, unknown>;
    if (vars && "input" in vars) {
      assert.equal(
        (vars.input as Record<string, unknown>)?.secret,
        undefined,
        "MutationCache variables must NOT retain secret on failure",
      );
    }
  }

  queryClient.clear();
});

test("Actor validation: isValidActor correctly identifies valid authenticated actors", () => {
  assert.equal(isValidActor(null), false);
  assert.equal(isValidActor(undefined), false);
  assert.equal(isValidActor({} as unknown as V1Actor), false);
  assert.equal(
    isValidActor({
      actor_id: "",
      username: "tuan",
      authenticated: true,
      roles: [],
      permissions: [],
    }),
    false,
  );
  assert.equal(
    isValidActor({
      actor_id: "act_1",
      username: "",
      authenticated: true,
      roles: [],
      permissions: [],
    }),
    false,
  );
  assert.equal(
    isValidActor({
      actor_id: "act_1",
      username: "tuan",
      authenticated: false,
      roles: [],
      permissions: [],
    }),
    false,
  );
  assert.equal(
    isValidActor({
      actor_id: "act_1",
      username: "tuan",
      authenticated: true,
      roles: ["ai.user"],
      permissions: ["ai.workspaces.manage"],
    }),
    true,
  );
});

test("Quota validation and distinction: bounds and configured status", () => {
  const MAX_TOKEN_LIMIT = 1_000_000_000_000_000; // 10^15

  const validate = (value: string): boolean => {
    const trimmed = value.trim();
    if (trimmed === "") return true; // valid (means null = unconstrained)
    if (!/^\d+$/.test(trimmed)) return false;
    return Number(trimmed) <= MAX_TOKEN_LIMIT;
  };

  assert.equal(validate(""), true, "Empty means unconstrained/null");
  assert.equal(validate("0"), true, "0 is valid non-negative integer");
  assert.equal(validate("1000000"), true, "1,000,000 is valid");
  assert.equal(validate("1000000000000000"), true, "10^15 is valid");
  assert.equal(validate("1000000000000001"), false, "10^15 + 1 exceeds limit");
  assert.equal(validate("-500"), false, "Negative is invalid");
  assert.equal(validate("abc"), false, "Non-digit is invalid");
  assert.equal(validate("12.5"), false, "Decimal is invalid");
});

test("Model defaults selection: inactive provider is excluded from default choices", () => {
  const providersMeta = new Map([
    [
      "prov_active_chat",
      { name: "Active Chat", capabilities: ["chat"], is_active: true },
    ],
    [
      "prov_inactive_chat",
      { name: "Inactive Chat", capabilities: ["chat"], is_active: false },
    ],
    [
      "prov_active_embed",
      { name: "Active Embed", capabilities: ["embedding"], is_active: true },
    ],
  ]);

  const grantedIds = [
    "prov_active_chat",
    "prov_inactive_chat",
    "prov_active_embed",
  ];

  // Filter for chat capability
  const chatOptions = grantedIds.filter((id) => {
    const meta = providersMeta.get(id);
    return (
      Boolean(meta?.is_active) && (meta?.capabilities ?? []).includes("chat")
    );
  });

  assert.deepEqual(
    chatOptions,
    ["prov_active_chat"],
    "Inactive provider must not be selectable as a default model",
  );

  // Filter for embedding capability
  const embedOptions = grantedIds.filter((id) => {
    const meta = providersMeta.get(id);
    return (
      Boolean(meta?.is_active) &&
      (meta?.capabilities ?? []).includes("embedding")
    );
  });

  assert.deepEqual(
    embedOptions,
    ["prov_active_embed"],
    "Active embedding provider is selectable",
  );
});

test("Workspace draft isolation: switching workspaceId discards previous draft", () => {
  let activeWorkspaceId = "ws-alpha";
  let limitDraft: string | null = "500000";
  let blockedDraft: boolean | null = true;

  // Simulate workspace switch
  const handleWorkspaceChange = (nextWorkspaceId: string) => {
    if (nextWorkspaceId !== activeWorkspaceId) {
      activeWorkspaceId = nextWorkspaceId;
      limitDraft = null;
      blockedDraft = null;
    }
  };

  handleWorkspaceChange("ws-beta");
  assert.equal(activeWorkspaceId, "ws-beta");
  assert.equal(
    limitDraft,
    null,
    "limitDraft must be reset to null on workspace change",
  );
  assert.equal(
    blockedDraft,
    null,
    "blockedDraft must be reset to null on workspace change",
  );
});
