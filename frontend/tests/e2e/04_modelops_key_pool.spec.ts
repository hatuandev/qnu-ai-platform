import { expect, test } from "@playwright/test";

test.describe("04. Provider Management, Detail Screen & LobeHub SVG Icons", () => {
  test("TC-PROV-01: /models overview page displays Quản Lý Provider and Minimalist Provider Cards", async ({
    page,
  }) => {
    await page.goto("/models");
    await page.waitForLoadState("networkidle");

    // Title check
    await expect(page.locator("h1")).toContainText("Quản Lý Provider");

    // Check presence of at least one provider card or empty state
    const providerCards = page.locator(".grid > div");
    if ((await providerCards.count()) > 0) {
      const firstCard = providerCards.first();
      await expect(firstCard).toBeVisible();

      // Check click on card transitions to Detail View
      await firstCard.click();
      await page.waitForTimeout(400);

      // Verify Detail View breadcrumb and header
      await expect(
        page.getByRole("button", { name: "Quay lại danh sách Nhà cung cấp" })
      ).toBeVisible();
      await expect(page.getByText("Chi Tiết Provider")).toBeVisible();
      await expect(page.getByText("Nhóm Khóa API (Key Pool)")).toBeVisible();
      await expect(page.getByText("Mô Hình Khả Dụng")).toBeVisible();
    }
  });

  test("TC-PROV-02: Create Provider modal displays catalog presets with LobeHub icons", async ({
    page,
  }) => {
    await page.goto("/models");
    await page.waitForLoadState("networkidle");

    // Click Add Provider
    await page.getByRole("button", { name: "Thêm Provider Mới" }).click();

    // Check Dialog
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText("Mẫu Cấu Hình Sẵn (Presets)");

    // Check preset buttons
    await expect(dialog.getByRole("button", { name: "Google Gemini" })).toBeVisible();
    await expect(dialog.getByRole("button", { name: "DeepSeek AI" })).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Groq Cloud (LPU)" })).toBeVisible();

    // Click Groq preset and check auto-fill
    await dialog.getByRole("button", { name: "Groq Cloud (LPU)" }).click();
    const nameInput = dialog.locator('input[placeholder*="Ví dụ: OpenAI Production"]');
    await expect(nameInput).toHaveValue("Groq Cloud (LPU)");

    // Close Dialog
    await dialog.getByRole("button", { name: "Hủy" }).click();
    await expect(dialog).not.toBeVisible();
  });

  test("TC-PROV-03: Provider Detail View handles Hero Toggle Switch, Key Pool form and Back navigation", async ({
    page,
  }) => {
    await page.goto("/models");
    await page.waitForLoadState("networkidle");

    const providerCards = page.locator(".grid > div");
    if ((await providerCards.count()) > 0) {
      // Click first card to navigate to Detail View
      await providerCards.first().click();
      await page.waitForTimeout(400);

      // Check Detail View Hero Card toggle switch
      const heroSwitch = page.locator(".shadow-xs, .bg-card").getByRole("switch").first();
      await expect(heroSwitch).toBeVisible();

      // Check Key Pool section in detail screen
      await expect(page.getByRole("button", { name: "Test 429 Failover" })).toBeVisible();
      const addKeyBtn = page.getByRole("button", { name: "Thêm Khóa Mới" });
      await expect(addKeyBtn).toBeVisible();

      // Open Add Key form
      await addKeyBtn.click();
      await expect(page.getByText("Thêm Khóa API Mới Vào Nhóm")).toBeVisible();
      await expect(page.getByPlaceholder("VD: Key Khoa CNTT 2, Free Tier B...")).toBeVisible();

      // Close Add Key form
      await page.getByRole("button", { name: "Đóng Form" }).click();

      // Click Back to list
      const backBtn = page.getByRole("button", { name: "Quay lại danh sách Nhà cung cấp" });
      await backBtn.click();
      await page.waitForTimeout(300);

      // Verify back on overview
      await expect(page.locator("h1")).toContainText("Quản Lý Provider");
    }
  });
});
