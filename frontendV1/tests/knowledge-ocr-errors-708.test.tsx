// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { OcrTabContainer } from "@/features/knowledge/ocr-tab-container";

const fixture = vi.hoisted(() => ({ status: "failed" }));
vi.mock("@tanstack/react-router", () => ({ useBlocker: () => undefined }));
vi.mock("@/features/knowledge/ocr-queries", () => ({
  useProcessingRunsQuery: () => ({ data: { items: [] } }),
  useProcessingRunDetailQuery: () => ({
    data: {
      id: "ocr",
      generation: 1,
      status: fixture.status,
      error_code: "ocr_provider_timeout",
      error_detail: "Synthetic timeout",
      config_fingerprint: "hash",
    },
  }),
  useTextReviewQuery: () => ({ data: undefined }),
}));
vi.mock("@/features/knowledge/ocr-runs-list", () => ({
  OcrRunsList: () => null,
}));
vi.mock("@/features/knowledge/ocr-request-dialog", () => ({
  OcrRequestDialog: () => null,
}));
vi.mock("@/features/knowledge/ocr-artifacts-panel", () => ({
  OcrArtifactsPanel: () => null,
}));
vi.mock("@/features/knowledge/ocr-comparison-view", () => ({
  OcrComparisonView: () => null,
}));
vi.mock("@/features/knowledge/ocr-text-review-panel", () => ({
  OcrTextReviewPanel: () => null,
}));
afterEach(cleanup);

test.each(["failed", "uncertain"])(
  "OCR %s shows an actionable error outside the technical tab",
  (status) => {
    fixture.status = status;
    render(
      <OcrTabContainer
        workspaceId="w"
        collectionId="c"
        sourceId="s"
        revisionId="r"
        revisionNo={1}
        fileName="synthetic.pdf"
        contentType="application/pdf"
        canManage={false}
        initialRunId="ocr"
      />,
    );
    expect(screen.getByRole("alert").textContent).toContain(
      "ocr_provider_timeout",
    );
  },
);

test("a completed OCR run does not show a stale failure banner", () => {
  fixture.status = "completed";
  render(
    <OcrTabContainer
      workspaceId="w"
      collectionId="c"
      sourceId="s"
      revisionId="r"
      revisionNo={1}
      fileName="synthetic.pdf"
      contentType="application/pdf"
      canManage={false}
      initialRunId="ocr"
    />,
  );
  expect(screen.queryByRole("alert")).toBeNull();
});
