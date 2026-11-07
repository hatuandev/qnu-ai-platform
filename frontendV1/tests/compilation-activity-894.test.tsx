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
import { ApiProblemError, v1Client } from "@/app/api/v1";
import {
  CompilationActivityProvider,
  useCompilationActivity,
} from "@/features/knowledge/compilation-activity";
import { CompilationActivityPanel } from "@/features/knowledge/compilation-activity-panel";
import {
  compilationKeys,
  useCreateCompilationMutation,
} from "@/features/knowledge/compilation-queries";
import type { CompilationRunResponse } from "@/features/knowledge/compilation-types";

const auth = vi.hoisted(() => ({
  sessionId: 1,
  isAuthenticated: true,
  actor: { actor_id: "actor-a" },
}));
vi.mock("@/app/auth/v1", () => ({ useV1Auth: () => auth }));
vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    params,
    ...props
  }: {
    children: ReactNode;
    params: Record<string, string>;
  }) => (
    <a
      {...props}
      href={`/workspaces/${params.workspaceId}/collections/${params.collectionId}/compilations/${params.runId}`}
    >
      {children}
    </a>
  ),
}));
const run: CompilationRunResponse = {
  id: "cmp-a",
  workspace_id: "ws-a",
  collection_id: "col-a",
  topic: "Tài liệu tuyển sinh",
  status: "queued",
  generation: 1,
  provider_id: "provider",
  requested_by: "actor-a",
  requested_at: "2026-11-07T01:00:00Z",
  started_at: null,
  finished_at: null,
  dispatched_at: null,
  attempt_count: 0,
  error_code: null,
  input_sha256: "sha",
  usage_tokens: null,
  parent_run_id: null,
  origin: "compiler",
};
const observed = (status = "running", total = 4, completed = 1) => ({
  run_id: run.id,
  status,
  total,
  completed,
  latest_output_partial: false,
});
let client: QueryClient;
function Actions() {
  const activity = useCompilationActivity();
  const create = useCreateCompilationMutation("ws-a", "col-a");
  return (
    <>
      <button type="button" onClick={() => activity?.track(run)}>
        Theo dõi
      </button>
      <button
        type="button"
        onClick={() =>
          activity?.track({
            ...run,
            id: "cmp-b",
            workspace_id: "ws-b",
            topic: "Tài liệu khác",
          })
        }
      >
        Thêm lượt
      </button>
      <button
        type="button"
        onClick={() =>
          create.mutate({
            input: { topic: run.topic, ocr_run_ids: ["ocr-a"] },
            idempotencyKey: "create-once",
          })
        }
      >
        Biên soạn
      </button>
    </>
  );
}
function App({ page = "Nguồn" }: { page?: string }) {
  return (
    <QueryClientProvider client={client}>
      <CompilationActivityProvider>
        <p>{page}</p>
        <Actions />
        <CompilationActivityPanel />
      </CompilationActivityProvider>
    </QueryClientProvider>
  );
}
async function track() {
  fireEvent.click(screen.getByText("Theo dõi"));
  await waitFor(() =>
    expect(screen.getByText("1/4 nhóm hoàn tất")).toBeTruthy(),
  );
}
beforeEach(() => {
  auth.sessionId = 1;
  auth.actor.actor_id = "actor-a";
  auth.isAuthenticated = true;
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  vi.spyOn(v1Client, "get").mockImplementation(async () => observed() as never);
  vi.spyOn(v1Client, "post").mockResolvedValue({
    run,
    created: true,
    dispatched: true,
  });
});
afterEach(() => {
  cleanup();
  client.clear();
  vi.useRealTimers();
});

test("successful creation registers one background run and reads the authorized progress path", async () => {
  render(<App />);
  fireEvent.click(screen.getByText("Biên soạn", { exact: true }));
  await waitFor(() => expect(screen.getByText("25%")).toBeTruthy());
  expect(v1Client.post).toHaveBeenCalledTimes(1);
  expect(v1Client.get).toHaveBeenCalledWith(
    "/workspaces/ws-a/collections/col-a/compilation-runs/cmp-a/progress",
    { signal: expect.any(AbortSignal) },
  );
  expect(
    screen.getByRole("link", { name: run.topic }).getAttribute("href"),
  ).toContain("/ws-a/collections/col-a/compilations/cmp-a");
});
test("route changes and tracking a replay preserve one entry; collapse never cancels or resubmits", async () => {
  const view = render(<App />);
  await track();
  view.rerender(<App page="Autre page" />);
  fireEvent.click(screen.getByText("Theo dõi"));
  expect(screen.getAllByRole("link", { name: run.topic })).toHaveLength(1);
  fireEvent.click(
    screen.getByRole("button", { name: "Thu gọn tiến độ biên soạn" }),
  );
  expect(screen.queryByRole("link", { name: run.topic })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Mở tiến độ biên soạn" }));
  expect(screen.getByRole("link", { name: run.topic })).toBeTruthy();
  expect(v1Client.post).not.toHaveBeenCalled();
});
test("progress continues while collapsed and stops polling after a terminal response", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  render(<App />);
  await track();
  fireEvent.click(
    screen.getByRole("button", { name: "Thu gọn tiến độ biên soạn" }),
  );
  vi.mocked(v1Client.get).mockResolvedValue(observed("completed", 4, 4));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(3100);
  });
  expect(v1Client.get).toHaveBeenCalledTimes(2);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(10000);
  });
  expect(v1Client.get).toHaveBeenCalledTimes(2);
  fireEvent.click(screen.getByRole("button", { name: "Mở tiến độ biên soạn" }));
  expect(screen.getByText("Đã biên soạn · Mở để xem và duyệt")).toBeTruthy();
});

