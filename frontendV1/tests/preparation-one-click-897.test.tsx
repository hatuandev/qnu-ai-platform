// @vitest-environment jsdom
/**
 * G2: the normal prep screen offers one action and no technical choices,
 * and reports the pinned policy outcome truthfully.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { PreparationDialog } from "@/features/knowledge/preparation-dialog";
import type { PreparationIntent } from "@/features/knowledge/preparation-types";

const state = vi.hoisted(() => ({
  intents: [] as PreparationIntent[],
  detail: null as PreparationIntent | null,
  create: vi.fn(),
  cancel: vi.fn(),
}));

vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({ sessionId: 1, isAuthenticated: true }),
}));
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
vi.mock("@/features/knowledge/preparation-queries", () => ({
  usePreparationIntentsQuery: () => ({
    data: state.intents,
    isLoading: false,
    isError: false,
  }),
  usePreparationIntentQuery: () => ({
    data: state.detail,
    isError: false,
    refetch: vi.fn(),
  }),
  useCreatePreparationIntentMutation: () => ({
    isPending: false,
    mutateAsync: state.create,
  }),
  useCancelPreparationIntentMutation: () => ({
    isPending: false,
    mutateAsync: state.cancel,
  }),
}));
vi.mock("@/features/knowledge/compilation-queries", () => ({
  compilationKeys: { run: (...parts: unknown[]) => ["run", ...parts] },
}));
vi.mock("@/features/knowledge/compilation-requests", () => ({
  getCompilationProgress: () => new Promise(() => {}),
}));

function intent(overrides: Partial<PreparationIntent> = {}): PreparationIntent {
  return {
    id: "prep-1",
    workspace_id: "ws-1",
    collection_id: "col-1",
    source_id: "src-1",
    revision_id: "rev-1",
    revision_no: 2,
    revision_sha256: "a".repeat(64),
    mode: "auto",
    status: "queued",
    topic: "Quy chế tuyển sinh",
    text_version: 0,
    text_version_id: null,
    text_canonical_sha256: null,
    provider_id: null,
    max_output_tokens: null,
    ocr_run_id: null,
    compilation_run_id: null,
    error_code: null,
    created_at: "2026-11-08T08:00:00Z",
    updated_at: "2026-11-08T08:00:00Z",
    started_at: null,
    finished_at: null,
    policy: null,
    reused: false,
    ...overrides,
  };
}

const props = {
  workspaceId: "ws-1",
  collectionId: "col-1",
  sourceId: "src-1",
  sourceTitle: "Quy chế tuyển sinh",
  revisionId: "rev-1",
  revisionNo: 2,
  revisionSha256: "a".repeat(64),
  savedRunId: "ocr-1",
  savedTextVersion: 3,
  isOpen: true,
  onClose: vi.fn(),
};

beforeEach(() => {
  state.intents = [];
  state.detail = null;
  state.create.mockReset();
  state.cancel.mockReset();
  state.create.mockImplementation(async () => {
    const created = intent();
    state.intents = [created];
    state.detail = created;
    return { intent: created, created: true, dispatched: true };
  });
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
  vi.unstubAllGlobals();
});

function renderDialog() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <PreparationDialog {...props} />
    </QueryClientProvider>,
  );
}

test("the normal screen submits one automatic request without technical choices", async () => {
  renderDialog();

  expect(screen.queryByRole("radio")).toBeNull();
  expect(screen.queryByText("Model (chat)")).toBeNull();
  expect(screen.queryByText(/GIới hạn output tokens/i)).toBeNull();
  expect(screen.queryByText("Bổ sung bằng AI")).toBeNull();
  expect(screen.getByText(/Hệ thống tự chọn cách phù hợp/)).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "Chuẩn bị nội dung" }));

  await waitFor(() => expect(state.create).toHaveBeenCalledTimes(1));
  expect(state.create.mock.calls[0][0]).toEqual({
    input: {
      mode: "auto",
      revision_id: "rev-1",
      ocr_run_id: "ocr-1",
      text_version: 3,
    },
    idempotencyKey: expect.any(String),
  });
  await waitFor(() => expect(screen.getByText("Đã ghi nhận")).toBeTruthy());
});

test("a ready result shows the pinned policy, reuse and the draft link", () => {
  const ready = intent({
    status: "ready",
    compilation_run_id: "cmp-1",
    reused: true,
    policy: {
      version: "qnu.preparation.auto/v1",
      supplement: "selective",
      reason: null,
    },
  });
  state.intents = [ready];
  state.detail = ready;

  renderDialog();

  expect(screen.getByText("Bản nháp đã sẵn sàng")).toBeTruthy();
  expect(
    screen.getByText(
      "Có bổ sung bằng AI, tách khỏi bản nguồn và kèm dẫn chứng.",
    ),
  ).toBeTruthy();
  expect(
    screen.getByText("Dùng lại bản nháp đã có cho đúng nguồn và chính sách"),
  ).toBeTruthy();
  expect(
    screen.getByRole("link", { name: /Mở bản nháp/ }).getAttribute("href"),
  ).toContain("/ws-1/collections/col-1/compilations/cmp-1");
  expect(screen.queryByRole("button", { name: "Dừng" })).toBeNull();
});

test("a policy downgrade is explained and stop is available while active", async () => {
  const queued = intent({
    status: "compiling",
    compilation_run_id: "cmp-1",
    policy: {
      version: "qnu.preparation.auto/v1",
      supplement: "disabled",
      reason: "chat_credentials_missing",
    },
  });
  state.intents = [queued];
  state.detail = queued;
  state.cancel.mockResolvedValue({ ...queued, status: "cancelled" });

  renderDialog();

  expect(
    screen.getByText(
      "Chưa bổ sung AI vì chưa có khóa model chat được cấp cho đơn vị. Bản nguồn vẫn được giữ đầy đủ.",
    ),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Dừng" }));
  await waitFor(() => expect(state.cancel).toHaveBeenCalledWith("prep-1"));
});

test("a stop that loses the race shows the finished intent, not older history", async () => {
  const cancelledOld = intent({
    id: "prep-old",
    status: "cancelled",
    error_code: "preparation_cancelled",
  });
  const active = intent({ id: "prep-new", status: "compiling" });
  const finished = intent({
    id: "prep-new",
    status: "ready",
    compilation_run_id: "cmp-new",
  });
  state.intents = [cancelledOld];
  state.detail = cancelledOld;
  state.create.mockImplementation(async () => {
    state.detail = active;
    return { intent: active, created: true, dispatched: true };
  });
  state.cancel.mockImplementation(async () => {
    state.detail = finished;
    return finished;
  });

  renderDialog();
  fireEvent.click(screen.getByRole("button", { name: "Chuẩn bị lại" }));
  fireEvent.click(screen.getByRole("button", { name: "Chuẩn bị nội dung" }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Dừng" })).toBeTruthy(),
  );
  fireEvent.click(screen.getByRole("button", { name: "Dừng" }));

  await waitFor(() =>
    expect(screen.getByText("Bản nháp đã sẵn sàng")).toBeTruthy(),
  );
  expect(screen.queryByText("Đã hủy")).toBeNull();
  expect(screen.queryByRole("button", { name: "Chuẩn bị lại" })).toBeNull();
  expect(
    screen.getByRole("link", { name: /Mở bản nháp/ }).getAttribute("href"),
  ).toContain("/compilations/cmp-new");
});

function stepIcons() {
  const list = screen.getByRole("list", { name: "Các bước chuẩn bị" });
  return within(list)
    .getAllByRole("listitem")
    .map((item) => item.querySelector("svg")?.getAttribute("class") ?? "");
}

test("a cancelled request does not claim the draft step was produced", () => {
  const cancelled = intent({
    status: "cancelled",
    error_code: "preparation_cancelled",
  });
  state.intents = [cancelled];
  state.detail = cancelled;

  renderDialog();

  const icons = stepIcons();
  expect(icons[0]).toContain("text-success");
  expect(icons[1]).toContain("text-muted-foreground");
  expect(icons[2]).toContain("text-muted-foreground");
});

test("a failure after the source was read marks the draft step, not all steps done", () => {
  const failed = intent({
    status: "failed",
    compilation_run_id: "cmp-1",
    error_code: "preparation_compilation_failed",
  });
  state.intents = [failed];
  state.detail = failed;

  renderDialog();

  const icons = stepIcons();
  expect(icons[0]).toContain("text-success");
  expect(icons[1]).toContain("text-success");
  expect(icons[2]).toContain("text-destructive");
});
