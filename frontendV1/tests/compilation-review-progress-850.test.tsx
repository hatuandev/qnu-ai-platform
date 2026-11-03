// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { CompilationReviewTab } from "../src/features/knowledge/compilation-review-tab";
import type { ReviewProgressResponse } from "../src/features/knowledge/compilation-types";

const ports = vi.hoisted(() => ({
  status: "uncertain",
  progress: undefined as ReviewProgressResponse | undefined,
  progressError: false,
  refetch: vi.fn(),
  create: vi.fn(),
  cancel: vi.fn(),
  report: vi.fn(),
}));
vi.mock("@/features/knowledge/compilation-requests", () => ({
  cancelCompilationReview: ports.cancel,
}));
vi.mock("@/features/modelops/queries", () => ({
  useCatalogQuery: () => ({ data: [] }),
}));
vi.mock("@/features/knowledge/review-downloads", () => ({
  ReviewDownloads: () => null,
}));
vi.mock("@/features/knowledge/compilation-queries", () => ({
  useAutoReviewQuery: () => ({
    data: { status: "uncertain", review_id: "old" },
    refetch: ports.refetch,
  }),
  useCompilationReviewsQuery: () => ({
    data: [{ id: "old", status: ports.status }],
    refetch: ports.refetch,
  }),
  useCompilationReviewQuery: (
    _w: string,
    _c: string,
    _r: string,
    id: string,
  ) => ({
    refetch: ports.refetch,
    data: {
      id,
      status: ports.status,
      error_code:
        ports.status === "uncertain" ? "chat_provider_uncertain" : null,
    },
  }),
  useCompilationReviewProgressQuery: () => ({
    data: ports.progress,
    isError: ports.progressError,
    refetch: ports.refetch,
  }),
  useCompilationReviewReportQuery: (...args: unknown[]) => {
    ports.report(...args);
    return {};
  },
  useCreateReviewMutation: () => ({
    mutateAsync: ports.create,
    isPending: false,
  }),
}));
const props = {
  workspaceId: "w",
  collectionId: "c",
  runId: "run",
  canReview: true,
};
beforeEach(() => {
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  vi.clearAllMocks();
  ports.status = "uncertain";
  ports.progressError = false;
  ports.create.mockResolvedValue({ id: "new" });
  ports.progress = {
    review_id: "old",
    status: "uncertain",
    segmented: true,
    total: 11,
    completed: 1,
    pending: 9,
    running: 0,
    failed: 0,
    uncertain: 1,
    cancelled: 0,
    segments: [
      {
        id: "s1",
        index: 1,
        depth: 0,
        is_leaf: true,
        status: "completed",
        error_code: null,
      },
      {
        id: "s2",
        index: 2,
        depth: 0,
        is_leaf: true,
        status: "uncertain",
        error_code: "chat_provider_uncertain",
      },
      {
        id: "s3",
        index: 3,
        depth: 0,
        is_leaf: true,
        status: "pending",
        error_code: null,
      },
    ],
  };
});
afterEach(cleanup);

function currentProgress(): ReviewProgressResponse {
  if (!ports.progress) throw new Error("Missing progress fixture");
  return ports.progress;
}

test("interrupted review exposes preserved partial work without claiming an empty successful report", () => {
  render(<CompilationReviewTab {...props} />);
  expect(screen.getByText("Lượt rà soát chưa hoàn tất")).toBeTruthy();
  expect(screen.getByText("1/11 nhóm hoàn tất")).toBeTruthy();
  expect(screen.getByText("9%")).toBeTruthy();
  expect(screen.getByText(/9 chưa chạy.*1 chưa xác định/)).toBeTruthy();
  expect(screen.getByText(/Hệ thống không tự gửi lại/)).toBeTruthy();
  expect(screen.queryByText("Không thể tải báo cáo review")).toBeNull();
  expect(ports.create).not.toHaveBeenCalled();
  expect(ports.report).toHaveBeenLastCalledWith("w", "c", "run", "old", {
    enabled: false,
  });
  fireEvent.click(screen.getByText("Chi tiết từng nhóm"));
  expect(screen.getByText("Nhóm 2")).toBeTruthy();
  expect(screen.getByText("Chưa xác định kết quả")).toBeTruthy();
});

test("running review uses actual group counts", () => {
  ports.status = "running";
  ports.progress = {
    ...currentProgress(),
    status: "running",
    running: 2,
    pending: 8,
    uncertain: 0,
  };
  render(<CompilationReviewTab {...props} />);
  expect(screen.getByText("Đang rà soát độc lập")).toBeTruthy();
  expect(screen.getByRole("progressbar").getAttribute("aria-valuenow")).toBe(
    "9.090909090909092",
  );
  expect(screen.getByText(/2 đang chạy.*8 chưa chạy/)).toBeTruthy();
  expect(ports.create).not.toHaveBeenCalled();
});

test("GET failure preserves terminal review status and only retries reading progress", () => {
  ports.progressError = true;
  render(<CompilationReviewTab {...props} />);
  expect(screen.getByText("Lượt rà soát chưa hoàn tất")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Tải lại tiến độ" }));
  expect(ports.refetch).toHaveBeenCalledTimes(1);
  expect(ports.create).not.toHaveBeenCalled();
});

test("stop sends a request for the selected review and refreshes its status", async () => {
  ports.status = "running";
  ports.progress = { ...currentProgress(), status: "running" };
  ports.cancel.mockResolvedValue({ status: "cancelled" });
  const { rerender } = render(<CompilationReviewTab {...props} />);
  fireEvent.click(screen.getByRole("button", { name: "Dừng rà soát" }));
  await waitFor(() => expect(ports.refetch).toHaveBeenCalled());
  expect(ports.cancel).toHaveBeenCalledExactlyOnceWith(
    expect.anything(),
    "w",
    "c",
    "run",
    "old",
  );
  ports.status = "cancelled";
  rerender(<CompilationReviewTab {...props} />);
  expect(screen.queryByRole("button", { name: "Dừng rà soát" })).toBeNull();
  expect(ports.create).not.toHaveBeenCalled();
});

test("progress from another review cannot leak into selected review", () => {
  ports.progress = { ...currentProgress(), review_id: "other", completed: 8 };
  render(<CompilationReviewTab {...props} />);
  expect(screen.queryByText("8/11 nhóm hoàn tất")).toBeNull();
  expect(screen.getByText("Đang tải tiến độ nhóm…")).toBeTruthy();
});

test("unplanned groups never generate a fabricated progress percentage", () => {
  ports.status = "queued";
  ports.progress = {
    ...currentProgress(),
    status: "queued",
    total: 0,
    completed: 0,
    segments: [],
  };
  render(<CompilationReviewTab {...props} />);
  expect(screen.queryByRole("progressbar")).toBeNull();
  expect(screen.getByText("0/0 nhóm hoàn tất")).toBeTruthy();
});

test("creating a new manual review selects its deep link instead of the old automatic review", async () => {
  const onSearchChange = vi.fn();
  render(<CompilationReviewTab {...props} onSearchChange={onSearchChange} />);
  fireEvent.click(
    screen.getByRole("button", { name: "Yêu cầu Review thủ công" }),
  );
  expect(screen.getByText(/Lịch sử lượt cũ được giữ lại/)).toBeTruthy();
  expect(ports.create).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Bắt đầu Review" }));
  await waitFor(() =>
    expect(onSearchChange).toHaveBeenCalledWith({
      reviewId: "new",
      reviewPage: 1,
    }),
  );
  expect(ports.create).toHaveBeenCalledTimes(1);
});
