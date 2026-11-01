// @vitest-environment jsdom
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { clearAccessToken, setAccessToken } from "@/app/api/v1";
import { IndexPanel } from "@/features/knowledge/index-panel";
import type { SearchResponse } from "@/features/knowledge/index-types";

const mocks = vi.hoisted(() => ({ search: vi.fn(), runs: [] as unknown[] }));
vi.mock("@/features/modelops/queries", () => ({
  useCatalogQuery: () => ({ data: [], isPending: false }),
}));
vi.mock("@/features/knowledge/index-queries", () => ({
  useIndexRunsQuery: () => ({
    data: mocks.runs,
    isPending: false,
    isError: false,
  }),
  useRequestIndexMutation: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useSearchMutation: () => ({ mutateAsync: mocks.search, isPending: false }),
}));
vi.mock("sonner", () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
}));

const oldResult: SearchResponse = {
  index_run_id: "index-a",
  generation: 1,
  status: "results",
  eligible_documents: 1,
  skipped_documents: [],
  trace: {},
  hits: [
    {
      chunk_id: "chunk-a",
      document_id: "doc-a",
      version_id: "v-a",
      publication_decision_id: "p-a",
      score: 0.9,
      kind: "paragraph",
      text: "Synthetic private content from collection A",
      citations: {},
      structure: null,
    },
  ],
};
beforeEach(() => {
  mocks.search.mockReset();
  mocks.runs = [];
});
afterEach(() => {
  cleanup();
  clearAccessToken();
});

