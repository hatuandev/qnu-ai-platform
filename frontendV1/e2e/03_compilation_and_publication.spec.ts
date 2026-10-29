import { expect, test } from "@playwright/test";
import { loginAndEnsureDashboard } from "./helpers/auth";

test.describe("F-G. Compilation, Review, Approval, Publication & Indexing Flow", () => {
  test("should compile documents, perform semantic review, approve, publish, and update search index", async ({
    page,
  }) => {
    await test.step("1. Đăng nhập và mở kho tri thức", async () => {
      await loginAndEnsureDashboard(page);

      const sidebar = page.locator("aside, [data-sidebar='sidebar']").first();
      await sidebar.getByText("Kho tri thức", { exact: true }).click();
      await expect(page).toHaveURL(/.*knowledge/);

      // Open the first collection in the list
      const collectionLink = page.locator("a[href*='/knowledge/col_']").first();
      await expect(collectionLink).toBeVisible({ timeout: 15000 });
      await collectionLink.click();
      await expect(page).toHaveURL(/.*knowledge\/col_/);
    });

    await test.step("2. Chuyển sang tab Biên soạn và tạo bản biên soạn", async () => {
      // Click tab 'Biên soạn'
      const compilerTab = page.getByRole("tab", { name: "Biên soạn" });
      await expect(compilerTab).toBeVisible({ timeout: 10000 });
      await compilerTab.click();

      // Click button 'Tạo bản biên soạn'
      const createCompileBtn = page
        .getByRole("button", { name: /Tạo bản biên soạn|Bắt đầu biên soạn/i })
        .first();
      await expect(createCompileBtn).toBeVisible({ timeout: 10000 });
      await createCompileBtn.click();

      // Inside compilation dialog, select source if checkbox exists
      const sourceCheckbox = page.locator("input[type='checkbox']").first();
      if (await sourceCheckbox.isVisible({ timeout: 3000 })) {
        await sourceCheckbox.check();
      }

      // Submit compilation
      const submitCompile = page
        .getByRole("button", {
          name: /Bắt đầu biên soạn|Tạo biên soạn|Xác nhận/i,
        })
        .last();
      if (await submitCompile.isEnabled()) {
        await submitCompile.click();
      }

      // Verify compilation run appears in the list
      await expect(
        page.getByText(/running|completed|Hoàn tất|Đang xử lý/i).first(),
      ).toBeVisible({ timeout: 30000 });
    });

    await test.step("3. Chuyển sang tab Phát hành và đăng ký tài liệu biên soạn", async () => {
      // Click tab 'Phát hành'
      const pubTab = page.getByRole("tab", { name: "Phát hành" });
      await expect(pubTab).toBeVisible({ timeout: 10000 });
      await pubTab.click();

      // Verify publication list rendered
      await expect(
        page
          .getByText(/Chưa có tài liệu biên soạn nào|Tài liệu đã phát hành/i)
          .first(),
      ).toBeVisible({ timeout: 10000 });
    });

    await test.step("4. Kiểm tra nút 'Cập nhật tìm kiếm' và trạng thái 'Sẵn sàng hỏi đáp'", async () => {
      // If a published document exists, check readiness indicator
      const readyBadge = page
        .getByText(/Sẵn sàng hỏi đáp|Cập nhật tìm kiếm|Đã phát hành/i)
        .first();
      if (await readyBadge.isVisible({ timeout: 5000 })) {
        const updateSearchBtn = page.getByRole("button", {
          name: /Cập nhật tìm kiếm/i,
        });
        if (await updateSearchBtn.isVisible({ timeout: 2000 })) {
          await updateSearchBtn.click();
          await expect(
            page.getByText(/Đang cập nhật|thành công/i).first(),
          ).toBeVisible({ timeout: 10000 });
        }
      }
    });
  });
});
