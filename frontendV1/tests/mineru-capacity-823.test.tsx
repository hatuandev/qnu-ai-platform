// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import {
  ConsumerModelBudgetNotice,
  resolveCapabilityBudgetState,
} from "@/features/modelops/capacity-badge";
import type { CatalogItem } from "@/features/modelops/types";

afterEach(cleanup);

test("MinerU catalog does not require an image-token bound", () => {
  const model: CatalogItem = {
    id: "mineru-test",
    name: "MinerU",
    model_name: "mineru",
    provider_type: "mineru",
    capabilities: ["ocr"],
    default_capabilities: ["ocr"],
    token_limits: null,
    capacity_status: "unknown",
    operational_budgets: {},
  };
  expect(resolveCapabilityBudgetState(model, "ocr").isBlocked).toBe(false);
  render(<ConsumerModelBudgetNotice model={model} capability="ocr" />);
  expect(screen.getByText(/không áp dụng token LLM/)).toBeDefined();
  expect(screen.queryByText(/Cần bổ sung thông tin/)).toBeNull();
  expect(
    resolveCapabilityBudgetState(
      { ...model, provider_type: "openai_compatible" },
      "ocr",
    ).isBlocked,
  ).toBe(true);
});
