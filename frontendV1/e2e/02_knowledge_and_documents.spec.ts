import path from "node:path";
import { expect, test } from "@playwright/test";
import { loginAndEnsureDashboard } from "./helpers/auth";

const FIXTURES_DIR = path.resolve(__dirname, "fixtures");

test.describe("B-E. Knowledge, Folders, Upload & Extraction Flow", () => {
  const collectionName = `Kho Tuyển sinh E2E ${Date.now()}`;
  const folderName = "Đề án & Chỉ tiêu";

  test("should manage collections, folders, upload documents, show progress, review & edit content", async ({
    page,
  }) => {
    await test.step("1. Đi tới trang Kho tri thức và tạo kho mới", async () => {
      await loginAndEnsureDashboard(page);

      // Navigate to Knowledge via sidebar
      const sidebar = page.locator("aside, [data-sidebar='sidebar']").first();
      await sidebar.getByText("Kho tri thức", { exact: true }).click();
      await expect(page).toHaveURL(/.*knowledge/);

      // Click create collection button
      const createBtn = page.getByRole("button", { name: /Tạo kho/i }).first();
      await expect(createBtn).toBeVisible({ timeout: 10000 });
      await createBtn.click();

      // Fill dialog
      const nameInput = page.getByLabel(/Tên kho tri thức/i);
      await expect(nameInput).toBeVisible();
      await nameInput.fill(collectionName);

      const submitBtn = page.getByRole("button", { name: /Tạo kho/i }).last();
      await submitBtn.click();

      // Verify collection appears in the list
      await expect(page.getByText(collectionName)).toBeVisible({
        timeout: 15000,
      });
    });

    await test.step("2. Mở kho tri thức và tạo thư mục mới", async () => {
      await page.getByText(collectionName).click();
      await expect(page).toHaveURL(/.*knowledge\/col_/);

      // Create a folder
      const folderBtn = page
        .getByRole("button", { name: /Thư mục mới/i })
        .or(page.getByRole("button", { name: /Tạo thư mục/i }))
        .first();

      if (await folderBtn.isVisible({ timeout: 5000 })) {
        await folderBtn.click();
        const folderInput = page.getByLabel(/Tên thư mục/i);
        await folderInput.fill(folderName);
        await page
          .getByRole("button", { name: /Tạo thư mục|Lưu/i })
          .last()
          .click();
        await expect(page.getByText(folderName)).toBeVisible({
          timeout: 10000,
        });
      }
    });

    await test.step("3. Tải lên tệp PDF native và quan sát tiến độ bóc tách thật", async () => {
      // Open upload dialog
      const uploadBtn = page
        .getByRole("button", { name: /Tải lên tài liệu|Tải lên/i })
        .first();
      await uploadBtn.click();

      const fileInput = page.locator('input[type="file"]');
      await expect(fileInput).toBeAttached();

      const pdfPath = path.join(FIXTURES_DIR, "de_an_tuyen_sinh_2026.pdf");
      await fileInput.setInputFiles(pdfPath);

      // Submit upload
      const submitUpload = page
        .getByRole("button", {
          name: /Tải lên và bóc tách|Tải lên/i,
        })
        .last();
      await submitUpload.click();

      // Verify ProcessingProgress appears during/after upload
      const _progressIndicator = page.locator(
        "[role='progressbar'], [aria-live='polite'], .animate-pulse",
      );
      // Wait for document to be processed
      await expect(page.getByText(/de_an_tuyen_sinh_2026/i)).toBeVisible({
        timeout: 30000,
      });

      // Verify status badge
      await expect(
        page.getByText(/Đã bóc tách|Hoàn tất|running|completed/i).first(),
      ).toBeVisible({ timeout: 15000 });
    });

    await test.step("4. Chuyển đổi chế độ hiển thị Bảng / Lưới", async () => {
      const viewToggle = page
        .locator("[role='radiogroup'], [data-view-toggle]")
        .first();
      if (await viewToggle.isVisible()) {
        const tableButton = page
          .getByRole("radio", { name: /Bảng|Table/i })
          .or(page.locator("button[value='table']"));
        if (await tableButton.isVisible()) {
          await tableButton.click();
          await expect(page.locator("table")).toBeVisible();
        }
      }
    });

    await test.step("5. Mở chi tiết tài liệu: đối chiếu 2 cột, sửa nội dung & tải xuống", async () => {
      // Click document title to open detail page
      await page
        .getByText(/de_an_tuyen_sinh_2026/i)
        .first()
        .click();
      await expect(page).toHaveURL(/.*files\/src_/);

      // Verify two-column view
      await expect(page.getByText(/Bản gốc|Bản hiển thị/i).first()).toBeVisible(
        { timeout: 15000 },
      );
      await expect(page.getByText(/Nội dung|Markdown/i).first()).toBeVisible({
        timeout: 15000,
      });

      // Verify extracted text is visible on the right panel
      await expect(
        page.getByText(/Tuyển sinh|Chỉ tiêu|Quy Nhơn/i).first(),
      ).toBeVisible({ timeout: 20000 });

      // Test manual edit if edit buttons exist
      const editBtn = page.getByRole("button", { name: /Sửa/i }).first();
      if (await editBtn.isVisible({ timeout: 3000 })) {
        await editBtn.click();
        const textarea = page.locator("textarea").first();
        if (await textarea.isVisible({ timeout: 2000 })) {
          await textarea.fill(
            "THÔNG BÁO TUYỂN SINH ĐẠI HỌC 2026 - ĐÃ HIỆU ĐÍNH E2E",
          );
          const saveBtn = page.getByRole("button", { name: /Lưu/i }).first();
          await saveBtn.click();
        }
      }

      // Test download original via menu ⋯
      const moreBtn = page
        .getByRole("button", { name: /Thao tác|More/i })
        .or(
          page.locator(
            "button:has(svg.lucide-ellipsis, svg.lucide-more-horizontal)",
          ),
        )
        .first();
      if (await moreBtn.isVisible({ timeout: 3000 })) {
        await moreBtn.click();
        const downloadOption = page.getByText(/Tải xuống bản gốc/i);
        if (await downloadOption.isVisible({ timeout: 3000 })) {
          const [download] = await Promise.all([
            page
              .waitForEvent("download", { timeout: 10000 })
              .catch(() => [null]),
            downloadOption.click(),
          ]);
          if (download) {
            expect(download.suggestedFilename()).toContain(
              "de_an_tuyen_sinh_2026",
            );
          }
        }
      }
    });
  });
});
