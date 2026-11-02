// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CompilationDialog } from "@/features/knowledge/compilation-dialog";

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
    mutateAsync: vi.fn(),
  }),
}));
beforeEach(() => {
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
it("keeps compiler configuration when parent renders the same pinned input again", () => {
  const view = render(<CompilationDialog {...props} initialRun={{ ...run }} />);
  fireEvent.change(screen.getByLabelText(/Chủ đề biên soạn/), {
    target: { value: "User-entered topic" },
  });
  expect(
    (screen.getByLabelText(/Chủ đề biên soạn/) as HTMLTextAreaElement).value,
  ).toBe("User-entered topic");
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
