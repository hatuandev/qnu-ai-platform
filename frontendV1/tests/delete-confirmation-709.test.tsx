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
import { clearAccessToken, getTokenState, setAccessToken } from "@/app/api/v1";
import { LifecycleActionDialog } from "@/features/lifecycle/action-dialog";
import type { LifecycleAction, ResourceKind } from "@/features/lifecycle/types";

const env = vi.hoisted(() => ({ navigate: vi.fn() }));
vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({ sessionId: getTokenState().sessionId }),
}));
vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => env.navigate,
  Link: ({ children }: { children: ReactNode }) => (
    <a href="#receipt">{children}</a>
  ),
}));
let row: LifecycleAction;
let mode:
  | "ok"
  | "pending"
  | "preview-error"
  | "network-once"
  | "stale"
  | "denied";
let previewCount: number;
let accepted: { body: unknown; key: string | null }[];
const clients: QueryClient[] = [];
const response = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
beforeEach(() => {
  setAccessToken("synthetic-709");
  mode = "ok";
  previewCount = 0;
  accepted = [];
  row = {
    id: "preview-709",
    kind: "source",
    resource_id: "source-709",
    action: "delete",
    reason: "",
    impact: {
      originals_and_raw_evidence: "permanently_deleted",
      permanent: true,
    },
    preview_sha256: "a".repeat(64),
    status: "preview",
    result: null,
    error_code: null,
    expires_at: new Date(Date.now() + 60000).toISOString(),
    accepted_at: null,
    finished_at: null,
  };
  vi.stubGlobal("matchMedia", () => ({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init?: RequestInit) => {
      const path = new URL(input, "http://synthetic.invalid").pathname;
      if (init?.method === "POST" && path.endsWith("/previews")) {
        previewCount++;
        if (mode === "preview-error")
          return response(
            {
              status: 503,
              code: "unavailable",
              detail: "Không đọc được phạm vi xóa.",
            },
            503,
          );
        row = {
          ...row,
          ...JSON.parse(String(init.body)),
          id: `preview-${previewCount}`,
          status: "preview",
        };
        return response(row);
      }
      if (init?.method === "POST") {
        accepted.push({
          body: JSON.parse(String(init.body)),
          key: new Headers(init.headers).get("Idempotency-Key"),
        });
        if (mode === "network-once") {
          mode = "ok";
          throw new TypeError("Mất phản hồi kiểm thử.");
        }
        if (mode === "stale")
          return response(
            {
              status: 409,
              code: "lifecycle_preview_stale",
              detail: "Phạm vi xóa đã thay đổi.",
            },
            409,
          );
        if (mode === "denied")
          return response(
            {
              status: 403,
              code: "workspace_forbidden",
              detail: "Không còn quyền xóa.",
            },
            403,
          );
        row = {
          ...row,
          status: mode === "pending" ? "pending" : "completed",
          accepted_at: new Date().toISOString(),
          result:
            row.kind === "source"
              ? mode === "pending"
                ? { permanent: true }
                : {
                    permanent: true,
                    originals_retained: false,
                    restore_available: false,
                  }
              : null,
        };
      }
      return response(row);
    }),
  );
});
afterEach(() => {
  cleanup();
  clients.forEach((client) => {
    client.clear();
  });
  clients.length = 0;
  clearAccessToken();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});
function mount(kind: ResourceKind = "source", onClose = vi.fn()) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  clients.push(client);
  render(
    <QueryClientProvider client={client}>
      <LifecycleActionDialog
        workspaceId="w"
        target={{ kind, resource_id: "source-709", action: "delete" }}
        label="Tài liệu thử"
        onClose={onClose}
      />
    </QueryClientProvider>,
  );
  return onClose;
}
async function ready() {
  await waitFor(() =>
    expect(
      (
        screen.getByRole("button", {
          name: /^Xóa(?: vĩnh viễn)?$/,
          exact: true,
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(false),
  );
}

test.each(["source", "collection", "document"] as const)(
  "%s deletion asks once without a reason or checkbox",
  async (kind) => {
    mount(kind);
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("checkbox")).toBeNull();
    await ready();
    expect(accepted).toHaveLength(0);
    expect(row.reason).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: /^Xóa(?: vĩnh viễn)?$/, exact: true }),
    );
    await waitFor(() => expect(accepted).toHaveLength(1));
    expect(accepted[0]).toEqual({
      body: { preview_id: "preview-1", preview_sha256: "a".repeat(64) },
      key: "lifecycle:preview-1",
    });
  },
);

test("cancel never calls the deletion endpoint", async () => {
  const close = mount();
  await ready();
  fireEvent.click(screen.getByRole("button", { name: "Hủy", exact: true }));
  expect(close).toHaveBeenCalledOnce();
  expect(accepted).toHaveLength(0);
});

test("preview failure blocks delete and allows retry", async () => {
  mode = "preview-error";
  mount();
  await screen.findByText("Không đọc được phạm vi xóa.");
  expect(accepted).toHaveLength(0);
  mode = "ok";
  fireEvent.click(screen.getByRole("button", { name: "Thử lại", exact: true }));
  await ready();
  expect(accepted).toHaveLength(0);
});

