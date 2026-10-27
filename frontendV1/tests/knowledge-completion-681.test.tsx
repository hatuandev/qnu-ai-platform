// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  cleanup,
  fireEvent,
  render,
  renderHook,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { type ReactNode, useState } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { clearAccessToken, getTokenState, setAccessToken } from "@/app/api/v1";
import { EvaluationForm } from "@/features/evaluation/evaluation-form";
import { GoldPicker } from "@/features/evaluation/gold-picker";
import type { IndexManifest } from "@/features/evaluation/types";
import {
  useCompilationReviewsQuery,
  useCompilationRunsQuery,
} from "@/features/knowledge/compilation-queries";
import { CompilationRunsList } from "@/features/knowledge/compilation-runs-list";
import {
  DocumentScopePicker,
  type DocumentSelection,
} from "@/features/knowledge/document-scope-picker";
import { IndexPanel } from "@/features/knowledge/index-panel";
import { useIndexRunsQuery } from "@/features/knowledge/index-queries";
import type { IndexRun, SearchHit } from "@/features/knowledge/index-types";
import {
  ListPagination,
  readArrayPage,
} from "@/features/knowledge/list-pagination";
import type {
  DetectionResponse,
  ReviewDocument,
} from "@/features/knowledge/ocr-types";
import {
  useCompiledDocumentHistoryQuery,
  useCompiledDocumentsQuery,
  useCompiledVersionsQuery,
} from "@/features/knowledge/publication-queries";
import {
  SpellingResultPanel,
  SpellingResultView,
} from "@/features/knowledge/spelling-result-panel";

vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({ sessionId: getTokenState().sessionId }),
}));
vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  Link: ({ children }: { children: ReactNode }) => (
    <a href="#synthetic">{children}</a>
  ),
}));
vi.mock("@/features/modelops/queries", () => ({
  useCatalogQuery: () => ({ data: [], isPending: false }),
}));
const hash = "a".repeat(64);
const doc: ReviewDocument = {
  run_id: "ocr",
  version: 2,
  version_id: "v2",
  canonical_sha256: hash,
  original_sha256: hash,
  markdown_sha256: hash,
  saved_at: null,
  units: [
    {
      evidence_id: "block",
      page: 1,
      kind: "paragraph",
      text: "Văn bãn thử",
      original_text: "Văn bãn thử",
      bbox: {},
      row: null,
      column: null,
    },
  ],
};
const check: DetectionResponse = {
  id: "check",
  status: "completed",
  version: 2,
  canonical_sha256: hash,
  suggestions: [
    {
      evidence_id: "block",
      start: 4,
      end: 7,
      original: "bãn",
      replacement: "bản",
      reason: "Từ chưa phù hợp",
    },
  ],
  checked_evidence_ids: ["block"],
  error_code: null,
  usage_id: null,
  created_at: "2026-10-27T00:00:00Z",
};
const hit: SearchHit = {
  chunk_id: "chunk",
  document_id: "d0",
  version_id: "v",
  publication_decision_id: "p",
  score: 0.5,
  kind: "paragraph",
  text: "Nội dung tổng hợp",
  citations: {},
  structure: null,
};
const manifest: IndexManifest = {
  run_id: "run",
  generation: 1,
  chunks: [{ id: "chunk", text_sha256: hash }],
  inputs: [
    { document_id: "d0", version_id: "v", publication_decision_id: "p" },
  ],
};
const run: IndexRun = {
  id: "run",
  workspace_id: "w",
  collection_id: "c",
  generation: 1,
  status: "completed",
  is_active: true,
  provider_id: "e",
  dimension: 3,
  input_sha256: hash,
  manifest_sha256: hash,
  chunks_total: 1,
  attempt_count: 1,
  requested_at: "2026-10-27T00:00:00Z",
  dispatched_at: null,
  started_at: null,
  finished_at: null,
  error_code: null,
};
const respond = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
let calls: { method: string; url: URL; body: Record<string, unknown> }[];
let status: number;
let saved: DetectionResponse;
let outside: boolean;
let delayedSearch: Promise<Response> | undefined;
const clients: QueryClient[] = [];
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
function show(children: ReactNode) {
  return render(children, { wrapper: Wrapper });
}
beforeEach(() => {
  setAccessToken("synthetic-681");
  calls = [];
  status = 200;
  saved = check;
  outside = false;
  delayedSearch = undefined;
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
      const url = new URL(input, "http://synthetic.invalid");
      const method = init?.method ?? "GET";
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      calls.push({ url, method, body });
      if (status !== 200)
        return respond(
          {
            title: "Không được truy cập",
            detail: "Không mở được dữ liệu",
            status,
          },
          status,
        );
      if (url.pathname.endsWith("/search"))
        return (
          delayedSearch ??
          respond({
            index_run_id: "run",
            generation: 1,
            status: "results",
            eligible_documents: 1,
            skipped_documents: [],
            trace: { manifest_sha256: hash },
            hits: [{ ...hit, document_id: outside ? "outside" : "d0" }],
          })
        );
      if (url.pathname.endsWith("/retrieval-evaluations"))
        return respond({
          schema_version: "1",
          id: "evaluation",
          index_run_id: "run",
          manifest_sha256: hash,
          label_version: "v1",
          label_author: "Synthetic",
          label_status: "draft_needs_human_check",
          top_k: 5,
          candidate_k: 30,
          records: [],
          summary: {},
          answer_evaluation: "NOT RUN",
          publication_approval: false,
          timing_boundary: "synthetic",
        });
      if (url.pathname.includes("/checks/")) return respond(saved);
      if (url.pathname.endsWith("/compiled-documents")) {
        const offset = Number(url.searchParams.get("offset"));
        const size = Number(url.searchParams.get("limit"));
        return respond(
          Array.from({ length: 25 }, (_, i) => ({
            id: `d${i}`,
            title: `Tài liệu ${i}`,
            document_key: `key-${i}`,
          })).slice(offset, offset + size),
        );
      }
      if (url.pathname.endsWith("/index-runs")) return respond([run]);
      return respond([]);
    }),
  );
});
afterEach(() => {
  cleanup();
  for (const c of clients.splice(0)) c.clear();
  clearAccessToken();
  vi.unstubAllGlobals();
});

