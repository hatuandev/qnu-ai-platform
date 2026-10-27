// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import {
  clearAccessToken,
  getTokenState,
  setAccessToken,
} from "@/app/api/v1/session-token";
import type { CallerWorkspaceRole } from "@/app/auth/v1/permissions";
import { LifecycleActionDialog } from "@/features/lifecycle/action-dialog";
import {
  LifecycleReceipt,
  LifecycleReceiptView,
} from "@/features/lifecycle/action-receipt";
import { ResourcesPage } from "@/features/lifecycle/resources-page";
import type { LifecycleAction } from "@/features/lifecycle/types";
import { OperationsPage } from "@/features/operations/operations-page";
import { RecoveryDialog } from "@/features/operations/recovery-dialog";
import type { JobView, OperationAction } from "@/features/operations/types";

const env = vi.hoisted(() => ({
  role: { kind: "member", role: "admin" } as CallerWorkspaceRole,
  navigate: vi.fn(),
}));
vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({ sessionId: getTokenState().sessionId }),
}));
vi.mock("@/features/workspaces/queries", () => ({
  useCallerWorkspaceRole: () => ({ role: env.role, isPending: false }),
}));
vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => env.navigate,
  Link: ({ children, to }: { children: ReactNode; to: string }) => (
    <a href="#synthetic-receipt" data-destination={to}>
      {children}
    </a>
  ),
}));
const clients: QueryClient[] = [];
let action: LifecycleAction;
let operation: OperationAction;
let acceptMode: "success" | "network-once" | "stale" | "denied";
let postCalls: {
  path: string;
  body: Record<string, unknown>;
  key: string | null;
}[];
let getCalls: string[];
let delayedPreview: Promise<Response> | null;
let failJobs: boolean;
let trashCount: number;
let detailJob: JobView;
let acceptStatus: "completed" | "pending";
const response = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const job: JobView = {
  kind: "index",
  id: "job-one",
  workspace_id: "w",
  collection_id: "c",
  status: "running",
  created_at: "2026-10-27T00:00:00Z",
  started_at: null,
  finished_at: null,
  lease_expires_at: null,
  error_code: null,
  attempts: 1,
  progress_done: 4,
  progress_total: null,
  usage_tokens: null,
  provider_id: "provider",
  recovery_allowed: true,
  recovery_reason: "expired_lease",
};
beforeEach(() => {
  setAccessToken("synthetic-678-session");
  env.role = { kind: "member", role: "admin" };
  env.navigate.mockReset();
  acceptMode = "success";
  postCalls = [];
  getCalls = [];
  delayedPreview = null;
  failJobs = false;
  trashCount = 0;
  acceptStatus = "completed";
  detailJob = {
    ...job,
    status: "uncertain",
    recovery_allowed: false,
    recovery_reason: "uncertain_inference",
  };
  action = {
    id: "life-one",
    kind: "source",
    resource_id: "source",
    action: "archive",
    reason: "Synthetic reason",
    impact: {
      jobs_to_cancel: 2,
      originals_and_raw_evidence: "retained",
      restore_requires_new_index: true,
    },
    preview_sha256: "a".repeat(64),
    status: "preview",
    result: null,
    error_code: null,
    expires_at: new Date(Date.now() + 60000).toISOString(),
    accepted_at: null,
    finished_at: null,
  };
  operation = {
    id: "operation-one",
    workspace_id: "w",
    kind: "index",
    job_id: "job-one",
    action: "recover",
    reason: "Synthetic reason",
    preview_sha256: "b".repeat(64),
    status: "preview",
    expires_at: new Date(Date.now() + 60000).toISOString(),
    dispatched_at: null,
  };
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
    })),
  );
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init?: RequestInit) => {
      const url = new URL(input, "http://synthetic.invalid");
      const path = url.pathname;
      const method = init?.method ?? "GET";
      if (method === "POST") {
        const body = JSON.parse(String(init?.body));
        postCalls.push({
          path,
          body,
          key: new Headers(init?.headers).get("Idempotency-Key"),
        });
        if (path.endsWith("/lifecycle/previews")) {
          action = { ...action, ...body };
          return delayedPreview ?? response(action);
        }
        if (path.endsWith("/recovery-preview")) {
          operation.reason = body.reason;
          return response(operation);
        }
        if (acceptMode === "network-once") {
          acceptMode = "success";
          throw new TypeError("Synthetic disconnected response");
        }
        if (acceptMode === "stale")
          return response(
            {
              status: 409,
              code: path.includes("lifecycle")
                ? "lifecycle_preview_stale"
                : "operation_preview_stale",
              detail: "Synthetic snapshot changed",
            },
            409,
          );
        if (acceptMode === "denied")
          return response(
            {
              status: 403,
              code: "workspace_access_denied",
              detail: "Synthetic permission revoked",
            },
            403,
          );
        if (path.endsWith("/lifecycle/actions")) {
          action = {
            ...action,
            status: acceptStatus,
            accepted_at: new Date().toISOString(),
            finished_at: new Date().toISOString(),
          };
          return response(action);
        }
        if (path.endsWith("/operations/actions")) {
          operation = {
            ...operation,
            status: "dispatched",
            dispatched_at: new Date().toISOString(),
          };
          return response(operation);
        }
      }
      getCalls.push(path);
      if (path.includes("/lifecycle/actions/")) return response(action);
      if (path.includes("/operations/actions/")) return response(operation);
      if (path.endsWith("/lifecycle/resources")) {
        const offset = Number(url.searchParams.get("offset"));
        return response({
          items: Array.from({ length: trashCount }, (_, i) => ({
            kind: "source",
            resource_id: `source-${i}`,
            status: "deleted",
            updated_at: "2026-10-27T00:00:00Z",
          })).slice(offset, offset + 21),
          limit: 21,
          offset,
        });
      }
      if (path.endsWith("/operations/summary"))
        return response({
          jobs: [{ kind: "index", status: "running", count: 1 }],
          usage: [
            {
              status: "uncertain",
              records: 1,
              observed_tokens: null,
              reserved_tokens: 64,
              observed_cost_usd: null,
              cost_records: 0,
            },
          ],
        });
      if (path.endsWith("/operations/readiness"))
        return response({
          scope: "dependency_and_modelops_configuration",
          ready: false,
          checks: {
            storage: { ok: false, code: "no_source_to_probe" },
            quota: { ok: false, configured: false, remaining_tokens: null },
          },
          live_inference_verified: false,
          production_auth_configured: false,
          reconcile_enabled: false,
        });
      if (path.endsWith("/operations/jobs"))
        return failJobs
          ? response(
              {
                status: 503,
                code: "database_unavailable",
                detail: "Synthetic jobs unavailable",
              },
              503,
            )
          : response({
              items: [{ ...job, status: "uncertain", recovery_allowed: false }],
              total: 1,
              limit: 20,
              offset: 0,
            });
      if (path.includes("/operations/jobs/")) return response(detailJob);
      throw new Error(`Unexpected synthetic endpoint ${method} ${path}`);
    }),
  );
});
afterEach(() => {
  cleanup();
  for (const client of clients.splice(0)) client.clear();
  clearAccessToken();
  vi.unstubAllGlobals();
});
function mount(element: ReactNode) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity },
      mutations: { retry: false },
    },
  });
  clients.push(client);
  return {
    client,
    ...render(
      <QueryClientProvider client={client}>{element}</QueryClientProvider>,
    ),
  };
}
function dialog() {
  return (
    <LifecycleActionDialog
      workspaceId="w"
      target={{ kind: "source", resource_id: "source", action: "archive" }}
      label="Synthetic source"
      onClose={vi.fn()}
    />
  );
}
async function preview() {
  fireEvent.change(screen.getByLabelText("Lý do"), {
    target: { value: "Synthetic reason" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Xem trước tác động" }));
  await screen.findByText("Bản gốc và bằng chứng OCR");
}
test("human acknowledgement is required after impact preview; confirmation uses exact server hash", async () => {
  mount(dialog());
  await preview();
  const confirm = screen.getByRole("button", { name: "Xác nhận thao tác" });
  expect(confirm.hasAttribute("disabled")).toBe(true);
  fireEvent.click(confirm);
  expect(
    postCalls.filter((c) => c.path.endsWith("/lifecycle/actions")),
  ).toHaveLength(0);
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(confirm);
  await waitFor(() => expect(action.status).toBe("completed"));
  expect(postCalls[1]).toMatchObject({
    body: { preview_id: "life-one", preview_sha256: "a".repeat(64) },
    key: "lifecycle:life-one",
  });
  await waitFor(() =>
    expect(env.navigate).toHaveBeenCalledWith(
      expect.objectContaining({ to: "/workspaces/$workspaceId/resources" }),
    ),
  );
});
test("retry after a disconnected accept retains the same preview, body and idempotency key", async () => {
  acceptMode = "network-once";
  mount(dialog());
  await preview();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Xác nhận thao tác" }));
  const retry = await screen.findByRole("button", {
    name: "Thử lại cùng thao tác",
  });
  await waitFor(() => expect(retry.hasAttribute("disabled")).toBe(false));
  fireEvent.click(retry);
  await waitFor(() => expect(action.status).toBe("completed"));
  const accepts = postCalls.filter((c) =>
    c.path.endsWith("/lifecycle/actions"),
  );
  expect(accepts).toHaveLength(2);
  expect(accepts[1]).toEqual(accepts[0]);
  expect(postCalls.filter((c) => c.path.endsWith("/previews"))).toHaveLength(1);
});
test("stale preview stops confirmation and requires a new explicit preview", async () => {
  acceptMode = "stale";
  mount(dialog());
  await preview();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Xác nhận thao tác" }));
  await screen.findByRole("button", { name: "Xem trước tác động" });
  expect(postCalls).toHaveLength(2);
  expect(action.status).toBe("preview");
});
test("expired preview never reaches the acceptance endpoint", async () => {
  action.expires_at = new Date(Date.now() - 1000).toISOString();
  mount(dialog());
  await preview();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Xác nhận thao tác" }));
  await screen.findByText(/Bản xem trước đã hết hạn/);
  expect(postCalls).toHaveLength(1);
});
test("revoked server permission is shown as an error without reporting completion", async () => {
  acceptMode = "denied";
  mount(dialog());
  await preview();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Xác nhận thao tác" }));
  await screen.findByText("Synthetic permission revoked");
  expect(action.status).toBe("preview");
  expect(env.navigate).not.toHaveBeenCalled();
});
test("late preview after logout must not populate cache for the old or new user", async () => {
  let release!: (value: Response) => void;
  delayedPreview = new Promise((resolve) => {
    release = resolve;
  });
  const oldSession = getTokenState().sessionId;
  const view = mount(dialog());
  fireEvent.change(screen.getByLabelText("Lý do"), {
    target: { value: "Synthetic reason" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Xem trước tác động" }));
  await waitFor(() => expect(postCalls).toHaveLength(1));
  act(() => setAccessToken("synthetic-new-user"));
  await act(async () => release(response(action)));
  expect(
    view.client.getQueryData([
      "v1",
      oldSession,
      "lifecycle-action",
      "w",
      "life-one",
    ]),
  ).toBeUndefined();
  expect(screen.queryByText("Bản gốc và bằng chứng OCR")).toBeNull();
});
test("an accepted pending lifecycle receipt can be continued after a fresh page load", async () => {
  action = {
    ...action,
    action: "cleanup",
    kind: "index",
    status: "pending",
    accepted_at: new Date().toISOString(),
  };
  mount(<LifecycleReceipt workspaceId="w" actionId="life-one" />);
  fireEvent.click(
    await screen.findByRole("button", {
      name: "Tiếp tục thao tác đã xác nhận",
    }),
  );
  await waitFor(() => expect(action.status).toBe("completed"));
  expect(postCalls).toHaveLength(1);
  expect(postCalls[0]).toMatchObject({
    body: { preview_id: "life-one", preview_sha256: "a".repeat(64) },
    key: "lifecycle:life-one",
  });
});
test("recovery requires confirmation, then shows dispatched rather than claiming job completion", async () => {
  mount(<RecoveryDialog workspaceId="w" job={job} onClose={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Lý do"), {
    target: { value: "Synthetic reason" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Xem trước giao lại" }));
  const confirm = await screen.findByRole("button", {
    name: "Xác nhận giao lại",
  });
  expect(confirm.hasAttribute("disabled")).toBe(true);
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(confirm);
  await screen.findByText(/Đã giao lại/);
  expect(operation.status).toBe("dispatched");
  expect(postCalls[1].key).toBe("operations:operation-one");
});
test("ordinary members cannot call the operations or readiness endpoints", async () => {
  env.role = { kind: "member", role: "member" };
  mount(
    <OperationsPage
      workspaceId="w"
      search={{ page: 1, pageSize: 20 }}
      onSearch={vi.fn()}
    />,
  );
  expect(screen.getByRole("alert").textContent).toMatch(/Cần quyền/);
  await act(async () => {
    await Promise.resolve();
  });
  expect(getCalls).toHaveLength(0);
});
test("reviewer sees unknown metrics honestly and cannot fetch readiness or recover uncertain jobs", async () => {
  env.role = { kind: "member", role: "reviewer" };
  mount(
    <OperationsPage
      workspaceId="w"
      search={{ page: 1, pageSize: 20, jobKind: "index", jobId: "job-one" }}
      onSearch={vi.fn()}
    />,
  );
  await screen.findByText("Điều kiện giao lại từ server:", { exact: false });
  expect(screen.getAllByText(/Chưa có số đo/).length).toBeGreaterThan(0);
  expect(
    screen.queryByRole("button", { name: "Xem trước giao lại" }),
  ).toBeNull();
  expect(getCalls.some((path) => path.endsWith("/readiness"))).toBe(false);
});
test("admin readiness stays distinct from live inference and blocks uncertain job recovery", async () => {
  mount(
    <OperationsPage
      workspaceId="w"
      search={{ page: 1, pageSize: 20, jobKind: "index", jobId: "job-one" }}
      onSearch={vi.fn()}
    />,
  );
  await screen.findByText("Chưa có nguồn để kiểm tra đọc tệp.");
  expect(
    screen.getByText(/Kiểm tra này không gọi model suy luận thật/),
  ).toBeTruthy();
  expect(
    screen
      .getByRole("button", { name: "Xem trước giao lại" })
      .hasAttribute("disabled"),
  ).toBe(true);
});
test("empty trash remains an honest empty state, not a failed mutation or fake success", async () => {
  mount(<ResourcesPage workspaceId="w" page={1} onPageChange={vi.fn()} />);
  await screen.findByText(/Trang này không có tài nguyên/);
  expect(postCalls).toHaveLength(0);
  expect(
    screen.getByRole("button", { name: /Sau/ }).hasAttribute("disabled"),
  ).toBe(true);
});
test("a failed jobs request is an error rather than an empty list", async () => {
  failJobs = true;
  mount(
    <OperationsPage
      workspaceId="w"
      search={{ page: 1, pageSize: 20 }}
      onSearch={vi.fn()}
    />,
  );
  await screen.findByText("Synthetic jobs unavailable");
  expect(screen.queryByText("Không có tác vụ khớp bộ lọc.")).toBeNull();
});
test("trash pagination uses the extra row, exposes only 20 resources and honors editor restore limits", async () => {
  trashCount = 21;
  env.role = { kind: "member", role: "editor" };
  mount(<ResourcesPage workspaceId="w" page={1} onPageChange={vi.fn()} />);
  await screen.findByText(/source-0 ·/);
  expect(screen.getAllByText("Trong thùng rác")).toHaveLength(20);
  expect(
    screen.queryByRole("button", { name: /Thao tác vòng đời:/ }),
  ).toBeNull();
  expect(
    screen.getByRole("button", { name: /Sau/ }).hasAttribute("disabled"),
  ).toBe(false);
});
test("a conversation owner can follow a receipt without needing operations permissions", () => {
  env.role = { kind: "member", role: "member" };
  mount(
    <LifecycleReceiptView
      workspaceId="w"
      action={{ ...action, kind: "conversation", status: "completed" }}
    />,
  );
  expect(
    screen
      .getByRole("link", { name: "Theo dõi biên nhận" })
      .getAttribute("data-destination"),
  ).toBe("/workspaces/$workspaceId/resources");
});

test("an accepted pending recovery can continue after reload using its original key", async () => {
  operation.status = "pending";
  mount(
    <OperationsPage
      workspaceId="w"
      search={{ page: 1, pageSize: 20, operationActionId: "operation-one" }}
      onSearch={vi.fn()}
    />,
  );
  fireEvent.click(
    await screen.findByRole("button", {
      name: "Tiếp tục giao lại đã xác nhận",
    }),
  );
  await waitFor(() => expect(operation.status).toBe("dispatched"));
  expect(postCalls).toHaveLength(1);
  expect(postCalls[0].key).toBe("operations:operation-one");
  expect(postCalls[0].body).toEqual({
    preview_id: "operation-one",
    preview_sha256: "b".repeat(64),
  });
});
test("editor cannot recover a backup even when its job is otherwise recoverable", async () => {
  env.role = { kind: "member", role: "editor" };
  detailJob = { ...job, kind: "backup", recovery_allowed: true };
  mount(
    <OperationsPage
      workspaceId="w"
      search={{ page: 1, pageSize: 20, jobKind: "backup", jobId: "job-one" }}
      onSearch={vi.fn()}
    />,
  );
  await screen.findByText(/Điều kiện giao lại từ server:/);
  expect(
    screen
      .getByRole("button", { name: "Xem trước giao lại" })
      .hasAttribute("disabled"),
  ).toBe(true);
  expect(getCalls.some((path) => path.endsWith("/readiness"))).toBe(false);
});

test("replacement keeps the serving version until the server reports completion", async () => {
  acceptStatus = "pending";
  const view = mount(
    <LifecycleActionDialog
      workspaceId="w"
      target={{
        kind: "document",
        resource_id: "doc",
        action: "replace",
        replacement_version_id: "approved-version",
      }}
      label="Synthetic approved replacement"
      onClose={vi.fn()}
    />,
  );
  await preview();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Xác nhận thao tác" }));
  await screen.findByText(/Bản cũ tiếp tục phục vụ trong khi chỉ mục mới/);
  expect(postCalls[0].body).toMatchObject({
    action: "replace",
    replacement_version_id: "approved-version",
  });
  expect(screen.queryByText("Hoàn tất")).toBeNull();
  expect(env.navigate).not.toHaveBeenCalled();
  action = {
    ...action,
    status: "completed",
    result: {
      index_run_id: "new-index",
      publication_decision_id: "new-publication",
    },
  };
  await act(async () => {
    await view.client.invalidateQueries({
      queryKey: [
        "v1",
        getTokenState().sessionId,
        "lifecycle-action",
        "w",
        "life-one",
      ],
    });
  });
  await screen.findByText("Hoàn tất");
  expect(
    screen.queryByText(/Bản cũ tiếp tục phục vụ trong khi chỉ mục mới/),
  ).toBeNull();
});
