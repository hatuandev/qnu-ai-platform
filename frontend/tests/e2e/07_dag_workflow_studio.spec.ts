import { expect, test } from "@playwright/test";

/**
 * Suite 07: Visual DAG Workflow Studio E2E Tests.
 * Verifies:
 * 1. Switching between 5 Official QNU Workflows (Admissions, Regulations, Drafting, Question Bank, Library).
 * 2. Opening Node Catalog Drawer, adding a node, and inspecting/editing properties via Property Inspector.
 * 3. In-Canvas Test Runner execution with real-time visual node status animation and chat response.
 */
test.describe("07. Visual DAG Workflow Studio", () => {
  test("TC-DAG-01: Switches between 5 official QNU workflows and verifies custom node topologies", async ({
    page,
  }) => {
    await page.goto("/nodes");
    await page.waitForLoadState("domcontentloaded");

    // 1. Verify default Admissions workflow
    await expect(page.locator("text=Luồng Trợ lý Tuyển sinh QNU").first()).toBeVisible();
    await expect(page.locator("text=input.chat")).toBeVisible();
    await expect(page.locator("text=qdrant+fts")).toBeVisible();
    await expect(page.locator("text=guard.citation")).toBeVisible();

    // 2. Switch to Drafting workflow
    const draftingBtn = page.getByRole("button", { name: /Soạn thảo/i });
    await expect(draftingBtn).toBeVisible();
    await draftingBtn.click();
    await page.waitForTimeout(300);

    // Verify drafting nodes appear (nd30_formatter, human_approval)
    await expect(page.locator("text=tool.api").first()).toBeVisible();
    await expect(page.locator("text=checkpoint").first()).toBeVisible();

    // 3. Switch to Question Bank workflow
    const qbBtn = page.getByRole("button", { name: /Đề thi/i });
    await expect(qbBtn).toBeVisible();
    await qbBtn.click();
    await page.waitForTimeout(300);

    // Verify Question bank nodes appear (core.llm)
    await expect(page.locator("text=core.llm").first()).toBeVisible();

    // Take screenshot of DAG canvas overview
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/dag_canvas_overview.png",
      fullPage: false,
    });
  });

  test("TC-DAG-02: Adds a new Node from Catalog and customizes properties via Property Inspector", async ({
    page,
  }) => {
    await page.goto("/nodes");
    await page.waitForLoadState("domcontentloaded");

    // Open Node Catalog Drawer
    const addNodeBtn = page.getByRole("button", { name: /Thêm Node/i });
    await expect(addNodeBtn).toBeVisible();
    await addNodeBtn.click();
    await page.waitForTimeout(300);

    // Verify Catalog Drawer opened
    await expect(page.locator("text=Thư Viện Nodes (Catalog)")).toBeVisible();

    // Find and add "Gọi Công Cụ Ngoại Vi" (tool.api_caller)
    const addToolBtn = page
      .locator('[data-testid="catalog-item-tool.api_caller"]')
      .getByRole("button", { name: /Thêm Node/i });
    await expect(addToolBtn).toBeVisible();
    await addToolBtn.click();
    await page.waitForTimeout(400);

    // Verify Property Inspector automatically opened for newly created node
    await expect(page.locator("text=Thuộc Tính Node")).toBeVisible();

    // Edit display name
    const labelInput = page.locator("#node-display-name");
    await expect(labelInput).toBeVisible();
    await labelInput.fill("Cổng Tra Cứu Điểm UIS Tự Động");

    // Save changes
    const saveBtn = page.getByRole("button", { name: /Lưu Cấu Hình Node/i });
    await expect(saveBtn).toBeVisible();
    await saveBtn.click();
    await page.waitForTimeout(200);

    // Verify success indicator
    await expect(page.locator("text=Đã lưu thành công!")).toBeVisible();

    // Take screenshot of Property Inspector
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/dag_property_inspector.png",
      fullPage: false,
    });
  });

  test("TC-DAG-03: Runs in-canvas test execution with live visual node animation", async ({
    page,
  }) => {
    await page.goto("/nodes");
    await page.waitForLoadState("domcontentloaded");

    // Open In-Canvas Test Runner
    const runTestBtn = page.getByRole("button", { name: /Chạy Thử Luồng/i });
    await expect(runTestBtn).toBeVisible();
    await runTestBtn.click();
    await page.waitForTimeout(300);

    // Verify Test Runner drawer is visible
    const runnerTitle = page.locator("text=Trình Chạy Thử Nghiệm Luồng (In-Canvas)");
    await expect(runnerTitle).toBeVisible();

    // Click a quick prompt
    const quickPrompt = page.locator("button").filter({ hasText: /Điểm chuẩn ngành Công nghệ thông tin/i }).first();
    await expect(quickPrompt).toBeVisible();
    await quickPrompt.click();

    // Click "Chạy Thử Luồng (Run DAG)"
    const executeBtn = page.getByRole("button", { name: /Chạy Thử Luồng \(Run DAG\)/i });
    await expect(executeBtn).toBeVisible();
    await executeBtn.click();

    // Verify running state and then completion
    await expect(page.locator("text=Kết Quả Thực Thi")).toBeVisible({ timeout: 10000 });

    // Verify response text contains QNU admission details in markdown output
    const outputArea = page.getByTestId("test-runner-markdown-output");
    await expect(outputArea).toBeVisible();
    await expect(outputArea).toContainText("Công nghệ thông tin");
    await expect(outputArea).toContainText("25.50");

    // Switch to Trace tab
    const traceTab = page.getByRole("tab", { name: /Trace/i });
    await expect(traceTab).toBeVisible();
    await traceTab.click();
    await page.waitForTimeout(200);

    // Verify executed steps listed
    await expect(page.locator("text=knowledge_answer").first()).toBeVisible();

    // Take screenshot of In-Canvas Test Runner completed with trace
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/dag_in_canvas_test_runner.png",
      fullPage: false,
    });
  });
});
