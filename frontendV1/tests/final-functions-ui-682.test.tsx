// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { type ReactNode, useState } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { clearAccessToken, getTokenState, setAccessToken } from "@/app/api/v1";
import type { CallerWorkspaceRole } from "@/app/auth/v1/permissions";
import type { AnswerResponse } from "@/features/conversations/types";
import {
  buildAnswerRequest,
  DEFAULT_ANSWER_SETTINGS,
} from "@/features/knowledge/answer-request";
import { AnswerResult } from "@/features/knowledge/answer-result";
import { AnswersPage } from "@/features/knowledge/answers-page";
import { ReviewDownloads } from "@/features/knowledge/review-downloads";
import { EMPTY_METADATA_FILTER_DRAFT } from "@/features/rag/metadata-filter-fields";
import { QnuDashboardPage } from "@/features/workspaces/qnu-dashboard-page";

const env = vi.hoisted(() => ({
  role: { kind: "platform-admin" } as CallerWorkspaceRole,
  downloads: [] as { blob: Blob; name: string }[],
}));
vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({
    sessionId: getTokenState().sessionId,
    actor: {
      authenticated: true,
      actor_id: "synthetic-682",
      permissions: ["ai.workspaces.manage"],
    },
  }),
}));
vi.mock("@/navigation/use-feature-scope", () => ({
  useFeatureScope: () => ({}),
}));
vi.mock("@/features/workspaces/queries", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/workspaces/queries")>()),
  useCallerWorkspaceRole: () => ({
    role: env.role,
    isPending: false,
    error: null,
  }),
}));
vi.mock("@tanstack/react-router", () => ({
  useRouterState: ({
    select,
  }: {
    select?: (state: {
      location: { pathname: string; search: Record<string, unknown> };
    }) => unknown;
  } = {}) => {
    const state = { location: { pathname: "/dashboard", search: {} } };
    return select ? select(state) : state;
  },
  Link: ({
    children,
    to,
    search,
  }: {
    children: ReactNode;
    to: string;
    search?: unknown;
  }) => (
    <a href="#fixture" data-route={to} data-search={JSON.stringify(search)}>
      {children}
    </a>
  ),
}));
vi.mock("@/lib/download-blob", () => ({
  downloadBlob: (blob: Blob, name: string) =>
    env.downloads.push({ blob, name }),
}));
const rawText = `${JSON.stringify({ raw: "  Văn bản nguyên trạng  " }, null, 2)}\n`;
const source = {
  evidence_id: "E1",
  chunk_id: "chunk",
  document_id: "doc",
  version_id: "v",
  publication_decision_id: "p",
  score: 0.5,
  kind: "paragraph",
  text: "Bằng chứng tổng hợp, không phải dữ liệu thực.",
  citations: {
    block: {
      filename: "synthetic.pdf",
      source_id: "source",
      revision_id: "revision",
      page_number: 2,
    },
  },
  structure: null,
};
const answer: AnswerResponse = {
  id: "answer",
  status: "answered",
  answer: "Câu trả lời tổng hợp",
  statements: [{ text: "Câu trả lời tổng hợp", evidence_ids: ["E1"] }],
  sources: [source],
  index_run_id: "idx",
  generation: 2,
  trace: {
    model_name: "synthetic-chat",
    total_tokens: null,
    verification: { mode: "off", status: "not_run" },
  },
};
const collection = {
  id: "c",
  workspace_id: "w",
  name: "Kho tổng hợp",
  description: null,
  source_count: 2,
  created_by: "synthetic",
  created_at: "2026-10-27T00:00:00Z",
  updated_at: "2026-10-27T00:00:00Z",
};
const workspace = {
  id: "w",
  code: "synthetic",
  name: "Workspace tổng hợp",
  description: "Kiểm tra giao diện",
  status: "active",
  member_count: 7,
  created_at: "2026-10-27T00:00:00Z",
  updated_at: "2026-10-27T00:00:00Z",
};
type Call = {
  url: URL;
  method: string;
  body: Record<string, unknown>;
  headers: Headers;
};
let calls: Call[];
let answerStatus: number;
let rawStatus: number;
let summaryStatus: number;
let workspaceStatus: number;
let empty: boolean;
let suspended: boolean;
let withdrawn: boolean;
let result: AnswerResponse;
let delayed: Promise<Response> | undefined;
let delayPath: string;
let catalogStatus: number;
const clients: QueryClient[] = [];
const response = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
function Wrapper({ children }: { children: ReactNode }) {
  const [client] = useState(() => {
    const c = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    clients.push(c);
    return c;
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
const show = (children: ReactNode) => render(children, { wrapper: Wrapper });
beforeEach(() => {
  setAccessToken("synthetic-682");
  env.role = { kind: "platform-admin" };
  env.downloads = [];
  calls = [];
  answerStatus =
    rawStatus =
    summaryStatus =
    workspaceStatus =
    catalogStatus =
      200;
  empty = suspended = withdrawn = false;
  result = answer;
  delayed = undefined;
  delayPath = "";
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  );
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  Element.prototype.scrollIntoView = vi.fn();
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.setPointerCapture = vi.fn();
  Element.prototype.releasePointerCapture = vi.fn();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init?: RequestInit) => {
      const url = new URL(input, "http://fixture.invalid");
      const method = init?.method ?? "GET";
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      calls.push({ url, method, body, headers: new Headers(init?.headers) });
      const path = url.pathname;
      if (delayPath && path.endsWith(delayPath) && delayed) return delayed;
      const fail = (status: number) =>
        response(
          {
            status,
            title: "Yêu cầu không hoàn tất",
            detail: "Lỗi tổng hợp để kiểm tra",
            code: "synthetic_failure",
          },
          status,
        );
      if (path.endsWith("/answers"))
        return answerStatus === 200 ? response(result) : fail(answerStatus);
      if (path.endsWith("/raw") || path.endsWith("/markdown"))
        return rawStatus === 200
          ? new Response(rawText, {
              headers: {
                "Content-Type": "application/json",
                "Content-Disposition":
                  "attachment; filename=review-original.json",
              },
            })
          : fail(rawStatus);
      if (path.endsWith("/modelops/catalog"))
        return catalogStatus === 200
          ? response([
              {
                id: "chat",
                name: "Chat cho workspace",
                model_name: "synthetic-chat",
                capabilities: ["chat"],
                default_capabilities: ["chat"],
              },
              {
                id: "rerank",
                name: "Rerank",
                model_name: "synthetic-rerank",
                capabilities: ["rerank"],
                default_capabilities: [],
              },
            ])
          : fail(catalogStatus);
      if (path.endsWith("/published"))
        return response({
          document: { id: "doc" },
          version: { id: withdrawn ? "other-version" : "v" },
          decision: { id: "p" },
          content: {},
        });
      if (path.endsWith("/compiled-documents"))
        return response([
          { id: "doc", title: "Tài liệu tổng hợp", document_key: "synthetic" },
        ]);
      if (path.endsWith("/operations/summary"))
        return summaryStatus === 200
          ? response({
              jobs: empty
                ? []
                : [
                    { kind: "ocr", status: "queued", count: 2 },
                    { kind: "compiler", status: "running", count: 3 },
                    { kind: "review", status: "failed", count: 4 },
                    { kind: "spelling", status: "uncertain", count: 1 },
                    { kind: "index", status: "completed", count: 9 },
                  ],
              usage: empty
                ? []
                : [
                    {
                      status: "completed",
                      records: 2,
                      observed_tokens: null,
                      reserved_tokens: 500,
                      observed_cost_usd: null,
                      cost_records: 0,
                    },
                  ],
            })
          : fail(summaryStatus);
      if (path.endsWith("/operations/readiness"))
        return response({
          scope: "workspace",
          ready: false,
          checks: { worker: { ok: false } },
          live_inference_verified: false,
          production_auth_configured: false,
          reconcile_enabled: false,
        });
      if (path.endsWith("/workspaces")) {
        const start = (Number(url.searchParams.get("page")) - 1) * 20;
        return response({
          items: empty
            ? []
            : Array.from({ length: 29 }, (_, i) => ({
                ...workspace,
                id: i ? `w${i}` : "w",
                name: `Workspace ${i}`,
              })).slice(start, start + 20),
          meta: {
            page: Number(url.searchParams.get("page")),
            page_size: 20,
            total: empty ? 0 : 29,
          },
        });
      }
      if (/\/workspaces\/[^/]+$/.test(path))
        return workspaceStatus === 200
          ? response({
              ...workspace,
              id: path.split("/").at(-1),
              name: path.endsWith("/other") ? "Workspace khác" : workspace.name,
              status: suspended ? "suspended" : "active",
            })
          : fail(workspaceStatus);
      if (path.endsWith("/collections"))
        return response({
          items: empty
            ? []
            : [collection, { ...collection, id: "c2", name: "Kho khác" }],
          meta: { page: 1, page_size: 6, total: empty ? 0 : 17 },
        });
      if (/\/collections\/[^/]+$/.test(path)) return response(collection);
      throw new Error(`Unexpected fixture endpoint ${path}`);
    }),
  );
});
afterEach(() => {
  cleanup();
  for (const c of clients.splice(0)) c.clear();
  clearAccessToken();
  vi.unstubAllGlobals();
});
function readBlob(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
}
const props = { workspaceId: "w", collectionId: "c" };
async function sendQuestion() {
  const button = await screen.findByRole("button", { name: "Gửi câu hỏi" });
  await waitFor(() =>
    expect((button as HTMLButtonElement).disabled).toBe(false),
  );
  fireEvent.change(screen.getByLabelText("Câu hỏi"), {
    target: { value: "Nội dung nào áp dụng?" },
  });
  fireEvent.click(button);
}

