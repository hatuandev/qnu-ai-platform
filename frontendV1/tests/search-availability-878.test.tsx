// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import {
  SearchAvailability,
  useSearchAvailability,
} from "@/features/knowledge/search-availability";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  readiness: vi.fn(),
}));
vi.mock("@/app/api/v1", () => ({
  v1Client: { get: mocks.get, post: mocks.post },
}));
vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({ sessionId: "session-a" }),
}));
vi.mock("@/features/knowledge/index-requests", () => ({
  getDocumentIndexReadiness: mocks.readiness,
}));

const version = {
  id: "version-current",
  status: "published" as const,
  state_version: 3,
  bundle_sha256: "source-bundle",
};
function Harness({ canRetry = true }: { canRetry?: boolean }) {
  const state = useSearchAvailability(
    "workspace-a",
    "collection-a",
    "document-a",
    version,
  );
  return <SearchAvailability state={state} canRetry={canRetry} />;
}
function mount(canRetry = true) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <Harness canRetry={canRetry} />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  mocks.get.mockReset();
  mocks.post.mockReset();
  mocks.readiness.mockReset();
  mocks.get.mockResolvedValue({
    status: "building",
    revision: 1,
    error_code: null,
  });
  mocks.readiness.mockResolvedValue({ status: "not_indexed" });
});
afterEach(cleanup);

test("publication waits for the worker without submitting another index request", async () => {
  mount();
  await screen.findByText(/Đang cập nhật cho trợ lý AI/);
  await waitFor(() => expect(mocks.get).toHaveBeenCalled());
  expect(mocks.post).not.toHaveBeenCalled();
  expect(
    screen.queryByRole("button", { name: /Tạo index|Cập nhật tìm kiếm/ }),
  ).toBeNull();
});

test("a ready generation with the wrong version never displays ready", async () => {
  mocks.get.mockResolvedValue({
    status: "ready",
    revision: 1,
    error_code: null,
  });
  mocks.readiness.mockResolvedValue({
    status: "ready",
    version_id: "old-version",
    version_state: 3,
    bundle_sha256: "source-bundle",
  });
  mount();
  await screen.findByText("Tài liệu chưa được cập nhật cho trợ lý AI.");
  expect(screen.queryByText("Sẵn sàng tra cứu cho trợ lý AI.")).toBeNull();
});

test("ready requires matching published version state and bundle", async () => {
  mocks.get.mockResolvedValue({
    status: "ready",
    revision: 1,
    error_code: null,
  });
  mocks.readiness.mockResolvedValue({
    status: "ready",
    version_id: version.id,
    version_state: version.state_version,
    bundle_sha256: version.bundle_sha256,
  });
  mount();
  await screen.findByText("Sẵn sàng tra cứu cho trợ lý AI.");
});

test("uncertain work needs an explicit request and warns before creating new work", async () => {
  mocks.get.mockResolvedValue({
    status: "uncertain",
    revision: 1,
    error_code: "embedding_uncertain",
  });
  mocks.post.mockResolvedValue({
    status: "pending",
    revision: 2,
    error_code: null,
  });
  mount();
  await screen.findByText(/Chạy lại sẽ tạo tác vụ mới/);
  expect(mocks.post).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Thử cập nhật" }));
  await waitFor(() => expect(mocks.post).toHaveBeenCalledTimes(1));
  expect(mocks.post.mock.calls[0][0]).toMatch(/search-readiness\/retry$/);
  expect(mocks.post.mock.calls[0][2].idempotencyKey).toBeTruthy();
});

test("read-only members cannot request a new background update", async () => {
  mocks.get.mockResolvedValue({
    status: "failed",
    revision: 1,
    error_code: "embedding_auth_failed",
  });
  mount(false);
  await screen.findByText(/cập nhật tìm kiếm chưa hoàn tất/);
  expect(screen.queryByRole("button", { name: "Thử cập nhật" })).toBeNull();
});

test.each([
  { version_state: 2, bundle_sha256: version.bundle_sha256 },
  { version_state: version.state_version, bundle_sha256: "other-bundle" },
])("stale state or bundle cannot claim ready: %j", async (binding) => {
  mocks.get.mockResolvedValue({
    status: "ready",
    revision: 1,
    error_code: null,
  });
  mocks.readiness.mockResolvedValue({
    status: "ready",
    version_id: version.id,
    ...binding,
  });
  mount();
  await screen.findByText("Tài liệu chưa được cập nhật cho trợ lý AI.");
  expect(screen.queryByText("Sẵn sàng tra cứu cho trợ lý AI.")).toBeNull();
});

test("a readiness read error offers refresh without automatically starting work", async () => {
  mocks.get.mockRejectedValue(new Error("Synthetic read failure"));
  mount();
  await screen.findByText("Chưa xác minh được trạng thái phục vụ trợ lý.");
  expect(screen.getByRole("button", { name: "Kiểm tra lại" })).toBeTruthy();
  expect(mocks.post).not.toHaveBeenCalled();
});
