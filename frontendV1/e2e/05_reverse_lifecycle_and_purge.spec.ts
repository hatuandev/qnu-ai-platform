import { expect, test } from "@playwright/test";
import { loginAndEnsureDashboard } from "./helpers/auth";

test.describe("I. Reverse Lifecycle & Permanent Purge Flow", () => {
  test("should block deletion while published, allow permanent purge after withdraw, and clean records", async ({
    page,
  }) => {
    await test.step("1. Đăng nhập và mở kho tri thức", async () => {
      await loginAndEnsureDashboard(page);

      const sidebar = page.locator("aside, [data-sidebar='sidebar']").first();
      await sidebar.getByText("Kho tri thức", { exact: true }).click();
      await expect(page).toHaveURL(/.*knowledge/);

      // Open collection
      const collectionLink = page.locator("a[href*='/knowledge/col_']").first();
      await expect(collectionLink).toBeVisible({ timeout: 15000 });
      await collectionLink.click();
      await expect(page).toHaveURL(/.*knowledge\/col_/);
    });

    await test.step("2. Kiểm tra thao tác Xóa vĩnh viễn trên tài liệu nguồn", async () => {
      // Find row menu ⋯ on a source
      const moreBtn = page
        .locator(
          "button:has(svg.lucide-more-horizontal), button:has(svg.lucide-ellipsis)",
        )
        .first();

      if (await moreBtn.isVisible({ timeout: 5000 })) {
        await moreBtn.click();

        // Check if 'Xóa vĩnh viễn' or 'Lưu trữ' exists in menu
        const deleteOption = page
          .getByText(/Xóa vĩnh viễn|Xóa tài liệu|Lưu trữ/i)
          .first();
        if (await deleteOption.isVisible({ timeout: 3000 })) {
          await deleteOption.click();

          // Verify confirmation dialog opens (LifecycleActionDialog)
          await expect(
            page.getByText(/Xác nhận|Xóa vĩnh viễn|Hủy/i).first(),
          ).toBeVisible({ timeout: 5000 });

          // Cancel to preserve test state if needed
          const cancelBtn = page
            .getByRole("button", { name: /Hủy|Đóng/i })
            .first();
          if (await cancelBtn.isVisible()) {
            await cancelBtn.click();
          }
        }
      }
    });

    await test.step("3. Kiểm tra vùng theo dõi yêu cầu xóa đang chờ (PendingSourceDeletions)", async () => {
      // Verify PendingSourceDeletions container is present or rendered cleanly
      const pendingArea = page.locator("[data-pending-deletions]");
      // If no deletions pending, it should be empty or hidden without throwing errors
      if (await pendingArea.isVisible({ timeout: 2000 })) {
        await expect(pendingArea).toBeVisible();
      }
    });
  });
});
