// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ConnectionKeyModal } from "@/features/modelops/connections/connection-key-modal";
import { ApiError } from "@/app/api/client";

const mocks = vi.hoisted(() => ({
  addKey: vi.fn(),
  addModel: vi.fn(),
  testConnection: vi.fn(),
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: {
    error: (msg: string) => mocks.toastError(msg),
    success: (msg: string) => mocks.toastSuccess(msg),
  },
}));

vi.mock("@/features/modelops/connections/api", () => ({
  useAddConnectionKey: () => ({
    mutateAsync: mocks.addKey,
    isPending: false,
  }),
  useAddConnectionModel: () => ({
    mutateAsync: mocks.addModel,
    isPending: false,
  }),
  useTestConnection: () => ({
    mutateAsync: mocks.testConnection,
  }),
}));

describe("ConnectionKeyModal payload validation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("matchMedia", () => ({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
  });

  afterEach(() => {
    cleanup();
  });

  it("submits exactly name, secret and priority without extra default_model property", async () => {
    mocks.addKey.mockResolvedValueOnce({ id: "key_123" });
    mocks.addModel.mockResolvedValueOnce({ id: "model_123" });

    render(
      <ConnectionKeyModal
        open={true}
        onOpenChange={vi.fn()}
        connectionId="conn_1e28e3a3"
        connectionName="Test Connection"
        availableModels={["model-existing"]}
      />,
    );

    fireEvent.change(screen.getByLabelText(/Tên kết nối/i), {
      target: { value: "dev" },
    });
    fireEvent.change(screen.getByLabelText(/^API Key/i), {
      target: { value: "sk-test-secret-123" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Lưu API Key/i }));

    await waitFor(() => {
      expect(mocks.addKey).toHaveBeenCalledTimes(1);
    });

    // Verify payload strictly matches KeyCreateRequest schema
    const submittedPayload = mocks.addKey.mock.calls[0][0];
    expect(submittedPayload).toEqual({
      name: "dev",
      secret: "sk-test-secret-123",
      priority: 5,
    });
    expect(submittedPayload).not.toHaveProperty("default_model");
  });

  it("displays specific RFC 7807 problem details message on ApiError", async () => {
    mocks.addKey.mockRejectedValueOnce(
      new ApiError(422, "Extra inputs are not permitted: default_model", {
        detail: "Extra inputs are not permitted: default_model",
      }),
    );

    render(
      <ConnectionKeyModal
        open={true}
        onOpenChange={vi.fn()}
        connectionId="conn_1e28e3a3"
        connectionName="Test Connection"
      />,
    );

    fireEvent.change(screen.getByLabelText(/Tên kết nối/i), {
      target: { value: "dev" },
    });
    fireEvent.change(screen.getByLabelText(/^API Key/i), {
      target: { value: "sk-test-secret-123" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Lưu API Key/i }));

    await waitFor(() => {
      expect(mocks.toastError).toHaveBeenCalledWith(
        "Extra inputs are not permitted: default_model",
      );
    });
  });
});