test("lost response retries the same deletion intent", async () => {
  mode = "network-once";
  mount();
  await ready();
  fireEvent.click(
    screen.getByRole("button", { name: /^Xóa(?: vĩnh viễn)?$/, exact: true }),
  );
  const retry = await screen.findByRole("button", {
    name: "Thử lại cùng thao tác",
  });
  fireEvent.click(retry);
  await waitFor(() => expect(accepted).toHaveLength(2));
  expect(accepted[1]).toEqual(accepted[0]);
});

test("accepted source deletion shows progress until the receipt completes", async () => {
  mode = "pending";
  const close = mount();
  await ready();
  fireEvent.click(screen.getByRole("button", { name: "Xóa vĩnh viễn" }));
  await screen.findByText(/Đã nhận yêu cầu xóa/);
  expect(screen.getByRole("button", { name: "Đang xóa…" })).toHaveProperty(
    "disabled",
    true,
  );
  expect(
    screen.queryByRole("button", { name: "Thử lại cùng thao tác" }),
  ).toBeNull();
  expect(close).not.toHaveBeenCalled();

  row = {
    ...row,
    status: "completed",
    result: {
      permanent: true,
      originals_retained: false,
      restore_available: false,
    },
  };
  await act(async () => {
    await clients.at(-1)?.invalidateQueries();
  });
  await waitFor(() => expect(close).toHaveBeenCalledOnce());
  expect(accepted).toHaveLength(1);
});

test("a stale preview requires another explicit delete confirmation", async () => {
  mode = "stale";
  mount();
  await ready();
  fireEvent.click(
    screen.getByRole("button", { name: /^Xóa(?: vĩnh viễn)?$/, exact: true }),
  );
  await screen.findByText("Phạm vi xóa đã thay đổi.");
  mode = "ok";
  fireEvent.click(screen.getByRole("button", { name: "Thử lại", exact: true }));
  await ready();
  expect(accepted).toHaveLength(1);
});

test("revoked permission is shown without claiming deletion succeeded", async () => {
  mode = "denied";
  mount();
  await ready();
  fireEvent.click(
    screen.getByRole("button", { name: /^Xóa(?: vĩnh viễn)?$/, exact: true }),
  );
  await screen.findByText("Không còn quyền xóa.");
  expect(env.navigate).not.toHaveBeenCalled();
});

test("an old account cannot submit a prepared deletion after logout", async () => {
  mount();
  await ready();
  act(() => {
    clearAccessToken();
    setAccessToken("another-synthetic-account");
  });
  fireEvent.click(
    screen.getByRole("button", { name: /^Xóa(?: vĩnh viễn)?$/, exact: true }),
  );
  expect(accepted).toHaveLength(0);
});

test("an expired confirmation never submits a deletion", async () => {
  row.expires_at = new Date(Date.now() - 1000).toISOString();
  mount();
  await ready();
  fireEvent.click(
    screen.getByRole("button", { name: /^Xóa(?: vĩnh viễn)?$/, exact: true }),
  );
  await screen.findByText("Thông tin xác nhận đã hết hạn. Vui lòng thử lại.");
  expect(accepted).toHaveLength(0);
});

test("published input blocks permanent deletion and keeps the user in knowledge", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      response(
        {
          status: 409,
          code: "source_publication_in_use",
          detail: "Tài liệu đang phát hành. Hãy thu hồi trước khi xóa.",
        },
        409,
      ),
    ),
  );
  mount();
  await screen.findByText(
    "Tài liệu đang phát hành. Hãy thu hồi trước khi xóa.",
  );
  expect(
    screen
      .getByRole("button", { name: "Xóa vĩnh viễn", exact: true })
      .hasAttribute("disabled"),
  ).toBe(true);
  expect(accepted).toHaveLength(0);
  expect(env.navigate).not.toHaveBeenCalled();
});

test("a server with soft-delete preview cannot accept permanent deletion", async () => {
  row.impact = { originals_and_raw_evidence: "retained" };
  mount();
  await screen.findByText(/Máy chủ chưa hỗ trợ xóa vĩnh viễn/);
  expect(accepted).toHaveLength(0);
  expect(
    screen
      .getByRole("button", { name: "Xóa vĩnh viễn", exact: true })
      .hasAttribute("disabled"),
  ).toBe(true);
});

test("switching resources prepares a new confirmation instead of reusing the old one", async () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  clients.push(client);
  function view(resourceId: string) {
    return (
      <QueryClientProvider client={client}>
        <LifecycleActionDialog
          workspaceId="w"
          target={{ kind: "source", resource_id: resourceId, action: "delete" }}
          label={resourceId}
          onClose={vi.fn()}
        />
      </QueryClientProvider>
    );
  }
  const rendered = render(view("first"));
  await ready();
  rendered.rerender(view("second"));
  await waitFor(() => expect(previewCount).toBe(2));
  await ready();
  fireEvent.click(
    screen.getByRole("button", { name: /^Xóa(?: vĩnh viễn)?$/, exact: true }),
  );
  await waitFor(() => expect(accepted).toHaveLength(1));
  expect(accepted[0].body).toMatchObject({ preview_id: "preview-2" });
  expect(row.resource_id).toBe("second");
});