test("direct answers calls the exact collection endpoint with default policy, no fake conversation or retry key", async () => {
  show(<AnswersPage {...props} />);
  await sendQuestion();
  await screen.findByText("Câu trả lời tổng hợp");
  const post = calls.find((c) => c.method === "POST");
  expect(post?.url.pathname).toMatch(/workspaces\/w\/collections\/c\/answers$/);
  expect(post?.body).toEqual(
    expect.objectContaining({
      question: "Nội dung nào áp dụng?",
      retrieval_mode: "dense",
      provider_id: null,
      verification_mode: "off",
      context_window: 0,
      document_ids: null,
      metadata_filter: {},
    }),
  );
  expect(post?.headers.has("Idempotency-Key")).toBe(false);
  expect(calls.filter((c) => c.method === "POST")).toHaveLength(1);
});
test("the document picker scope and exact year are submitted to answers", async () => {
  show(<AnswersPage {...props} />);
  await screen.findByLabelText("Câu hỏi");
  fireEvent.click(screen.getByRole("button", { name: "Chọn tài liệu" }));
  const dialog = await screen.findByRole("dialog");
  await waitFor(() =>
    expect(
      (within(dialog).getByRole("combobox") as HTMLButtonElement).disabled,
    ).toBe(false),
  );
  fireEvent.click(within(dialog).getByRole("combobox"));
  fireEvent.click(
    await screen.findByRole("option", {
      name: "Tài liệu tổng hợp · synthetic",
    }),
  );
  fireEvent.click(within(dialog).getByRole("button", { name: "Xong" }));
  fireEvent.click(screen.getByText("Phạm vi năm, ngành và hiệu lực"));
  fireEvent.change(screen.getByLabelText("Năm dữ liệu"), {
    target: { value: "2024" },
  });
  await sendQuestion();
  await screen.findByText("Câu trả lời tổng hợp");
  expect(calls.find((c) => c.method === "POST")?.body).toEqual(
    expect.objectContaining({
      document_ids: ["doc"],
      metadata_filter: { data_year: 2024 },
    }),
  );
});
test("invalid explicit year blocks answering instead of silently broadening the scope", async () => {
  show(<AnswersPage {...props} />);
  await screen.findByLabelText("Câu hỏi");
  fireEvent.click(screen.getByText("Phạm vi năm, ngành và hiệu lực"));
  fireEvent.change(screen.getByLabelText("Năm dữ liệu"), {
    target: { value: "202" },
  });
  await sendQuestion();
  await screen.findByRole("alert");
  expect(calls.filter((c) => c.method === "POST")).toHaveLength(0);
});
test("explicit ModelOps provider and hybrid settings are preserved", async () => {
  show(<AnswersPage {...props} />);
  await screen.findByLabelText("Câu hỏi");
  const model = screen.getByRole("region", { name: "Model trả lời" });
  await waitFor(() =>
    expect(
      (within(model).getByRole("combobox") as HTMLButtonElement).disabled,
    ).toBe(false),
  );
  fireEvent.click(within(model).getByRole("combobox"));
  fireEvent.click(
    await screen.findByRole("option", {
      name: "Chat cho workspace · synthetic-chat",
    }),
  );
  fireEvent.click(screen.getByText("Cấu hình RAG"));
  fireEvent.click(screen.getByRole("combobox", { name: "Cách truy xuất" }));
  fireEvent.click(
    await screen.findByRole("option", { name: "Hybrid (dense + từ khóa)" }),
  );
  fireEvent.change(screen.getByLabelText("Đoạn lân cận mỗi phía"), {
    target: { value: "1" },
  });
  await sendQuestion();
  await screen.findByText("Câu trả lời tổng hợp");
  expect(calls.find((c) => c.method === "POST")?.body).toEqual(
    expect.objectContaining({
      provider_id: "chat",
      retrieval_mode: "hybrid",
      candidate_k: 30,
      context_window: 1,
    }),
  );
});
test.each([403, 409, 503])(
  "answers HTTP %i remains an error with zero automatic retry",
  async (code) => {
    answerStatus = code;
    show(<AnswersPage {...props} />);
    await sendQuestion();
    await screen.findByText("Lỗi tổng hợp để kiểm tra");
    expect(screen.queryByText("Câu trả lời tổng hợp")).toBeNull();
    expect(calls.filter((c) => c.method === "POST")).toHaveLength(1);
    expect(screen.getByText(/Không tự gửi lại yêu cầu/)).toBeTruthy();
  },
);
test("double submit sends one request and a late answer cannot land under another collection", async () => {
  let release!: (r: Response) => void;
  delayed = new Promise((resolve) => {
    release = resolve;
  });
  delayPath = "/answers";
  const view = show(<AnswersPage {...props} />);
  await sendQuestion();
  const questionForm = screen.getByLabelText("Câu hỏi").closest("form");
  if (!questionForm) throw new Error("Missing question form in fixture");
  fireEvent.submit(questionForm);
  await waitFor(() =>
    expect(calls.filter((c) => c.method === "POST")).toHaveLength(1),
  );
  view.rerender(<AnswersPage workspaceId="w" collectionId="other" />);
  await act(async () => release(response(answer)));
  expect(screen.queryByText("Câu trả lời tổng hợp")).toBeNull();
});
test("logout and new session discard a late answer", async () => {
  let release!: (r: Response) => void;
  delayed = new Promise((resolve) => {
    release = resolve;
  });
  delayPath = "/answers";
  const view = show(<AnswersPage {...props} />);
  await sendQuestion();
  setAccessToken("synthetic-new-session");
  view.rerender(<AnswersPage {...props} />);
  await act(async () => release(response(answer)));
  expect(screen.queryByText("Câu trả lời tổng hợp")).toBeNull();
});
test("opening a citation verifies publication and retains full evidence text", async () => {
  show(<AnswersPage {...props} />);
  await sendQuestion();
  await screen.findByText("Câu trả lời tổng hợp");
  fireEvent.click(screen.getByRole("button", { name: "Nguồn E1" }));
  await screen.findByText(source.text);
  expect(
    calls.some((c) =>
      c.url.pathname.endsWith("/compiled-documents/doc/published"),
    ),
  ).toBe(true);
  expect(screen.getByRole("link", { name: "Mở phiên bản nguồn" })).toBeTruthy();
});
test("withdrawn source is blocked in the citation inspector", async () => {
  withdrawn = true;
  show(<AnswersPage {...props} />);
  await sendQuestion();
  await screen.findByText("Câu trả lời tổng hợp");
  fireEvent.click(screen.getByRole("button", { name: "Nguồn E1" }));
  await screen.findByText(/Nguồn đã thay đổi hoặc bị thu hồi/);
  expect(screen.queryByText(source.text)).toBeNull();
});
test("insufficient evidence shows the server reason without claiming infrastructure failed", () => {
  const request = buildAnswerRequest(
    "Câu hỏi",
    DEFAULT_ANSWER_SETTINGS,
    [],
    EMPTY_METADATA_FILTER_DRAFT,
  );
  show(
    <AnswerResult
      {...props}
      request={request}
      result={{
        ...answer,
        status: "insufficient_evidence",
        reason: "answer_not_supported",
        statements: [],
        answer: null,
        trace: { verification: { mode: "enforce", status: "unsupported" } },
      }}
    />,
  );
  expect(screen.getByRole("status").textContent).toMatch(/nguồn|hỗ trợ/);
  expect(screen.queryByText("Câu trả lời tổng hợp")).toBeNull();
});
test("inconsistent evidence and raw HTML are not promoted to trusted answer markup", () => {
  const request = buildAnswerRequest(
    "Câu hỏi",
    DEFAULT_ANSWER_SETTINGS,
    [],
    EMPTY_METADATA_FILTER_DRAFT,
  );
  show(
    <AnswerResult
      {...props}
      request={request}
      result={{
        ...answer,
        statements: [
          { text: '<img src=x onerror="alert(1)">', evidence_ids: ["foreign"] },
        ],
      }}
    />,
  );
  expect(screen.getByRole("alert").textContent).toMatch(
    /không có dẫn nguồn nhất quán/,
  );
  expect(document.querySelector("img")).toBeNull();
});
test.each(["none", "unknown"])(
  "unconfirmed role %s does not start catalog or answer requests",
  async (kind) => {
    env.role = { kind } as CallerWorkspaceRole;
    show(<AnswersPage {...props} />);
    await screen.findByText(/Chưa xác nhận được quyền hỏi đáp/);
    expect(
      calls.some((c) => c.url.pathname.endsWith("/modelops/catalog")),
    ).toBe(false);
    expect(calls.filter((c) => c.method === "POST")).toHaveLength(0);
  },
);

