import { expect, test } from "@playwright/test";
import { loginAndEnsureDashboard } from "./helpers/auth";

test.describe("Mobile Responsive Smoke Test", () => {
  test("should render mobile layout cleanly with accessible navigation drawer", async ({
    page,
  }) => {
    await test.step("1. Đăng nhập trên màn hình di động", async () => {
      await loginAndEnsureDashboard(page);
    });

    await test.step("2. Kiểm tra thanh đầu trang (Topbar) co giãn responsive", async () => {
      const topbar = page.getByRole("banner");
      await expect(topbar).toBeVisible();
    });

    await test.step("3. Mở menu điều hướng trên mobile (Sheet / Drawer)", async () => {
      // Find hamburger menu button on mobile
      const menuBtn = page
        .getByRole("button", { name: /Toggle Sidebar|Menu/i })
        .or(page.locator("button:has(svg.lucide-menu, svg.lucide-panel-left)"))
        .first();

      if (await menuBtn.isVisible({ timeout: 5000 })) {
        await menuBtn.click();
        // Check that navigation items appear inside drawer
        await expect(page.getByText("Kho tri thức").first()).toBeVisible({
          timeout: 5000,
        });
      }
    });
  });
});
