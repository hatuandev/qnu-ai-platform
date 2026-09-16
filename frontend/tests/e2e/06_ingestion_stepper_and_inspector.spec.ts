import path from "node:path";
import { expect, test } from "@playwright/test";

/**
 * Suite 06: Live Ingestion Stepper Tracker & Rich Chunks Inspector E2E Tests.
 * Verifies:
 * 1. 4-Stage Ingestion Pipeline Progress Tracker (MinIO S3 -> Layout & OCR -> Chunking -> Qdrant Vector Indexing).
 * 2. Rich Document & Chunks Inspector with 3-tab layout (Chunks Matrix, Structured Fact Layer, MinIO Metadata).
 */
test.describe("06. Ingestion Stepper & Rich Chunks Inspector", () => {
  const sampleDocxPath = path.resolve(process.cwd(), "sample_de_thi_bloom_2026.docx");

  test("TC-STEP-01: Live Ingestion Stepper tracks 4 pipeline stages to 100% completion", async ({
    page,
  }) => {
    await page.goto("/knowledge/collections/col_question_bank");
    await page.waitForLoadState("domcontentloaded");

    // Open Ingestion Form Modal
    const openModalBtn = page.getByRole("button", { name: /Nạp Văn Bản Mới/i });
    await openModalBtn.click();
    await page.waitForTimeout(300);

    // Upload Word file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(sampleDocxPath);

    // Click submit button
    const submitBtn = page.getByRole("button", { name: /Khởi Động Pipeline Nạp/i });
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // Verify Live Ingestion Stepper Modal appears
    const stepperModal = page.locator("text=Tiến Trình Pipeline Bóc Tách Tri Thức");
    await expect(stepperModal).toBeVisible();

    // Verify stages exist
    await expect(page.locator("text=Chặng 1: Lưu Trữ Tệp Gốc MinIO S3")).toBeVisible();
    await expect(page.locator("text=Chặng 2: Phân Tích Cấu Trúc & Bóc Tách OCR")).toBeVisible();
    await expect(page.locator("text=Chặng 3: Chuẩn Hóa & Phân Mảnh (Chunking)")).toBeVisible();
    await expect(page.locator("text=Chặng 4: Vector Indexing & Cơ Sở Dữ Liệu FTS")).toBeVisible();

    // Wait for 100% completion badge
    const doneBadge = page.locator("text=HOÀN TẤT 100%");
    await expect(doneBadge).toBeVisible({ timeout: 10000 });

    // Take screenshot of completed stepper
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/live_ingestion_stepper_completed.png",
      fullPage: false,
    });

    // Click finish button to close modal
    const finishBtn = page.getByRole("button", { name: /Xem Tài Liệu Trong Bảng/i });
    await expect(finishBtn).toBeEnabled();
    await finishBtn.click();
    await page.waitForTimeout(500);

    // Verify stepper modal closed
    await expect(stepperModal).not.toBeVisible();
  });

  test("TC-STEP-02: Rich Document Chunks Inspector displays 3-tab layout and copies chunk text", async ({
    page,
  }) => {
    await page.goto("/knowledge/collections/col_question_bank");
    await page.waitForLoadState("domcontentloaded");

    // Click "Chunks" button in document table row
    const chunksBtn = page
      .locator("button")
      .filter({ hasText: /Chunks/i })
      .first();
    await expect(chunksBtn).toBeVisible();
    await chunksBtn.click();
    await page.waitForTimeout(300);

    // Verify Rich Inspector Dialog is open
    const inspectorTitle = page.locator("text=Trình Đối Soát Bóc Tách & Chunks Inspector");
    await expect(inspectorTitle).toBeVisible();

    // Tab 1: Verify Chunks Matrix
    await expect(page.locator("text=Chunk #01")).toBeVisible();
    await expect(page.locator("text=Chunk #02")).toBeVisible();
    await expect(page.locator("text=Chunk #03")).toBeVisible();

    // Test Copy Chunk button
    const copyBtn = page
      .locator("button")
      .filter({ hasText: /Sao chép/i })
      .first();
    await copyBtn.click();
    await expect(page.locator("text=Đã sao chép").first()).toBeVisible({ timeout: 3000 });

    // Take screenshot of Tab 1: Chunks Matrix
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/rich_chunks_inspector_tab1.png",
      fullPage: false,
    });

    // Tab 2: Click Structured Fact Layer Tab
    const factTab = page.getByRole("tab", { name: /Lớp Dữ Liệu Số Hóa/i });
    await factTab.click();
    await page.waitForTimeout(200);

    // Verify Fact Table rendered
    await expect(page.locator("text=Công Nghệ Thông Tin")).toBeVisible();
    await expect(page.locator("text=25.50")).toBeVisible();

    // Take screenshot of Tab 2: Fact Layer
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/rich_chunks_inspector_tab2_facts.png",
      fullPage: false,
    });

    // Tab 3: Click MinIO & Vector Metadata Tab
    const metaTab = page.getByRole("tab", { name: /Siêu Dữ Liệu/i });
    await metaTab.click();
    await page.waitForTimeout(200);

    // Verify Metadata details
    await expect(page.locator("text=s3://qnu-knowledge-raw").first()).toBeVisible();
    await expect(page.locator("text=1024D Cosine")).toBeVisible();

    // Take screenshot of Tab 3: MinIO & Technical Metadata
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/rich_chunks_inspector_tab3_metadata.png",
      fullPage: false,
    });
  });
});
