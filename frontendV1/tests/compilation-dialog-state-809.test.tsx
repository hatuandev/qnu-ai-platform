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

it("submits the pinned version in fast mode without AI generation settings", async () => {
  render(<CompilationDialog {...props} initialRun={run} />);
  fireEvent.click(screen.getByRole("checkbox", { name: "Biên soạn nhanh" }));
  expect(screen.queryByRole("button", { name: "Cài đặt nâng cao" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Bắt đầu biên soạn" }));
  await waitFor(() => expect(create).toHaveBeenCalledOnce());
  expect(create.mock.calls[0][0].input).toEqual({
    topic: "Source",
    ocr_run_ids: ["run-1"],
    text_versions: { "run-1": 1 },
    source_first: true,
    auto_review: false,
  });
});
it("keeps compiler configuration when parent renders the same pinned input again", async () => {
  const view = render(<CompilationDialog {...props} initialRun={{ ...run }} />);
  fireEvent.change(screen.getByLabelText(/Chủ đề biên soạn/), {
    target: { value: "User-entered topic" },
  });
  expect(
    (screen.getByLabelText(/Chủ đề biên soạn/) as HTMLTextAreaElement).value,
  ).toBe("User-entered topic");
  fireEvent.click(screen.getByRole("button", { name: "Cài đặt nâng cao" }));
  fireEvent.change(
    screen.getByLabelText(/Giới hạn Output Tokens \(Tùy chọn\)/),
    { target: { value: "2048" } },
  );
  fireEvent.click(screen.getByRole("switch"));
  view.rerender(<CompilationDialog {...props} initialRun={{ ...run }} />);
  expect(
    (screen.getByLabelText(/Chủ đề biên soạn/) as HTMLTextAreaElement).value,
  ).toBe("User-entered topic");
  expect(
    (
      screen.getByLabelText(
        /Giới hạn Output Tokens \(Tùy chọn\)/,
      ) as HTMLInputElement
    ).value,
  ).toBe("2048");
  expect(screen.getByRole("switch").getAttribute("aria-checked")).toBe("false");
  fireEvent.click(screen.getByRole("button", { name: "Cài đặt nâng cao" }));
  fireEvent.click(screen.getByRole("button", { name: "Bắt đầu biên soạn" }));
  await waitFor(() => expect(create).toHaveBeenCalledOnce());
  expect(create.mock.calls[0][0]).toMatchObject({
    input: {
      topic: "User-entered topic",
      text_versions: { "run-1": 1 },
      max_output_tokens: 2048,
      auto_review: false,
    },
  });
});
it("starts a fresh configuration when reopened or switched to another pinned version", () => {
  const view = render(<CompilationDialog {...props} initialRun={run} />);
  const enter = () =>
    fireEvent.change(screen.getByLabelText(/Chủ đề biên soạn/), {
      target: { value: "Old topic" },
    });
  enter();
  view.rerender(
    <CompilationDialog {...props} isOpen={false} initialRun={run} />,
  );
  view.rerender(<CompilationDialog {...props} initialRun={run} />);
  expect(
    (screen.getByLabelText(/Chủ đề biên soạn/) as HTMLTextAreaElement).value,
  ).toBe("");
  enter();
  view.rerender(
    <CompilationDialog {...props} initialRun={{ ...run, textVersion: 2 }} />,
  );
  expect(
    (screen.getByLabelText(/Chủ đề biên soạn/) as HTMLTextAreaElement).value,
  ).toBe("");
});

it("opens with the pinned saved version and automatic settings, without technical fields", async () => {
  render(
    <CompilationDialog {...props} initialRun={{ ...run, textVersion: 6 }} />,
  );
  expect(screen.getByText("Bản đã lưu v6 · Tệp v1")).toBeTruthy();
  expect(screen.queryByLabelText(/Giới hạn Output Tokens/)).toBeNull();
  expect(screen.queryByText("Tài liệu nguồn")).toBeNull();
  expect(screen.queryByText(/Run ID:|Gen #|Khóa:/)).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Bắt đầu biên soạn" }));
  await waitFor(() => expect(create).toHaveBeenCalledOnce());
  expect(create.mock.calls[0][0]).toMatchObject({
    input: {
      topic: "Source",
      ocr_run_ids: ["run-1"],
      text_versions: { "run-1": 6 },
      provider_id: null,
      max_output_tokens: null,
      structured_output: false,
      auto_review: true,
      review_provider_id: null,
      review_max_output_tokens: null,
    },
  });
});

it("lets a user open source selection and advanced options only when needed", () => {
  render(<CompilationDialog {...props} initialRun={run} />);
  fireEvent.click(screen.getByRole("button", { name: "Thêm tài liệu" }));
  expect(screen.getByText("Tài liệu nguồn")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Cài đặt nâng cao" }));
  expect(
    screen.getByLabelText(/Giới hạn Output Tokens \(Tùy chọn\)/),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Cài đặt nâng cao" }));
  expect(screen.queryByLabelText(/Giới hạn Output Tokens/)).toBeNull();
});

it("opens the source picker for compilation started from a collection", () => {
  render(<CompilationDialog {...props} />);
  expect(screen.getByText("Tài liệu nguồn")).toBeTruthy();
  expect(
    screen
      .getByRole("button", { name: "Bắt đầu biên soạn" })
      .hasAttribute("disabled"),
  ).toBe(true);
});
