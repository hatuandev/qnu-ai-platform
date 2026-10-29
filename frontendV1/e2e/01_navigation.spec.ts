import { expect, test } from "@playwright/test";
import { loginAndEnsureDashboard } from "./helpers/auth";

test.describe("A. Navigation & Authentication Flow", () => {
  test("should authenticate via dev-gate and display 6 core sidebar navigation items", async ({
    page,
  }) => {
    await test.step("1. Đăng nhập qua dev auto-login và hiển thị trang Tổng quan", async () => {
      await loginAndEnsureDashboard(page);
      await expect(page).toHaveURL(/.*dashboard/);
      await expect(
        page.getByRole("heading", { name: "Tổng quan" }),
      ).toBeVisible();
    });

    await test.step("2. Kiểm tra bộ chọn Đơn vị nằm cố định trên thanh đầu trang (Topbar)", async () => {
      const topbar = page.getByRole("banner");
      await expect(topbar).toBeVisible();
      // The workspace selector is rendered in the topbar
      await expect(
        topbar
          .getByText("Đơn vị Thử nghiệm E2E")
          .or(topbar.getByRole("combobox")),
      ).toBeVisible();
    });

    await test.step("3. Kiểm tra Sidebar chính gồm đúng 6 mục", async () => {
      const sidebar = page.locator("aside, [data-sidebar='sidebar']").first();
      await expect(sidebar).toBeVisible();

      const expectedItems = [
        "Tổng quan",
        "Kho tri thức",
        "Trợ lý AI",
        "Hội thoại",
        "Tác vụ",
        "Cấu hình",
      ];

      for (const item of expectedItems) {
        await expect(sidebar.getByText(item, { exact: true })).toBeVisible();
      }
    });

    await test.step("4. Điều hướng qua các mục và kiểm tra URL / tiêu đề", async () => {
      const sidebar = page.locator("aside, [data-sidebar='sidebar']").first();

      // Click Kho tri thức
      await sidebar.getByText("Kho tri thức", { exact: true }).click();
      await expect(page).toHaveURL(/.*knowledge/);
      await expect(
        page.getByRole("heading", { name: "Kho tri thức" }),
      ).toBeVisible();

      // Click Trợ lý AI
      await sidebar.getByText("Trợ lý AI", { exact: true }).click();
      await expect(page).toHaveURL(/.*assistants/);

      // Click Hội thoại
      await sidebar.getByText("Hội thoại", { exact: true }).click();
      await expect(page).toHaveURL(/.*conversations/);

      // Click Tác vụ
      await sidebar.getByText("Tác vụ", { exact: true }).click();
      await expect(page).toHaveURL(/.*operations/);

      // Click Cấu hình
      await sidebar.getByText("Cấu hình", { exact: true }).click();
      await expect(page).toHaveURL(/.*settings/);
      await expect(
        page.getByRole("heading", { name: /Cấu hình hệ thống/i }),
      ).toBeVisible();
    });

    await test.step("5. Kiểm tra Breadcrumb, Back / Forward và Reload (F5)", async () => {
      // Reload on Cấu hình page keeps state
      await page.reload();
      await expect(page).toHaveURL(/.*settings/);
      await expect(
        page.getByRole("heading", { name: /Cấu hình hệ thống/i }),
      ).toBeVisible();

      // Browser back button returns to Tác vụ
      await page.goBack();
      await expect(page).toHaveURL(/.*operations/);

      // Browser forward returns to Cấu hình
      await page.goForward();
      await expect(page).toHaveURL(/.*settings/);
    });
  });
});
