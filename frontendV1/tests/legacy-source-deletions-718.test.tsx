// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { clearAccessToken, getTokenState, setAccessToken } from "@/app/api/v1";
import { PendingSourceDeletions } from "@/features/lifecycle/pending-source-deletions";
import type { LifecycleAction } from "@/features/lifecycle/types";
import { isSourcePurgeCompleted } from "@/features/lifecycle/types";

const dialog = vi.hoisted(() => vi.fn());
vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({ sessionId: getTokenState().sessionId }),
}));
vi.mock("@/features/lifecycle/action-dialog", () => ({
  LifecycleActionDialog: (props: { label: string }) => {
    dialog(props);
    return <div role="dialog">{props.label}</div>;
  },
}));
const clients: QueryClient[] = [];
let mode: "legacy" | "pending" | "old-server";
let writes: number;
const pending: LifecycleAction = {
  id: "accepted",
  resource_id: "private-source",
  kind: "source",
  action: "delete",
  status: "pending",
  accepted_at: "2026-10-29T00:00:00Z",
  impact: { resource_label: "Synthetic pending document" },
  result: { permanent: true },
  reason: "Synthetic confirmed deletion",
  preview_sha256: "a".repeat(64),
  error_code: null,
  expires_at: "2026-10-29T00:05:00Z",
  finished_at: null,
};
const response = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json" },
  });
beforeEach(() => {
  setAccessToken("synthetic-718");
  mode = "legacy";
  writes = 0;
  dialog.mockClear();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method && init.method !== "GET") writes++;
      if (mode === "old-server") return response({ detail: "Not Found" }, 404);
      const path = new URL(url, "http://synthetic.invalid").pathname;
      if (path.endsWith("/legacy"))
        return response({
          items:
            mode === "legacy"
              ? [
                  {
                    source_id: "private-source",
                    title: "Synthetic legacy document",
                  },
                ]
              : [],
          total: mode === "legacy" ? 1 : 0,
          limit: 20,
          offset: 0,
        });
      return response(mode === "pending" ? [pending] : []);
    }),
  );
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
});
afterEach(() => {
  cleanup();
  for (const client of clients) client.clear();
  clients.length = 0;
  clearAccessToken();
  vi.unstubAllGlobals();
});
function mount() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  clients.push(client);
  return render(
    <QueryClientProvider client={client}>
      <PendingSourceDeletions workspaceId="w" collectionId="c" enabled />
    </QueryClientProvider>,
  );
}
test("legacy file stays visible for a new confirmation without automatically deleting it", async () => {
  mount();
  await screen.findByText("Synthetic legacy document");
  expect(screen.queryByText("private-source")).toBeNull();
  expect(dialog).not.toHaveBeenCalled();
  fireEvent.keyDown(
    screen.getByRole("button", {
      name: "Thao tác với Synthetic legacy document",
    }),
    { key: "Enter" },
  );
  fireEvent.click(
    await screen.findByRole("menuitem", { name: "Hoàn tất xóa" }),
  );
  await screen.findByRole("dialog");
  expect(dialog).toHaveBeenCalledWith(
    expect.objectContaining({
      target: {
        kind: "source",
        resource_id: "private-source",
        action: "delete",
      },
      initialAction: undefined,
    }),
  );
  expect(writes).toBe(0);
});
test("pending deletion reuses its accepted receipt", async () => {
  mode = "pending";
  mount();
  const menu = await screen.findByRole("button", { name: "Thao tác xóa" });
  fireEvent.keyDown(menu, { key: "Enter" });
  fireEvent.click(
    await screen.findByRole("menuitem", { name: "Theo dõi / tiếp tục xóa" }),
  );
  expect(dialog).toHaveBeenCalledWith(
    expect.objectContaining({ initialAction: pending }),
  );
  expect(writes).toBe(0);
});
test("an old server explains the required API and worker reload", async () => {
  mode = "old-server";
  mount();
  await screen.findByText(/Máy chủ chưa nạp chức năng xóa mới/);
  expect(
    screen.getByRole("button", { name: "Tải lại trạng thái" }),
  ).toBeTruthy();
  expect(writes).toBe(0);
});

test("a completed old soft-delete receipt cannot be displayed as a completed purge", () => {
  expect(
    isSourcePurgeCompleted({
      ...pending,
      status: "completed",
      result: {
        originals_retained: true,
        restore_available: true,
      },
    }),
  ).toBe(false);
  expect(
    isSourcePurgeCompleted({
      ...pending,
      status: "completed",
      result: {
        permanent: true,
        originals_retained: false,
        restore_available: false,
      },
    }),
  ).toBe(true);
});
