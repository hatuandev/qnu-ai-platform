import { test, expect } from "@playwright/test";

/**
 * Suite 02: Chat Studio & AI Assistants E2E Tests.
 * Tests assistant switching, quick prompts, message sending, and chat components.
 */

test.describe("02. Chat Studio & AI Suite", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/chat");
    await page.waitForLoadState("domcontentloaded");
  });

  test("TC-CHAT-01: Chat Studio renders default Admissions assistant and input area", async ({ page }) => {
    // Check header info
    const heading = page.locator("h1, h2, span").filter({ hasText: "Trợ lý Tuyển sinh QNU" }).first();
    await expect(heading).toBeVisible();

    // Textarea input should be ready
    const textarea = page.locator('textarea[placeholder*="Nhắn tin với"]');
    await expect(textarea).toBeVisible();

    // Quick prompts should be available
    const quickPrompts = page.locator("button").filter({ hasText: "Điểm chuẩn ngành" });
    await expect(quickPrompts.first()).toBeVisible();
  });

  test("TC-CHAT-02: Switching between 5 Assistants updates the active assistant", async ({ page }) => {
    // Click Regulations assistant button in the left list
    const regulationsButton = page.locator("button").filter({ hasText: "Trợ lý Quy chế Học vụ" }).first();
    await regulationsButton.click();

    // Check textarea placeholder updated
    const textarea = page.locator('textarea[placeholder*="Quy chế Học vụ"]');
    await expect(textarea).toBeVisible();

    // Switch to Library assistant
    const libraryButton = page.locator("button").filter({ hasText: "Trợ lý Thư viện Số" }).first();
    await libraryButton.click();
    await expect(page.locator('textarea[placeholder*="Thư viện"]')).toBeVisible();
  });

  test("TC-CHAT-03: Typing a question enables the Send button and clicking sends message", async ({ page }) => {
    const textarea = page.locator('textarea[placeholder*="Nhắn tin với"]');
    const sendButton = page.locator("button").filter({ hasText: "Gửi" });

    // Initially send button is disabled when empty
    await expect(sendButton).toBeDisabled();

    // Fill message
    await textarea.fill("Cho tôi hỏi về quy chế học bổng khuyến khích học tập?");
    await expect(sendButton).toBeEnabled();

    // Send
    await sendButton.click();

    // User message bubble should appear in the chat stream
    const userMessage = page.locator("text=Cho tôi hỏi về quy chế học bổng khuyến khích học tập?");
    await expect(userMessage).toBeVisible({ timeout: 5000 });
  });

  test("TC-CHAT-04: Clicking a quick prompt automatically sends the question", async ({ page }) => {
    const quickPrompt = page.locator("button").filter({ hasText: "Điểm chuẩn ngành Công nghệ thông tin" }).first();
    await expect(quickPrompt).toBeVisible();

    await quickPrompt.click();

    // Message should be sent and displayed in chat history
    const messageInChat = page.locator("text=Điểm chuẩn ngành Công nghệ thông tin");
    await expect(messageInChat.first()).toBeVisible({ timeout: 5000 });
  });
});