test("closing clears the whole panel without cancelling jobs, and a newly tracked run opens it again", async () => {
  render(<App />);
  await track();
  fireEvent.click(screen.getByText("Thêm lượt"));
  await waitFor(() => expect(v1Client.get).toHaveBeenCalledTimes(2));
  fireEvent.click(
    screen.getByRole("button", { name: "Đóng bảng tiến độ biên soạn" }),
  );
  expect(screen.queryByRole("link", { name: run.topic })).toBeNull();
  expect(screen.queryByRole("link", { name: "Tài liệu khác" })).toBeNull();
  expect(
    screen.queryByRole("button", { name: "Mở tiến độ biên soạn" }),
  ).toBeNull();
  expect(v1Client.post).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText("Thêm lượt"));
  expect(screen.getByRole("link", { name: "Tài liệu khác" })).toBeTruthy();
  expect(
    screen.getByRole("button", { name: "Đóng bảng tiến độ biên soạn" }),
  ).toBeTruthy();
});

test("the close control remains available when collapsed or completed", async () => {
  vi.mocked(v1Client.get).mockResolvedValue(observed("completed", 4, 4));
  render(<App />);
  fireEvent.click(screen.getByText("Theo dõi"));
  await waitFor(() =>
    expect(screen.getByText("Đã biên soạn · Mở để xem và duyệt")).toBeTruthy(),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Thu gọn tiến độ biên soạn" }),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Đóng bảng tiến độ biên soạn" }),
  );
  expect(
    screen.queryByRole("button", { name: "Đóng bảng tiến độ biên soạn" }),
  ).toBeNull();
  expect(v1Client.post).not.toHaveBeenCalled();
});
test("zero planned groups does not invent a percentage", async () => {
  vi.mocked(v1Client.get).mockResolvedValue(observed("queued", 0, 0));
  render(<App />);
  fireEvent.click(screen.getByText("Theo dõi"));
  await waitFor(() => expect(v1Client.get).toHaveBeenCalledOnce());
  expect(screen.queryByRole("progressbar")).toBeNull();
  expect(screen.getByRole("status").textContent).toBe("Đang chờ");
});
test("multiple workspaces have separate progress keys and links", async () => {
  render(<App />);
  await track();
  fireEvent.click(screen.getByText("Thêm lượt"));
  await waitFor(() => expect(v1Client.get).toHaveBeenCalledTimes(2));
  expect(
    screen.getByRole("link", { name: "Tài liệu khác" }).getAttribute("href"),
  ).toContain("/ws-b/");
  expect(
    client.getQueryData([
      ...compilationKeys.run("ws-a", "col-a", "cmp-a", 1),
      "progress",
    ]),
  ).toBeTruthy();
  expect(
    client.getQueryData([
      ...compilationKeys.run("ws-b", "col-a", "cmp-b", 1),
      "progress",
    ]),
  ).toBeTruthy();
});
test("logout, session change or actor change clears the panel before another actor can see it", async () => {
  const view = render(<App />);
  await track();
  auth.actor.actor_id = "actor-b";
  view.rerender(<App />);
  expect(screen.queryByRole("link", { name: run.topic })).toBeNull();
  await track();
  auth.sessionId = 2;
  view.rerender(<App />);
  expect(screen.queryByRole("link", { name: run.topic })).toBeNull();
  await track();
  auth.isAuthenticated = false;
  view.rerender(<App />);
  expect(
    screen.queryByRole("button", { name: "Thu gọn tiến độ biên soạn" }),
  ).toBeNull();
});
test.each([403, 404])(
  "losing access (%s) removes tracking without sending work",
  async (status) => {
    vi.mocked(v1Client.get).mockRejectedValue(
      new ApiProblemError({
        status,
        code: "unavailable",
        message: "Unavailable",
      }),
    );
    render(<App />);
    fireEvent.click(screen.getByText("Theo dõi"));
    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: "Thu gọn tiến độ biên soạn" }),
      ).toBeNull(),
    );
    expect(v1Client.post).not.toHaveBeenCalled();
  },
);
test("network error is a monitoring warning, not a failed job or an inference retry", async () => {
  vi.mocked(v1Client.get).mockRejectedValue(new Error("Network disconnected"));
  render(<App />);
  fireEvent.click(screen.getByText("Theo dõi"));
  await waitFor(() =>
    expect(screen.getByText(/Mất kết nối cập nhật/)).toBeTruthy(),
  );
  expect(screen.queryByRole("progressbar")).toBeNull();
  expect(v1Client.post).not.toHaveBeenCalled();
});

test("a creation response arriving after account change cannot register in the new session", async () => {
  let finish: (value: unknown) => void = () => {};
  vi.mocked(v1Client.post).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const view = render(<App />);
  fireEvent.click(screen.getByText("Biên soạn", { exact: true }));
  auth.sessionId = 2;
  auth.actor.actor_id = "actor-b";
  view.rerender(<App />);
  await act(async () => {
    finish({ run, created: true, dispatched: true });
  });
  expect(screen.queryByRole("link", { name: run.topic })).toBeNull();
  expect(v1Client.get).not.toHaveBeenCalled();
});
test.each(["failed", "uncertain", "cancelled"])(
  "terminal %s remains distinct from completion",
  async (status) => {
    vi.mocked(v1Client.get).mockResolvedValue({
      ...observed(status),
      latest_output_partial: true,
    });
    render(<App />);
    fireEvent.click(screen.getByText("Theo dõi"));
    await waitFor(() =>
      expect(screen.getByText("Bản nháp còn phần chưa hoàn tất.")).toBeTruthy(),
    );
    expect(screen.queryByText("Đã biên soạn · Mở để xem và duyệt")).toBeNull();
    expect(v1Client.post).not.toHaveBeenCalled();
  },
);