test("invalid explicit year must block search instead of dropping scope", async () => {
  mocks.search.mockResolvedValue({ ...oldResult, hits: [] });
  render(<IndexPanel workspaceId="w" collectionId="a" canManage />);
  fireEvent.change(
    screen.getByRole("textbox", { name: "Câu truy vấn tìm kiếm thử" }),
    { target: { value: "synthetic query" } },
  );
  fireEvent.change(screen.getByLabelText("Năm dữ liệu"), {
    target: { value: "202" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Tìm thử" }));
  await act(async () => {
    await Promise.resolve();
  });
  expect(mocks.search).not.toHaveBeenCalled();
});

test("a valid year is sent unchanged", async () => {
  mocks.search.mockResolvedValue({ ...oldResult, hits: [] });
  render(<IndexPanel workspaceId="w" collectionId="a" canManage />);
  fireEvent.change(
    screen.getByRole("textbox", { name: "Câu truy vấn tìm kiếm thử" }),
    { target: { value: "synthetic query" } },
  );
  fireEvent.change(screen.getByLabelText("Năm dữ liệu"), {
    target: { value: "2026" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Tìm thử" }));
  await waitFor(() =>
    expect(mocks.search).toHaveBeenCalledWith(
      expect.objectContaining({ metadata_filter: { data_year: 2026 } }),
    ),
  );
});

test("catalog scope requires an explicit choice and preserves the manual year", async () => {
  mocks.search.mockResolvedValue({ ...oldResult, hits: [] });
  render(<IndexPanel workspaceId="w" collectionId="a" canManage />);
  const toggle = screen.getByRole("checkbox", { name: /Nhận diện phạm vi/ });
  expect(toggle.getAttribute("aria-checked")).toBe("false");
  fireEvent.click(toggle);
  fireEvent.change(
    screen.getByRole("textbox", { name: "Câu truy vấn tìm kiếm thử" }),
    { target: { value: "Nguồn dữ liệu" } },
  );
  fireEvent.change(screen.getByLabelText("Năm dữ liệu"), {
    target: { value: "2031" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Tìm thử" }));
  await waitFor(() =>
    expect(mocks.search).toHaveBeenCalledWith(
      expect.objectContaining({
        scope_resolution: "catalog",
        metadata_filter: { data_year: 2031 },
      }),
    ),
  );
});

test("completed search results must not stay visible under another collection", async () => {
  mocks.search.mockResolvedValue(oldResult);
  const view = render(
    <IndexPanel workspaceId="w" collectionId="a" canManage />,
  );
  fireEvent.change(
    screen.getByRole("textbox", { name: "Câu truy vấn tìm kiếm thử" }),
    { target: { value: "synthetic query" } },
  );
  fireEvent.click(screen.getByRole("button", { name: "Tìm thử" }));
  await screen.findByText("Synthetic private content from collection A");
  view.rerender(<IndexPanel workspaceId="w" collectionId="b" canManage />);
  expect(
    screen.queryByText("Synthetic private content from collection A"),
  ).toBeNull();
});

test("late search results must not land under another collection", async () => {
  let release!: (value: SearchResponse) => void;
  mocks.search.mockReturnValue(
    new Promise<SearchResponse>((resolve) => {
      release = resolve;
    }),
  );
  const view = render(
    <IndexPanel workspaceId="w" collectionId="a" canManage />,
  );
  fireEvent.change(
    screen.getByRole("textbox", { name: "Câu truy vấn tìm kiếm thử" }),
    { target: { value: "synthetic query" } },
  );
  fireEvent.click(screen.getByRole("button", { name: "Tìm thử" }));
  view.rerender(<IndexPanel workspaceId="w" collectionId="b" canManage />);
  await act(async () => release(oldResult));
  expect(
    screen.queryByText("Synthetic private content from collection A"),
  ).toBeNull();
});

test("invalid issued year blocks the Enter shortcut and exposes an accessible error", async () => {
  render(<IndexPanel workspaceId="w" collectionId="a" canManage />);
  const query = screen.getByRole("textbox", {
    name: "Câu truy vấn tìm kiếm thử",
  });
  fireEvent.change(query, { target: { value: "synthetic query" } });
  const year = screen.getByLabelText("Năm ban hành");
  fireEvent.change(year, { target: { value: "10000" } });
  fireEvent.keyDown(query, { key: "Enter" });
  await act(async () => {
    await Promise.resolve();
  });
  expect(year.getAttribute("aria-invalid")).toBe("true");
  expect(
    document.getElementById(year.getAttribute("aria-describedby") ?? "")
      ?.textContent,
  ).toMatch(/1000.*9999/);
  expect(mocks.search).not.toHaveBeenCalled();
});

test("a workspace change clears search state even with the same collection id", async () => {
  mocks.search.mockResolvedValue(oldResult);
  const view = render(
    <IndexPanel workspaceId="w-one" collectionId="a" canManage />,
  );
  fireEvent.change(
    screen.getByRole("textbox", { name: "Câu truy vấn tìm kiếm thử" }),
    { target: { value: "synthetic query" } },
  );
  fireEvent.click(screen.getByRole("button", { name: "Tìm thử" }));
  await screen.findByText("Synthetic private content from collection A");
  view.rerender(<IndexPanel workspaceId="w-two" collectionId="a" canManage />);
  expect(
    screen.queryByText("Synthetic private content from collection A"),
  ).toBeNull();
  expect(
    (
      screen.getByRole("textbox", {
        name: "Câu truy vấn tìm kiếm thử",
      }) as HTMLInputElement
    ).value,
  ).toBe("");
});

test("a new auth session drops both existing results and a pending response", async () => {
  setAccessToken("synthetic-index-session-one");
  let release!: (value: SearchResponse) => void;
  mocks.search.mockResolvedValueOnce(oldResult).mockReturnValueOnce(
    new Promise<SearchResponse>((resolve) => {
      release = resolve;
    }),
  );
  render(<IndexPanel workspaceId="w" collectionId="a" canManage />);
  const query = screen.getByRole("textbox", {
    name: "Câu truy vấn tìm kiếm thử",
  });
  fireEvent.change(query, { target: { value: "synthetic query" } });
  fireEvent.click(screen.getByRole("button", { name: "Tìm thử" }));
  await screen.findByText("Synthetic private content from collection A");
  fireEvent.keyDown(query, { key: "Enter" });
  act(() => setAccessToken("synthetic-index-session-two"));
  await act(async () => release(oldResult));
  expect(
    screen.queryByText("Synthetic private content from collection A"),
  ).toBeNull();
});

test("the newest search wins if two Enter requests finish out of order", async () => {
  let release!: (value: SearchResponse) => void;
  const newer = {
    ...oldResult,
    hits: [{ ...oldResult.hits[0], text: "Synthetic newer search result" }],
  };
  mocks.search
    .mockReturnValueOnce(
      new Promise<SearchResponse>((resolve) => {
        release = resolve;
      }),
    )
    .mockResolvedValueOnce(newer);
  render(<IndexPanel workspaceId="w" collectionId="a" canManage />);
  const query = screen.getByRole("textbox", {
    name: "Câu truy vấn tìm kiếm thử",
  });
  fireEvent.change(query, { target: { value: "first" } });
  fireEvent.keyDown(query, { key: "Enter" });
  fireEvent.change(query, { target: { value: "second" } });
  fireEvent.keyDown(query, { key: "Enter" });
  await screen.findByText("Synthetic newer search result");
  await act(async () => release(oldResult));
  expect(
    screen.queryByText("Synthetic private content from collection A"),
  ).toBeNull();
  expect(screen.getByText("Synthetic newer search result")).toBeTruthy();
});
