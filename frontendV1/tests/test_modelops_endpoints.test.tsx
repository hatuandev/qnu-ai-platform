// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ViewModeToggle } from "@/components/ui/view-mode-toggle";
import { EndpointCard } from "@/features/modelops/endpoints/endpoint-card";
import { KeySecretModal } from "@/features/modelops/endpoints/key-secret-modal";
import { ProviderCardGrid } from "@/features/modelops/provider-card-grid";
import type {
  AppApiKeySecretResponse,
  ProviderSummaryItem,
} from "@/features/modelops/types";

afterEach(cleanup);

test("ViewModeToggle switches between grid and table views", () => {
  const onChange = vi.fn();
  render(<ViewModeToggle value="grid" onChange={onChange} />);

  const tableBtn = screen.getByLabelText("Xem dạng danh sách bảng");
  expect(tableBtn).toBeDefined();
  fireEvent.click(tableBtn);
  expect(onChange).toHaveBeenCalledWith("table");

  const gridBtn = screen.getByLabelText("Xem dạng thẻ lưới");
  fireEvent.click(gridBtn);
  expect(onChange).toHaveBeenCalledWith("grid");
});

test("ProviderCardGrid groups providers by real registry family", () => {
  const onOpen = vi.fn();
  const mockProviders: ProviderSummaryItem[] = [
    {
      id: "prov_openai_01",
      name: "Qwen 2.5 7B",
      provider_type: "openai_compatible",
      base_url: "http://127.0.0.1:11434/v1",
      model_name: "qwen2.5:7b",
      capabilities: ["chat"],
      is_active: true,
      priority: 1,
      timeout_seconds: 30,
      token_limits: null,
      capacity_status: "unknown",
      capacity_basis: null,
      embedding_dimension: null,
      embedding_dimension_status: "unknown",
      created_at: "2026-10-28T00:00:00Z",
      updated_at: "2026-10-28T00:00:00Z",
      active_keys_count: 2,
      total_keys_count: 2,
      last_probe_status: "success",
      last_probe_at: "2026-10-28T10:00:00Z",
      last_probe_error: null,
    },
    {
      id: "prov_nemotron_01",
      name: "Nemotron OCR Production",
      provider_type: "nemotron",
      base_url: "http://127.0.0.1:8000/ocr",
      model_name: "nemotron-4-340b",
      capabilities: ["ocr"],
      is_active: true,
      priority: 2,
      timeout_seconds: 60,
      token_limits: null,
      capacity_status: "unknown",
      capacity_basis: null,
      embedding_dimension: null,
      embedding_dimension_status: "unknown",
      created_at: "2026-10-28T00:00:00Z",
      updated_at: "2026-10-28T00:00:00Z",
      active_keys_count: 1,
      total_keys_count: 1,
      last_probe_status: "untested",
      last_probe_at: null,
      last_probe_error: null,
    },
  ];

  render(<ProviderCardGrid providers={mockProviders} onOpen={onOpen} />);

  // Check section headers
  expect(screen.getByText("OpenAI Compatible")).toBeDefined();
  expect(screen.getByText("NVIDIA Nemotron OCR")).toBeDefined();

  // Check card content
  expect(screen.getByText("Qwen 2.5 7B")).toBeDefined();
  expect(screen.getByText("Nemotron OCR Production")).toBeDefined();

  // Check keys and probe status
  expect(screen.getByText(/2 khóa/)).toBeDefined();
  expect(screen.getByText("Đã kiểm tra")).toBeDefined();

  // Click card triggers onOpen
  fireEvent.click(screen.getByText("Qwen 2.5 7B"));
  expect(onOpen).toHaveBeenCalledWith(mockProviders[0]);
});

test("EndpointCard renders Base URL and feature badges", () => {
  const config = {
    base_url: "http://localhost:8002/platform/v1alpha1/integrations",
    openai_endpoint:
      "http://localhost:8002/platform/v1alpha1/integrations/openai/v1",
    capabilities: ["single_turn_chat"],
    supported_protocols: ["POST /chat/completions", "GET /models"],
    version: "v1alpha1",
  };

  render(<EndpointCard config={config} />);

  expect(screen.getByText("Điểm Cuối API Tích Hợp (Endpoints)")).toBeDefined();
  expect(
    screen.getByText(
      "http://localhost:8002/platform/v1alpha1/integrations/openai/v1",
    ),
  ).toBeDefined();
  expect(screen.getByText("POST /chat/completions")).toBeDefined();
  expect(screen.getByText("GET /models")).toBeDefined();
});

test("KeySecretModal displays secret once and fires onClose", () => {
  const onClose = vi.fn();
  const secretData: AppApiKeySecretResponse = {
    id: "key_001",
    app_id: "app_001",
    app_name: "Cổng Tuyển Sinh",
    workspace_id: "ws_001",
    name: "Khóa Web",
    key_prefix: "qnu_live_abcdef",
    status: "active",
    allowed_assistant_ids: [],
    rate_limit_rpm: 60,
    rate_limit_rpd: 10000,
    expires_at: null,
    last_used_at: null,
    rotated_from_key_id: null,
    revoked_at: null,
    revoked_reason: null,
    created_by: "usr_admin",
    created_at: "2026-10-28T00:00:00Z",
    secret_key: "qnu_live_super_secret_raw_token_xyz123",
  };

  render(<KeySecretModal data={secretData} onClose={onClose} />);

  expect(screen.getByText("Lưu Khóa Bí Mật Của Bạn")).toBeDefined();
  expect(
    screen.getByText("qnu_live_super_secret_raw_token_xyz123"),
  ).toBeDefined();
  expect(screen.getByText("Chỉ hiển thị một lần duy nhất")).toBeDefined();

  const closeBtn = screen.getByText("Tôi đã lưu khóa an toàn");
  fireEvent.click(closeBtn);
  expect(onClose).toHaveBeenCalled();
});
