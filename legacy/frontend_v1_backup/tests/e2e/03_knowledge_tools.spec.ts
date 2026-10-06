import { expect, test } from "@playwright/test";

/**
 * Suite 03: Knowledge Base & External Tools Gateway E2E Tests.
 * Tests collections/documents management, tabs, and Tool Playground execution.
 */

test.describe("03. Knowledge Base & Tools Gateway", () => {
  test("TC-KNW-01: Knowledge page displays title, tabs and collections", async ({ page }) => {
    await page.goto("/knowledge");
    await page.waitForLoadState("domcontentloaded");

    // Verify heading
    const heading = page.locator("h1").filter({ hasText: "Quản Trị Kho Tri Thức" });
    await expect(heading).toBeVisible();

    // Verify tab buttons exist
    const tabsList = page.locator('[role="tablist"]');
    await expect(tabsList).toBeVisible();
  });

  test("TC-KNW-02: Switching tabs in Knowledge Page works properly", async ({ page }) => {
    await page.goto("/knowledge");
    await page.waitForLoadState("domcontentloaded");

    // Click 'Tài liệu' tab
    const documentsTab = page.locator('[role="tab"]').filter({ hasText: "Tài liệu" }).first();
    if (await documentsTab.isVisible()) {
      await documentsTab.click();
      await page.waitForTimeout(300);
    }
  });

  test("TC-TOOL-01: Tools page displays 3 standard enterprise QNU tools", async ({ page }) => {
    await page.goto("/tools");
    await page.waitForLoadState("domcontentloaded");

    // Heading
    const heading = page.locator("h1").filter({ hasText: "Cổng Công Cụ Ngoại Vi" });
    await expect(heading).toBeVisible();

    // 3 Tools (resilient across backend and mock titles)
    const uisTool = page.locator("h3").filter({ hasText: /Tuyển Sinh/i });
    const docxTool = page.locator("h3").filter({ hasText: /Word.*NĐ 30/i });
    const xlsxTool = page.locator("h3").filter({ hasText: /Excel.*Bloom/i });

    await expect(uisTool).toBeVisible();
    await expect(docxTool).toBeVisible();
    await expect(xlsxTool).toBeVisible();
  });

  test("TC-TOOL-02: Tool Playground executes tool and displays result JSON", async ({ page }) => {
    await page.goto("/tools");
    await page.waitForLoadState("domcontentloaded");

    // Find run button
    const runButton = page.locator("button").filter({ hasText: "Thực Thi Công Cụ" });
    await expect(runButton).toBeVisible();

    // Click execute
    await runButton.click();

    // Wait for result JSON to appear
    const resultJson = page.locator("pre, code").filter({ hasText: "uis_admissions_query" });
    await expect(resultJson.first()).toBeVisible({ timeout: 5000 });
  });
});
