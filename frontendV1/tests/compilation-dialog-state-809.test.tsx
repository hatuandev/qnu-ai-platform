// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CompilationDialog } from "@/features/knowledge/compilation-dialog";

const { create } = vi.hoisted(() => ({ create: vi.fn() }));
vi.mock("@/features/modelops/queries", () => ({
  useCatalogQuery: () => ({ data: [] }),
}));
vi.mock("@/features/modelops/capacity-badge", () => ({
  ConsumerModelBudgetNotice: () => null,
}));
vi.mock("@/features/knowledge/queries", () => ({
  useSourcesQuery: () => ({ data: { items: [] } }),
  useRevisionsQuery: () => ({ data: [] }),
}));
vi.mock("@/features/knowledge/ocr-queries", () => ({
  useProcessingRunsQuery: () => ({ data: { items: [] } }),
  useTextReviewQuery: () => ({ data: { version: 1 } }),
}));
vi.mock("@/features/knowledge/compilation-queries", () => ({
  useCreateCompilationMutation: () => ({
    isPending: false,
    mutateAsync: create,
  }),
}));
beforeEach(() => {
  create
    .mockReset()
    .mockResolvedValue({ created: true, run: { id: "compiled" } });
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
const run = {
  runId: "run-1",
  sourceId: "src-1",
  sourceTitle: "Source",
  revisionId: "rev-1",
  revisionNo: 1,
  generation: 1,
  textVersion: 1,
};
const props = {
  workspaceId: "ws-1",
  collectionId: "col-1",
  isOpen: true,
  onClose: vi.fn(),
};

it("keeps the request key when the parent rerenders the same pinned source", async () => {
  const view = render(<CompilationDialog {...props} initialRun={{ ...run }} />);
  fireEvent.click(screen.getByRole("button", { name: "Bắt đầu biên soạn" }));
  await waitFor(() => expect(create).toHaveBeenCalledOnce());
  view.rerender(<CompilationDialog {...props} initialRun={{ ...run }} />);
  fireEvent.click(screen.getByRole("button", { name: "Bắt đầu biên soạn" }));
  await waitFor(() => expect(create).toHaveBeenCalledTimes(2));
  expect(create.mock.calls[0][0]).toEqual(create.mock.calls[1][0]);
});
it("uses a fresh request key on reopening or switching the pinned version", async () => {
  const view = render(<CompilationDialog {...props} initialRun={run} />);
  fireEvent.click(screen.getByRole("button", { name: "Bắt đầu biên soạn" }));
  await waitFor(() => expect(create).toHaveBeenCalledOnce());
  view.rerender(
    <CompilationDialog {...props} isOpen={false} initialRun={run} />,
  );
  view.rerender(<CompilationDialog {...props} initialRun={run} />);
  fireEvent.click(screen.getByRole("button", { name: "Bắt đầu biên soạn" }));
  await waitFor(() => expect(create).toHaveBeenCalledTimes(2));
  view.rerender(
    <CompilationDialog {...props} initialRun={{ ...run, textVersion: 2 }} />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Bắt đầu biên soạn" }));
  await waitFor(() => expect(create).toHaveBeenCalledTimes(3));
  const keys = create.mock.calls.map(([request]) => request.idempotencyKey);
  expect(keys.every((key) => typeof key === "string")).toBe(true);
  expect(new Set(keys).size).toBe(3);
  expect(create.mock.calls[2][0].input).toMatchObject({
    ocr_run_ids: ["run-1"],
    text_versions: { "run-1": 2 },
  });
});

it("opens with the pinned saved version and automatic settings, without technical fields", async () => {
  render(
    <CompilationDialog {...props} initialRun={{ ...run, textVersion: 6 }} />,
  );
  expect(screen.getByText("Bản đã lưu v6 · Tệp v1")).toBeTruthy();
  expect(screen.queryByLabelText(/Chủ đề biên soạn/)).toBeNull();
  expect(screen.queryByRole("button", { name: "Thêm tài liệu" })).toBeNull();
  expect(screen.queryByRole("button", { name: /Thao tác nguồn/ })).toBeNull();
  expect(screen.queryByRole("button", { name: "Cài đặt nâng cao" })).toBeNull();
  expect(
    screen.queryByRole("checkbox", { name: "Biên soạn nhanh" }),
  ).toBeNull();
  expect(screen.queryByRole("switch")).toBeNull();
  expect(screen.queryByLabelText(/Giới hạn Output Tokens/)).toBeNull();
  expect(screen.queryByText("Tài liệu nguồn")).toBeNull();
  expect(screen.queryByText(/Run ID:|Gen #|Khóa:/)).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Bắt đầu biên soạn" }));
  await waitFor(() => expect(create).toHaveBeenCalledOnce());
  expect(create.mock.calls[0][0].input).toEqual({
    topic: "Source",
    ocr_run_ids: ["run-1"],
    text_versions: { "run-1": 6 },
    selective_supplement: true,
    auto_review: false,
  });
});

it("keeps advanced options in the collection entry point", () => {
  render(<CompilationDialog {...props} />);
  fireEvent.click(screen.getByRole("button", { name: "Cài đặt nâng cao" }));
  expect(
    screen.getByLabelText(/Giới hạn Output Tokens \(Tùy chọn\)/),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Cài đặt nâng cao" }));
  expect(screen.queryByLabelText(/Giới hạn Output Tokens/)).toBeNull();
});

it("opens the source picker for compilation started from a collection", () => {
  render(<CompilationDialog {...props} />);
  expect(screen.getByLabelText(/Chủ đề biên soạn/)).toBeTruthy();
  expect(screen.getByRole("button", { name: "Thêm tài liệu" })).toBeTruthy();
  expect(screen.getByText("Tài liệu nguồn")).toBeTruthy();
  expect(
    screen
      .getByRole("button", { name: "Bắt đầu biên soạn" })
      .hasAttribute("disabled"),
  ).toBe(true);
});
it("keeps the legacy hybrid controls at the collection entry point", () => {
  render(<CompilationDialog {...props} />);
  fireEvent.click(screen.getByRole("checkbox", { name: "Biên soạn nhanh" }));
  fireEvent.click(
    screen.getByRole("checkbox", { name: "AI bổ sung cấu trúc và metadata" }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Cài đặt nâng cao" }));
  expect(
    screen
      .getByRole("switch", { name: "Rà soát sau khi biên soạn" })
      .getAttribute("aria-checked"),
  ).toBe("false");
});
