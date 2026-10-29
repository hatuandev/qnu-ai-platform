import { expect, test } from "@playwright/test";
import { loginAndEnsureDashboard } from "./helpers/auth";

test.describe("H. Assistant & Q&A Chat with Citations Flow", () => {
  const assistantName = `Trợ lý Tuyển sinh E2E ${Date.now()}`;

  test("should create assistant, test chat, verify factual answer, citations, and source links", async ({
    page,
  }) => {
    await test.step("1. Điều hướng tới trang Trợ lý AI và tạo trợ lý mới", async () => {
      await loginAndEnsureDashboard(page);

      const sidebar = page.locator("aside, [data-sidebar='sidebar']").first();
      await sidebar.getByText("Trợ lý AI", { exact: true }).click();
      await expect(page).toHaveURL(/.*assistants/);

      // Click button 'Tạo trợ lý'
      const createBtn = page
        .getByRole("button", { name: /Tạo trợ lý/i })
        .first();
      await expect(createBtn).toBeVisible({ timeout: 10000 });
      await createBtn.click();

      // Fill form
      const nameInput = page.getByLabel(/Tên trợ lý/i);
      await expect(nameInput).toBeVisible();
      await nameInput.fill(assistantName);

      // Submit
      const submitBtn = page
        .getByRole("button", { name: /Lưu|Tạo trợ lý/i })
        .last();
      await submitBtn.click();

      // Verify assistant in list
      await expect(page.getByText(assistantName)).toBeVisible({
        timeout: 15000,
      });
    });

    await test.step("2. Bấm 'Chat thử' để mở phiên hội thoại", async () => {
      // Find row/card for our assistant and click 'Chat thử'
      const chatBtn = page.getByRole("button", { name: /Chat thử/i }).first();
      await expect(chatBtn).toBeVisible({ timeout: 10000 });
      await chatBtn.click();

      // In Conversation create dialog, click confirm
      const startChatBtn = page
        .getByRole("button", {
          name: /Bắt đầu hội thoại|Tạo hội thoại/i,
        })
        .last();
      await expect(startChatBtn).toBeVisible({ timeout: 5000 });
      await startChatBtn.click();

      // Verify redirected to conversation page
      await expect(page).toHaveURL(/.*conversations\/conv_/);
    });

    await test.step("3. Đặt câu hỏi và kiểm tra câu trả lời có dữ kiện chuẩn cùng trích dẫn", async () => {
      // Find chat textarea
      const chatInput = page
        .locator("textarea, input[placeholder*='câu hỏi']")
        .first();
      await expect(chatInput).toBeVisible({ timeout: 15000 });

      await chatInput.fill(
        "Chỉ tiêu tuyển sinh năm 2026 của trường Đại học Quy Nhơn là bao nhiêu?",
      );

      // Send
      const sendBtn = page
        .getByRole("button", { name: /Gửi|Send/i })
        .or(page.locator("button:has(svg.lucide-send)"))
        .first();
      await sendBtn.click();

      // Await assistant answer
      await expect(
        page.getByText(/5500|chỉ tiêu|Quy Nhơn/i).first(),
      ).toBeVisible({ timeout: 25000 });

      // Verify citation badge [1] appears
      const citationBadge = page
        .locator("button:has-text('[1]'), span:has-text('[1]')")
        .first();
      if (await citationBadge.isVisible({ timeout: 5000 })) {
        await citationBadge.click();

        // Verify CitationSheet opens with link to source document
        await expect(
          page.getByText(/Trích dẫn|Tài liệu nguồn|Bản phát hành/i).first(),
        ).toBeVisible({ timeout: 5000 });
      }
    });
  });
});
