// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { CreateKeyDialog } from "@/features/modelops/endpoints/create-key-dialog";
import { EndpointCard } from "@/features/modelops/endpoints/endpoint-card";
import type { IntegrationConfig } from "@/features/modelops/types";

const { mutateAsync } = vi.hoisted(() => ({ mutateAsync: vi.fn() }));
vi.stubGlobal(
  "ResizeObserver",
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  },
);
vi.mock("@/features/modelops/queries", () => ({
  useCreateAppApiKeyMutation: () => ({ mutateAsync, isPending: false }),
}));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

test("review: endpoint card uses actual backend IntegrationConfigResponse", () => {
  // Actual backend contract: schemas.IntegrationConfigResponse and GET /integrations/config.
  const response = {
    base_url: "https://qnu-review.invalid/platform/v1alpha1/integrations",
    openai_endpoint:
      "https://qnu-review.invalid/platform/v1alpha1/integrations/openai/v1",
    supported_protocols: [
      "OpenAI-compatible /chat/completions",
      "OpenAI-compatible /models",
    ],
    capabilities: ["chat", "evidence_first_citations", "rag_retrieval"],
    version: "v1alpha1",
  };
  render(<EndpointCard config={response as unknown as IntegrationConfig} />);
  expect(screen.queryByText(response.openai_endpoint)).not.toBeNull();
});

test("review: restricted scope with zero selected assistants cannot create an all-access key", async () => {
  mutateAsync.mockResolvedValue({ id: "key_synthetic" });
  render(
    <CreateKeyDialog
      open
      onOpenChange={vi.fn()}
      workspaceId="ws_review"
      assistants={[{ id: "ast_review", name: "Review assistant" }]}
      onSuccess={vi.fn()}
    />,
  );
  fireEvent.change(screen.getByLabelText(/Tên ứng dụng/), {
    target: { value: "Review app" },
  });
  fireEvent.change(screen.getByLabelText(/^Tên khóa/), {
    target: { value: "Review key" },
  });
  fireEvent.click(screen.getByLabelText("Tất cả trợ lý trong workspace"));
  fireEvent.click(screen.getByRole("button", { name: "Tạo khóa" }));
  await waitFor(() => expect(mutateAsync).not.toHaveBeenCalled());
});