const rawProps = {
  ...props,
  runId: "run",
  reviewId: "review",
  status: "failed" as const,
};
test("failed review raw output downloads exact bytes even when no completed report exists", async () => {
  show(<ReviewDownloads {...rawProps} />);
  fireEvent.click(screen.getByRole("button", { name: "Tải bản gốc" }));
  await waitFor(() => expect(env.downloads).toHaveLength(1));
  expect(calls[0].url.pathname).toMatch(
    /compilation-runs\/run\/reviews\/review\/raw$/,
  );
  expect(env.downloads[0].name).toBe("review-original.json");
  expect(await readBlob(env.downloads[0].blob)).toBe(rawText);
  expect(
    (
      screen.getByRole("button", {
        name: "Tải Markdown báo cáo",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
});
test.each([403, 404])(
  "raw review HTTP %i never saves a fake error file",
  async (code) => {
    rawStatus = code;
    show(<ReviewDownloads {...rawProps} />);
    fireEvent.click(screen.getByRole("button", { name: "Tải bản gốc" }));
    await screen.findByText("Lỗi tổng hợp để kiểm tra");
    expect(env.downloads).toHaveLength(0);
    expect(calls).toHaveLength(1);
  },
);
test("completed review Markdown uses the same pinned review endpoint", async () => {
  show(<ReviewDownloads {...rawProps} status="completed" />);
  fireEvent.click(screen.getByRole("button", { name: "Tải Markdown báo cáo" }));
  await waitFor(() => expect(env.downloads).toHaveLength(1));
  expect(calls[0].url.pathname).toMatch(/reviews\/review\/markdown$/);
});
test.each(["queued", "running"] as const)(
  "review %s cannot be downloaded as a completed report",
  (status) => {
    show(<ReviewDownloads {...rawProps} status={status} />);
    expect(
      (screen.getByRole("button", { name: "Tải bản gốc" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    expect(
      (
        screen.getByRole("button", {
          name: "Tải Markdown báo cáo",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    expect(calls).toHaveLength(0);
  },
);
test("late raw download does not save under a different review selection", async () => {
  let release!: (r: Response) => void;
  delayed = new Promise((resolve) => {
    release = resolve;
  });
  delayPath = "/raw";
  const view = show(<ReviewDownloads {...rawProps} />);
  fireEvent.click(screen.getByRole("button", { name: "Tải bản gốc" }));
  fireEvent.click(screen.getByRole("button", { name: "Tải bản gốc" }));
  await waitFor(() => expect(calls).toHaveLength(1));
  view.rerender(<ReviewDownloads {...rawProps} reviewId="another" />);
  await act(async () => release(new Response("old raw")));
  expect(env.downloads).toHaveLength(0);
});

test("dashboard uses real scoped totals and preserves unknown costs instead of KTX or invented trends", async () => {
  show(<QnuDashboardPage workspaceId="w" page={1} onSearch={vi.fn()} />);
  await screen.findByText("Workspace tổng hợp");
  await screen.findByRole("table", { name: "Usage model theo trạng thái" });
  expect(screen.getByText("17")).toBeTruthy();
  expect(screen.getAllByText("5")).toHaveLength(2);
  expect(screen.getByText("9")).toBeTruthy();
  expect(screen.getAllByText("Chưa có số đo")).toHaveLength(2);
  expect(screen.queryByText(/doanh thu|công nợ|tỷ lệ lấp đầy/i)).toBeNull();
  const jobLink = screen.getByRole("link", {
    name: "Rà soát ngữ nghĩa · Thất bại: 4",
  });
  expect(JSON.parse(jobLink.getAttribute("data-search") ?? "{}")).toEqual(
    expect.objectContaining({ page: 1, kind: "review", status: "failed" }),
  );
  expect(calls.every((c) => c.method === "GET")).toBe(true);
});
test("a member can view collections but never requests operational summary or readiness", async () => {
  env.role = { kind: "member", role: "member" };
  show(<QnuDashboardPage workspaceId="w" page={1} onSearch={vi.fn()} />);
  await screen.findByText("Kho tổng hợp");
  expect(screen.getByText(/Số liệu tác vụ và usage dành/)).toBeTruthy();
  expect(calls.some((c) => c.url.pathname.includes("/operations/"))).toBe(
    false,
  );
});
test("an editor gets operations summary without the admin-only readiness request", async () => {
  env.role = { kind: "member", role: "editor" };
  show(<QnuDashboardPage workspaceId="w" page={1} onSearch={vi.fn()} />);
  await screen.findByRole("table", { name: "Usage model theo trạng thái" });
  expect(calls.some((c) => c.url.pathname.endsWith("/summary"))).toBe(true);
  expect(calls.some((c) => c.url.pathname.endsWith("/readiness"))).toBe(false);
});
test("a summary outage shows an error instead of zero job counters", async () => {
  summaryStatus = 503;
  show(<QnuDashboardPage workspaceId="w" page={1} onSearch={vi.fn()} />);
  await screen.findByText("Lỗi tổng hợp để kiểm tra");
  expect(screen.queryByText("Đang chờ / chạy")).toBeNull();
  expect(screen.queryByText("Cần kiểm tra")).toBeNull();
});
test("dashboard resolves first available workspace when no workspaceId is specified", async () => {
  const change = vi.fn();
  show(<QnuDashboardPage page={1} onSearch={change} />);
  await screen.findByText("Workspace tổng hợp");
  await screen.findByRole("table", { name: "Usage model theo trạng thái" });
  expect(calls.some((c) => c.url.pathname.endsWith("/workspaces"))).toBe(true);
});
test.each([403, 404])(
  "an explicit inaccessible workspace %i is not replaced by the first allowed one",
  async (status) => {
    workspaceStatus = status;
    show(
      <QnuDashboardPage workspaceId="forbidden" page={1} onSearch={vi.fn()} />,
    );
    await screen.findByText("Lỗi tổng hợp để kiểm tra");
    expect(screen.queryByText("Workspace tổng hợp")).toBeNull();
    expect(calls.some((c) => c.url.pathname.includes("/operations/"))).toBe(
      false,
    );
  },
);
test("suspended workspace stays suspended without loading its collections or operations", async () => {
  suspended = true;
  show(<QnuDashboardPage workspaceId="w" page={1} onSearch={vi.fn()} />);
  await screen.findByText(/Workspace tạm dừng/);
  expect(
    calls.some(
      (c) =>
        c.url.pathname.endsWith("/collections") ||
        c.url.pathname.includes("/operations/"),
    ),
  ).toBe(false);
});
test("empty workspace list is an honest empty state with no synthetic counters", async () => {
  empty = true;
  show(<QnuDashboardPage page={1} onSearch={vi.fn()} />);
  await screen.findByText(/Chưa có (đơn vị|workspace) để hiển thị/);
  expect(screen.queryByText("Đang chờ / chạy")).toBeNull();
  expect(calls).toHaveLength(1);
});
test("switching workspace removes the previous workspace data and ignores a late summary", async () => {
  let release!: (r: Response) => void;
  delayed = new Promise((resolve) => {
    release = resolve;
  });
  delayPath = "/operations/summary";
  const view = show(
    <QnuDashboardPage workspaceId="w" page={1} onSearch={vi.fn()} />,
  );
  await screen.findByText("Workspace tổng hợp");
  view.rerender(
    <QnuDashboardPage workspaceId="other" page={1} onSearch={vi.fn()} />,
  );
  await screen.findByText("Workspace khác");
  await act(async () => release(response({ jobs: [], usage: [] })));
  expect(screen.queryByText("Workspace tổng hợp")).toBeNull();
  expect(
    calls.some((c) =>
      /workspaces\/other\/operations\/summary$/.test(c.url.pathname),
    ),
  ).toBe(true);
});
