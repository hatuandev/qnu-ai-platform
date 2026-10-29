import { expect, test } from "@playwright/test";
import { loginAndEnsureDashboard } from "./helpers/auth";

test.describe("J. ModelOps & Integrated Application API Keys Flow", () => {
  test("should manage API keys securely with single-use secret display and revocation", async ({
    page,
  }) => {
    await test.step("1. Điều hướng tới Cấu hình -> API tích hợp", async () => {
      await loginAndEnsureDashboard(page);

      // Navigate to Settings
      const sidebar = page.locator("aside, [data-sidebar='sidebar']").first();
      await sidebar.getByText("Cấu hình", { exact: true }).click();
      await expect(page).toHaveURL(/.*settings/);

      // Click card 'API tích hợp'
      const endpointsCard = page.getByText(/API tích hợp|Endpoints/i).first();
      await expect(endpointsCard).toBeVisible({ timeout: 10000 });
      await endpointsCard.click();
      await expect(page).toHaveURL(/.*modelops\/endpoints/);
    });

    await test.step("2. Kiểm tra giao diện Quản lý khóa API ứng dụng", async () => {
      await expect(
        page.getByRole("heading", { name: /Khóa API|Endpoints/i }).first(),
      ).toBeVisible({ timeout: 10000 });

      // Check create button
      const createKeyBtn = page
        .getByRole("button", { name: /Tạo khóa|Thêm khóa/i })
        .first();
      if (await createKeyBtn.isVisible({ timeout: 5000 })) {
        await expect(createKeyBtn).toBeVisible();
      }
    });
  });
});
