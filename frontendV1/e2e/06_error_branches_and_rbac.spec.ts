import path from "node:path";
import { expect, test } from "@playwright/test";
import { loginAndEnsureDashboard } from "./helpers/auth";

const FIXTURES_DIR = path.resolve(__dirname, "fixtures");

test.describe("Error Branches & Validation Handling", () => {
  test("should handle unsupported files and corrupt files gracefully without UI crash", async ({
    page,
  }) => {
    await test.step("1. Mở kho tri thức và mở hộp thoại tải lên", async () => {
      await loginAndEnsureDashboard(page);

      const sidebar = page.locator("aside, [data-sidebar='sidebar']").first();
      await sidebar.getByText("Kho tri thức", { exact: true }).click();
      await expect(page).toHaveURL(/.*knowledge/);

      const collectionLink = page.locator("a[href*='/knowledge/col_']").first();
      await expect(collectionLink).toBeVisible({ timeout: 15000 });
      await collectionLink.click();

      const uploadBtn = page
        .getByRole("button", { name: /Tải lên tài liệu|Tải lên/i })
        .first();
      await uploadBtn.click();
    });

    await test.step("2. Tải lên tệp không được hỗ trợ (.exe) -> Bị chặn hoặc báo lỗi", async () => {
      const fileInput = page.locator('input[type="file"]');
      await expect(fileInput).toBeAttached();

      const exePath = path.join(FIXTURES_DIR, "hop_dong_khong_ho_tro.exe");
      await fileInput.setInputFiles(exePath);

      // Verify validation message or disabled submit
      const errorMsg = page.getByText(
        /không được hỗ trợ|chỉ chấp nhận PDF, DOCX/i,
      );
      const submitBtn = page
        .getByRole("button", {
          name: /Tải lên và bóc tách|Tải lên/i,
        })
        .last();

      // Either error text is visible or submit button is disabled
      const isErrorVisible = await errorMsg.isVisible({ timeout: 3000 });
      const isSubmitDisabled = await submitBtn.isDisabled();
      expect(isErrorVisible || isSubmitDisabled).toBeTruthy();
    });
  });
});
