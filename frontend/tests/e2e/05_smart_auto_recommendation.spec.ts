import path from "node:path";
import { expect, test } from "@playwright/test";

/**
 * Suite 05: Smart Auto-Recommendation Engine E2E Tests.
 * Verifies intelligent file inspection and automatic model selection (Docling / Mistral OCR / Native)
 * when uploading Word, PDF, and TXT files into the Knowledge Base.
 */
test.describe("05. Smart Auto-Recommendation Engine", () => {
  const sampleDocxPath = path.resolve(process.cwd(), "sample_de_thi_bloom_2026.docx");
  const samplePdfPath = path.resolve(process.cwd(), "sample_quyet_dinh_tuyen_sinh_2026.pdf");
  const sampleTxtPath = path.resolve(process.cwd(), "sample_de_an_2026.txt");

  test("TC-SMART-01: Auto-recommends Docling TableFormer and ClauseBasedChunker for Word .docx files", async ({
    page,
  }) => {
    await page.goto("/knowledge/collections/col_question_bank");
    await page.waitForLoadState("domcontentloaded");

    // Open Ingestion Modal
    const openModalBtn = page.getByRole("button", { name: /Nạp Văn Bản Mới/i });
    await expect(openModalBtn).toBeVisible();
    await openModalBtn.click();
    await page.waitForTimeout(300);

    // Verify modal is open
    const modalTitle = page.getByRole("heading", { name: /Nạp Văn Bản Vào Bộ Sưu Tập/i });
    await expect(modalTitle).toBeVisible();

    // Upload Word .docx file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(sampleDocxPath);

    // Verify file is selected
    await expect(page.locator("text=sample_de_thi_bloom_2026.docx")).toBeVisible();

    // Verify document title auto-filled
    const titleInput = page.getByPlaceholder(/Ví dụ: Đề án/i);
    await expect(titleInput).toHaveValue(/sample de thi bloom 2026/i);

    // Verify Smart Recommendation Banner appears
    const banner = page.locator("text=Đề Xuất Tối Ưu Cho Tệp Word (.docx)");
    await expect(banner).toBeVisible();

    const badge = page.locator("text=Tự Động Đề Xuất");
    await expect(badge).toBeVisible();

    // Verify OCR dropdown auto-selected Docling
    const ocrSelect = page.locator("select").first();
    await expect(ocrSelect).not.toHaveText(/\(không có provider/i);
    const selectedOcrText = await ocrSelect.evaluate(
      (el: HTMLSelectElement) => el.options[el.selectedIndex]?.text
    );
    expect(selectedOcrText.toLowerCase()).toContain("docling");

    // Verify Chunking Strategy radio selected ClauseBasedChunker
    const clauseRadio = page.locator('input[type="radio"][value="ClauseBasedChunker"]');
    await expect(clauseRadio).toBeChecked();

    // Take screenshot of Word recommendation
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/smart_recommendation_word.png",
      fullPage: false,
    });
  });

  test("TC-SMART-02: Auto-recommends Mistral OCR and Fast-path Inspector for PDF files", async ({
    page,
  }) => {
    await page.goto("/knowledge/collections/col_question_bank");
    await page.waitForLoadState("domcontentloaded");

    // Open Ingestion Modal
    const openModalBtn = page.getByRole("button", { name: /Nạp Văn Bản Mới/i });
    await expect(openModalBtn).toBeVisible();
    await openModalBtn.click();
    await page.waitForTimeout(300);

    // Upload PDF file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(samplePdfPath);

    // Verify Smart Recommendation Banner updates for PDF
    const banner = page.locator("text=Đề Xuất Cho Văn Bản Adobe PDF");
    await expect(banner).toBeVisible();

    const badge = page.locator("text=Fast-path + Cloud OCR");
    await expect(badge).toBeVisible();

    // Verify OCR dropdown auto-selected Mistral OCR
    const ocrSelect = page.locator("select").first();
    await expect(ocrSelect).not.toHaveText(/\(không có provider/i);
    const selectedOcrText = await ocrSelect.evaluate(
      (el: HTMLSelectElement) => el.options[el.selectedIndex]?.text
    );
    expect(selectedOcrText.toLowerCase()).toContain("mistral");

    // Take screenshot of PDF recommendation
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/smart_recommendation_pdf.png",
      fullPage: false,
    });
  });

  test("TC-SMART-03: Full Ingestion workflow with Smart Recommendation", async ({ page }) => {
    await page.goto("/knowledge/collections/col_question_bank");
    await page.waitForLoadState("domcontentloaded");

    // Open Ingestion Modal
    const openModalBtn = page.getByRole("button", { name: /Nạp Văn Bản Mới/i });
    await expect(openModalBtn).toBeVisible();
    await openModalBtn.click();
    await page.waitForTimeout(300);

    // Upload Text file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(sampleTxtPath);

    // Verify Banner for TXT
    const banner = page.locator("text=Đề Xuất Cho Văn Bản Thuần");
    await expect(banner).toBeVisible();

    // Submit form
    const submitBtn = page.getByRole("button", { name: /Khởi Động Pipeline Nạp/i });
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // Wait for Live Stepper to complete 100%
    const completedBadge = page.locator("text=HOÀN TẤT 100%");
    await expect(completedBadge).toBeVisible({ timeout: 10000 });

    // Click "Xem Tài Liệu Trong Bảng" button
    const finishBtn = page.getByRole("button", { name: /Xem Tài Liệu Trong Bảng/i });
    await expect(finishBtn).toBeVisible();
    await finishBtn.click();
    await page.waitForTimeout(500);

    // Verify new document appears in table
    const docRow = page.locator("td").filter({ hasText: /sample de an 2026/i });
    await expect(docRow.first()).toBeVisible({ timeout: 5000 });

    // Take screenshot of final ingested documents list
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/smart_ingestion_success.png",
      fullPage: false,
    });
  });
});