test.each([20, 100])(
  "lookahead size %i reaches next page without exceeding server limit",
  async (size) => {
    const rows = Array.from({ length: 205 }, (_, i) => i);
    const fetch = vi.fn(async (limit: number, offset: number) =>
      rows.slice(offset, offset + limit),
    );
    const first = await readArrayPage(fetch, size, 0);
    const next = await readArrayPage(fetch, size, size);
    expect(first.slice(0, size)).toEqual(rows.slice(0, size));
    expect(next.slice(0, size)).toEqual(rows.slice(size, size * 2));
    expect(first).toHaveLength(size + 1);
    expect(fetch.mock.calls.every(([limit]) => limit <= 100)).toBe(true);
    expect(await readArrayPage(fetch, size, 205)).toEqual([]);
  },
);
test("pagination has no invented total, disables final Next, allows return from an empty deep page", () => {
  const change = vi.fn();
  show(
    <ListPagination
      page={4}
      pageSize={20}
      hasNext={false}
      onPageChange={change}
    />,
  );
  expect(screen.getByText("Trang 4")).toBeTruthy();
  expect(
    (screen.getByRole("button", { name: "Trang sau" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Trang trước" }));
  expect(change).toHaveBeenCalledWith(3);
  expect(screen.queryByText(/tổng số/i)).toBeNull();
});
test("a failed Compiler page still allows returning to the previous page", async () => {
  status = 404;
  const change = vi.fn();
  show(
    <CompilationRunsList
      workspaceId="w"
      collectionId="c"
      canManage
      onOpenCreateDialog={vi.fn()}
      page={3}
      onPageChange={change}
    />,
  );
  await screen.findByText("Không thể tải danh sách lượt biên soạn");
  fireEvent.click(screen.getByRole("button", { name: "Trang trước" }));
  expect(change).toHaveBeenCalledWith(2);
  expect(
    (screen.getByRole("button", { name: "Trang sau" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
});
test("all six list hooks send real page offsets, including Compiler beyond 100", async () => {
  renderHook(
    () => {
      useCompiledDocumentsQuery("w", "c", 20, 40, { lookahead: true });
      useCompiledVersionsQuery("w", "c", "d", 20, 40, { lookahead: true });
      useCompiledDocumentHistoryQuery("w", "c", "d", 20, 40, {
        lookahead: true,
      });
      useCompilationRunsQuery("w", "c", 20, { offset: 100, lookahead: true });
      useCompilationReviewsQuery("w", "c", "run", 20, 40, { lookahead: true });
      useIndexRunsQuery("w", "c", { page: 3, pageSize: 20 });
    },
    { wrapper: Wrapper },
  );
  await waitFor(() => expect(calls).toHaveLength(6));
  expect(calls.every((c) => c.url.searchParams.get("limit") === "21")).toBe(
    true,
  );
  expect(calls.map((c) => c.url.searchParams.get("offset")).sort()).toEqual([
    "100",
    "40",
    "40",
    "40",
    "40",
    "40",
  ]);
});
function Picker({
  allowedIds,
  initial = [],
}: {
  allowedIds?: string[];
  initial?: DocumentSelection[];
}) {
  const [selected, setSelected] = useState(initial);
  return (
    <DocumentScopePicker
      workspaceId="w"
      collectionId="c"
      selected={selected}
      onChange={setSelected}
      allowedIds={allowedIds}
    />
  );
}
async function openPicker() {
  fireEvent.click(screen.getByRole("button", { name: "Chọn tài liệu" }));
  const dialog = await screen.findByRole("dialog");
  await waitFor(() =>
    expect(
      (within(dialog).getByRole("combobox") as HTMLButtonElement).disabled,
    ).toBe(false),
  );
  return dialog;
}
async function selectDoc(label = "Tài liệu 0 · key-0") {
  fireEvent.click(screen.getByRole("combobox"));
  fireEvent.click(await screen.findByRole("option", { name: label }));
}
test("document chooser loads subsequent server pages and retains choices across page changes", async () => {
  show(<Picker />);
  const dialog = await openPicker();
  await selectDoc();
  fireEvent.click(within(dialog).getByRole("button", { name: "Trang sau" }));
  await waitFor(() =>
    expect(calls.some((c) => c.url.searchParams.get("offset") === "20")).toBe(
      true,
    ),
  );
  await waitFor(() =>
    expect(
      (within(dialog).getByRole("combobox") as HTMLButtonElement).disabled,
    ).toBe(false),
  );
  await selectDoc("Tài liệu 20 · key-20");
  expect(
    within(dialog).getByText(
      "Đã chọn 2/100. Bỏ hết lựa chọn sẽ tìm trong toàn bộ tài liệu đủ điều kiện.",
    ),
  ).toBeTruthy();
  fireEvent.click(within(dialog).getByRole("button", { name: "Xong" }));
  expect(screen.getAllByRole("listitem")).toHaveLength(2);
});
test("evaluation picker offers only documents in its manifest and prevents duplicate choices", async () => {
  show(<Picker allowedIds={["d0"]} />);
  await openPicker();
  await selectDoc();
  fireEvent.click(screen.getByRole("combobox"));
  const option = await screen.findByRole("option", {
    name: "Tài liệu 0 · key-0",
  });
  expect(option.getAttribute("aria-disabled")).toBe("true");
  expect(
    screen.queryByRole("option", { name: "Tài liệu 1 · key-1" }),
  ).toBeNull();
});
test.each([403, 404])(
  "picker HTTP %i does not discard explicit selected scope",
  async (error) => {
    status = error;
    show(<Picker initial={[{ id: "d0", title: "Đã chọn" }]} />);
    fireEvent.click(screen.getByRole("button", { name: "Chọn tài liệu" }));
    await screen.findByText("Không mở được dữ liệu");
    expect(screen.getByText("Chỉ tìm trong 1 tài liệu đã chọn")).toBeTruthy();
  },
);
test("100-document limit prevents adding beyond the request contract", async () => {
  show(
    <Picker
      initial={Array.from({ length: 100 }, (_, i) => ({
        id: `selected-${i}`,
        title: `Đã chọn ${i}`,
      }))}
    />,
  );
  await openPicker();
  fireEvent.click(screen.getByRole("combobox"));
  expect(
    (
      await screen.findByRole("option", { name: "Tài liệu 0 · key-0" })
    ).getAttribute("aria-disabled"),
  ).toBe("true");
});
test("search sends exact document scope and rejects an in-flight result after the scope changes", async () => {
  let release!: (value: Response) => void;
  delayedSearch = new Promise((resolve) => {
    release = resolve;
  });
  show(<IndexPanel workspaceId="w" collectionId="c" canManage />);
  await openPicker();
  await selectDoc();
  fireEvent.click(screen.getByRole("button", { name: "Xong" }));
  fireEvent.change(
    screen.getByRole("textbox", { name: "Câu truy vấn tìm kiếm thử" }),
    { target: { value: "Câu hỏi" } },
  );
  fireEvent.click(screen.getByRole("button", { name: "Tìm thử" }));
  await waitFor(() =>
    expect(calls.find((c) => c.method === "POST")?.body.document_ids).toEqual([
      "d0",
    ]),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Bỏ tài liệu Tài liệu 0" }),
  );
  await act(async () =>
    release(
      respond({
        index_run_id: "run",
        generation: 1,
        status: "results",
        hits: [hit],
        trace: {},
        skipped_documents: [],
        eligible_documents: 1,
      }),
    ),
  );
  expect(screen.queryByText(hit.text)).toBeNull();
  expect(screen.getByText("Toàn bộ tài liệu đủ điều kiện")).toBeTruthy();
});
test("gold search uses exact document filter and rejects a hit from outside that filter", async () => {
  outside = true;
  const change = vi.fn();
  show(
    <GoldPicker
      workspaceId="w"
      collectionId="c"
      query="Câu hỏi"
      manifest={manifest}
      manifestSha={hash}
      selected={[]}
      onChange={change}
      disabled={false}
      documentIds={["d0"]}
    />,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Tìm đoạn làm đáp án chuẩn" }),
  );
  await screen.findByText(/Chỉ mục đã thay đổi hoặc kết quả khác snapshot/);
  expect(calls[0].body.document_ids).toEqual(["d0"]);
  expect(change).not.toHaveBeenCalled();
  expect(screen.queryByRole("checkbox")).toBeNull();
});
test("evaluation sends the same document filter as gold search; changing scope clears previous gold", async () => {
  show(
    <EvaluationForm
      workspaceId="w"
      collectionId="c"
      run={run}
      manifest={manifest}
    />,
  );
  fireEvent.change(screen.getByLabelText("Phiên bản bộ nhãn"), {
    target: { value: "v1" },
  });
  fireEvent.change(screen.getByLabelText("Người gán nhãn"), {
    target: { value: "Synthetic" },
  });
  fireEvent.change(screen.getByLabelText("Nội dung câu hỏi"), {
    target: { value: "Câu hỏi" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Tìm đoạn làm đáp án chuẩn" }),
  );
  const candidates = await screen.findByRole("list", { name: "Đoạn gợi ý" });
  fireEvent.click(within(candidates).getByRole("checkbox"));
  expect(
    screen.getByRole("list", { name: "Đáp án chuẩn đã chọn" }),
  ).toBeTruthy();
  await openPicker();
  await selectDoc();
  fireEvent.click(screen.getByRole("button", { name: "Xong" }));
  expect(
    screen.queryByRole("list", { name: "Đáp án chuẩn đã chọn" }),
  ).toBeNull();
  fireEvent.click(
    screen.getByRole("button", { name: "Tìm đoạn làm đáp án chuẩn" }),
  );
  await screen.findByRole("list", { name: "Đoạn gợi ý" });
  fireEvent.click(
    screen.getByRole("button", { name: "Chạy đánh giá truy xuất" }),
  );
  await waitFor(() =>
    expect(
      calls.some((c) => c.url.pathname.endsWith("/retrieval-evaluations")),
    ).toBe(true),
  );
  const searches = calls.filter((c) => c.url.pathname.endsWith("/search"));
  expect(searches.at(-1)?.body.document_ids).toEqual(["d0"]);
  const evaluation = calls.find((c) =>
    c.url.pathname.endsWith("/retrieval-evaluations"),
  );
  expect(evaluation?.body.queries).toEqual([
    expect.objectContaining({ document_ids: ["d0"], gold_chunk_ids: [] }),
  ]);
});
const spellingProps = {
  workspaceId: "w",
  collectionId: "c",
  sourceId: "s",
  revisionId: "r",
  runId: "ocr",
  checkId: "check",
  localCheck: null,
  doc,
  draftChanges: new Map<string, string>(),
  canManage: true,
};
test("reopening a saved check after remount uses its scoped GET, without rerunning the model", async () => {
  const view = show(
    <SpellingResultPanel {...spellingProps} onApply={vi.fn()} />,
  );
  await screen.findByText("Văn bãn thử");
  view.unmount();
  show(<SpellingResultPanel {...spellingProps} onApply={vi.fn()} />);
  await screen.findByText("Văn bãn thử");
  expect(calls.every((c) => c.method === "GET")).toBe(true);
  expect(calls[0].url.pathname).toMatch(
    /workspaces\/w\/collections\/c\/sources\/s\/revisions\/r\/processing-runs\/ocr\/text-review\/checks\/check$/,
  );
});
test.each([403, 404])(
  "saved check HTTP %i is an error, never treated as completed or auto-rerun",
  async (error) => {
    status = error;
    show(<SpellingResultPanel {...spellingProps} onApply={vi.fn()} />);
    await screen.findByText("Không mở được dữ liệu");
    expect(screen.queryByText("Hoàn tất")).toBeNull();
    expect(calls.every((c) => c.method === "GET")).toBe(true);
  },
);
test.each(["running", "uncertain", "failed"])(
  "check status %s never exposes correction actions",
  (state) => {
    show(
      <SpellingResultView
        check={{ ...check, status: state }}
        doc={doc}
        draftChanges={new Map()}
        canManage
        onApply={vi.fn()}
      />,
    );
    expect(
      screen.queryByRole("button", { name: "Áp dụng vào nháp" }),
    ).toBeNull();
    expect(screen.getByText(/không tự gọi model lại/)).toBeTruthy();
  },
);
test.each(["version", "hash"])(
  "a %s mismatch blocks saved suggestions",
  (mismatch) => {
    show(
      <SpellingResultView
        check={{
          ...check,
          ...(mismatch === "version"
            ? { version: 1 }
            : { canonical_sha256: "b".repeat(64) }),
        }}
        doc={doc}
        draftChanges={new Map()}
        canManage
        onApply={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert").textContent).toMatch(
      /phiên bản hoặc hash khác/,
    );
    expect(
      screen.queryByRole("button", { name: "Áp dụng vào nháp" }),
    ).toBeNull();
  },
);
test.each(["reader", "stale-span"])(
  "%s cannot apply a saved correction",
  (reason) => {
    const apply = vi.fn();
    show(
      <SpellingResultView
        check={check}
        doc={doc}
        draftChanges={
          reason === "stale-span"
            ? new Map([["block", "Văn bản đã sửa"]])
            : new Map()
        }
        canManage={reason !== "reader"}
        onApply={apply}
      />,
    );
    const button = screen.getByRole("button", { name: "Áp dụng vào nháp" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(button);
    expect(apply).not.toHaveBeenCalled();
  },
);
test("a valid saved suggestion is dismissed only after the parent accepts it into draft", () => {
  const apply = vi.fn().mockReturnValueOnce(false).mockReturnValueOnce(true);
  show(
    <SpellingResultView
      check={check}
      doc={doc}
      draftChanges={new Map()}
      canManage
      onApply={apply}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Áp dụng vào nháp" }));
  expect(screen.getByText("Văn bãn thử")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Áp dụng vào nháp" }));
  expect(screen.queryByText("Văn bãn thử")).toBeNull();
  expect(apply).toHaveBeenCalledTimes(2);
  expect(calls).toEqual([]);
});
