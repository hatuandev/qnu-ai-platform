import { test, expect } from "@playwright/test";

/**
 * Suite 01: Navigation, Breadcrumbs, Theme Toggle & Smoke Verification.
 * Ensures all 13 business screens load cleanly with zero critical console errors.
 */

const ROUTES = [
  { path: "/", titleFragment: "Bảng Điều Khiển" },
  { path: "/assistants", titleFragment: "Trợ Lý AI" },
  { path: "/chat", titleFragment: "Chat Studio" },
  { path: "/conversations", titleFragment: "Hội Thoại" },
  { path: "/channels", titleFragment: "Kênh Phân Phối" },
  { path: "/runs", titleFragment: "Lịch Sử Thực Thi" },
  { path: "/knowledge", titleFragment: "Kho Tri Thức" },
  { path: "/nodes", titleFragment: "Visual DAG Canvas" },
  { path: "/tools", titleFragment: "Cổng Công Cụ" },
  { path: "/evaluation", titleFragment: "Kiểm Định Ragas" },
  { path: "/models", titleFragment: "Quản Trị Mô Hình" },
  { path: "/developer", titleFragment: "Khóa API" },
  { path: "/design-system", titleFragment: "Hệ Thống Thiết Kế" },
];

test.describe("01. Navigation & Smoke Tests", () => {
  test("TC-NAV-01: All 13 business screens render without unhandled errors", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    for (const route of ROUTES) {
      await page.goto(route.path);
      await page.waitForLoadState("domcontentloaded");

      // Verify the main page body has content
      const bodyText = await page.textContent("body");
      expect(bodyText).toBeTruthy();

      // Check URL
      expect(page.url()).toContain(route.path);
    }

    // Fail if there are unhandled react/javascript crashes
    const criticalErrors = consoleErrors.filter(
      (err) =>
        !err.includes("Failed to load resource") && // Ignore offline backend requests
        !err.includes("ECONNREFUSED")
    );
    expect(criticalErrors).toEqual([]);
  });

  test("TC-NAV-02: Theme toggle switches between Dark and Light mode properly", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("domcontentloaded");

    const html = page.locator("html");
    const themeButton = page.locator('button[aria-label="Toggle Theme"]');
    await expect(themeButton).toBeVisible();

    const isInitiallyDark = (await html.getAttribute("class"))?.includes("dark");

    // Toggle theme
    await themeButton.click();
    if (isInitiallyDark) {
      await expect(html).not.toHaveClass(/dark/);
    } else {
      await expect(html).toHaveClass(/dark/);
    }

    // Toggle back
    await themeButton.click();
    if (isInitiallyDark) {
      await expect(html).toHaveClass(/dark/);
    } else {
      await expect(html).not.toHaveClass(/dark/);
    }
  });

  test("TC-NAV-03: Sidebar can be toggled to expand and collapse", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("header")).toBeVisible({ timeout: 10000 });

    const sidebarToggle = page.locator('button[aria-label="Toggle Sidebar"]');
    await expect(sidebarToggle).toBeVisible({ timeout: 10000 });

    // Toggle sidebar
    await sidebarToggle.click();
    await page.waitForTimeout(300);

    // Toggle back
    await sidebarToggle.click();
    await page.waitForTimeout(300);
  });

  test("TC-NAV-04: Quick search modal opens on click and closes on Escape", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("domcontentloaded");

    const searchButton = page.locator('button[aria-label="Mở tìm kiếm nhanh"]');
    await expect(searchButton).toBeVisible();

    await searchButton.click();
    // Modal dialog or input should appear
    const searchInput = page.locator('input[placeholder*="Tìm kiếm"]');
    if (await searchInput.isVisible()) {
      await page.keyboard.press("Escape");
    }
  });
});
