import { expect, test } from "@playwright/test";

/**
 * Suite 09: Knowledge Master-Detail & Full-Screen Split-Pane Ingestion Studio E2E Tests.
 * Verifies:
 * 1. Master View (/knowledge): Card Grid 3-columns, BGE-M3 chips, summary metric badge, background tasks tab.
 * 2. Dedicated Detail View (/knowledge/collections/:id): 3 Sub-tabs (Documents, Tasks, Playground).
 * 3. Dedicated Ingestion Form View: Centered card container, OCR engines, legal priority badge (10/10).
 * 4. Full-Screen Split-Pane Studio:
 *    - Left pane: Multi-color Bounding Boxes (text, table, stamp), filter pills, page synchronization.
 *    - Right pane: Markdown view, "Sửa tay" (Manual Edit) in-place textarea mode.
 *    - Tab "Bố cục & Khối": Regions layout analysis tree for scanned documents.
 *    - Commit to Vector DB with confirmation.
 */
test.describe("09. Knowledge Master-Detail & Full-Screen Ingestion Studio", () => {
  test("TC-INGEST-01: Verifies Knowledge Master View with 3-column card grid and background tasks tab", async ({
    page,
  }) => {
    await page.goto("/knowledge");
    await page.waitForLoadState("domcontentloaded");

    // 1. Verify Page Header & Summary Badge
    await expect(page.locator("text=Kho Tri thức & Vector Collections")).toBeVisible();
    await expect(page.getByText(/5 Kho.*Văn bản.*Chunks/)).toBeVisible();

    // 2. Verify 3-column Card Grid items (offline seed catalog names)
    await expect(page.locator("text=Kho Tri thức Tuyển sinh Đại học")).toBeVisible();
    await expect(page.locator("text=Kho Mẫu Văn bản & Hành chính")).toBeVisible();
    await expect(page.locator("text=Kho Quy chế & Quy định Đào tạo")).toBeVisible();
    await expect(page.locator("text=BAAI/bge-m3 (1024-dim)").first()).toBeVisible();

    // Take screenshot of Master Overview
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/knowledge_master_grid_overview.png",
      fullPage: false,
    });

    // 3. Switch to "Tác vụ Nền & Bóc tách" tab
    const tasksTabBtn = page.getByRole("button", { name: /Tác vụ Nền & Bóc tách/i });
    await expect(tasksTabBtn).toBeVisible();
    await tasksTabBtn.click();
    await page.waitForTimeout(300);

    // Verify background task list
    await expect(
      page.locator("text=Ingestion Đề án Tuyển sinh Đại học Chính quy 2026")
    ).toBeVisible();
    await expect(page.locator("text=celery_worker_gpu_01").first()).toBeVisible();
    await expect(page.locator("text=100%").first()).toBeVisible();
  });

  test("TC-INGEST-02: Verifies Dedicated Detail View with 3 sub-tabs and Ingest Form", async ({
    page,
  }) => {
    await page.goto("/knowledge/collections/col_admissions");
    await page.waitForLoadState("domcontentloaded");

    // 1. Verify Detail Page Header
    await expect(page.locator("h1:has-text('Kho Tri thức Tuyển sinh Đại học')")).toBeVisible();
    await expect(page.locator("text=admissions").first()).toBeVisible();
    await expect(page.locator("text=BAAI/bge-m3 (1024-dim)").first()).toBeVisible();

    // 2. Verify 3 Sub-tabs
    await expect(page.getByRole("tab", { name: /Danh mục Tài liệu/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /Tiến trình & Lịch sử Tác vụ/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /Hỏi Thử Nghiệm trong Kho/i })).toBeVisible();

    // 3. Verify Document Row
    await expect(page.locator("text=Thong tin tuyen sinh dai hoc 2026 Lan2 1 (1)")).toBeVisible();
    await expect(page.getByRole("cell", { name: /10 chunks/i })).toBeVisible();
    await expect(page.getByRole("cell").getByText("Ưu tiên Cao (Cốt lõi)").first()).toBeVisible();

    // Take screenshot of Collection Detail Page
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/knowledge_collection_detail_3tabs.png",
      fullPage: false,
    });

    // 4. Click "+ Nạp tài liệu" button to open Dedicated Ingest Form
    const ingestBtn = page.getByRole("button", { name: /\+ Nạp tài liệu/i });
    await expect(ingestBtn).toBeVisible();
    await ingestBtn.click();
    await page.waitForTimeout(300);

    // 5. Verify Ingest Form fields
    await expect(page.locator("text=Nạp & Bóc tách Tài liệu vào Kho Tri thức")).toBeVisible();
    await expect(page.locator("text=Tiêu đề / Số hiệu Văn bản")).toBeVisible();
    await expect(page.locator("text=Cấu hình Bộ máy OCR")).toBeVisible();
    await expect(page.locator("text=Ưu tiên Cao (Cốt lõi) (x100)")).toBeVisible();

    // Take screenshot of Document Ingest Form
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/knowledge_document_ingest_form.png",
      fullPage: false,
    });
  });

  test("TC-INGEST-03: Full-Screen Split-Pane Studio with Bounding Boxes, Regions, Manual Edit and Vector DB Commit", async ({
    page,
  }) => {
    // Navigate directly into Studio Verification view
    await page.goto("/knowledge/collections/col_admissions/verify/doc_ts_2026");
    await page.waitForLoadState("domcontentloaded");

    // 1. Verify Desktop-grade Topbar
    await expect(page.getByRole("button", { name: /Cấu hình lại/i })).toBeVisible();
    await expect(
      page.locator("text=Thông tin tuyển sinh đại học 2026 Lan2 1").first()
    ).toBeVisible();
    await expect(page.locator("text=14 Trang").first()).toBeVisible();
    await expect(page.locator("text=docling-tableformer-local")).toBeVisible();
    await expect(page.getByText(/21[.,]870.*37 Chunks/)).toBeVisible();

    // 2. Verify Left Pane: Page 1 with Bounding Box & Scanned Image
    await expect(page.locator("img[alt='Trang scan 1']")).toBeVisible();
    await expect(page.locator("text=THÔNG BÁO").first()).toBeVisible();
    await expect(page.locator("text=ĐẠI HỌC QUY NHƠN").first()).toBeVisible();
    await expect(page.getByText("Trang 1 / 14", { exact: true })).toBeVisible();

    // Take screenshot of Studio Page 1
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/knowledge_split_pane_studio_p1.png",
      fullPage: false,
    });

    // 3. Flip to Page 2
    const nextPageBtn = page.getByRole("button", { name: ">" });
    await expect(nextPageBtn).toBeVisible();
    await nextPageBtn.click();
    await page.waitForTimeout(300);

    // Verify Page 2 content, TableFormer Table Bounding Box & Actual Scanned Image
    await expect(page.locator("img[alt='Trang scan 2']")).toBeVisible();
    await expect(page.getByText("Trang 2 / 14", { exact: true })).toBeVisible();
    await expect(page.locator("text=Phương thức 1 (PT1 - mã 100)").first()).toBeVisible();
    await expect(page.locator("table")).toBeVisible();
    await expect(page.locator("text=Quản lý giáo dục").first()).toBeVisible();
    await expect(page.locator("text=7140114").first()).toBeVisible();

    // Take screenshot of Studio Page 2 with Table
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/knowledge_split_pane_studio_p2_table.png",
      fullPage: false,
    });

    // 3b. Flip to Page 3: Verify Page 3 has scanned image and Sư phạm Toán học
    await nextPageBtn.click();
    await page.waitForTimeout(300);
    await expect(page.locator("img[alt='Trang scan 3']")).toBeVisible();
    await expect(page.getByText("Trang 3 / 14", { exact: true })).toBeVisible();
    await expect(page.locator("text=Sư phạm Toán học").first()).toBeVisible();

    // Return to Page 2 for Regions test
    const prevPageBtn = page.getByRole("button", { name: "<" });
    await prevPageBtn.click();
    await page.waitForTimeout(300);

    // 4. Switch to "Bố cục & Khối" tab (Regions Layout Inspector for Scanned docs)
    const regionsTab = page.getByRole("tab", { name: /Bố cục & Khối/i });
    await expect(regionsTab).toBeVisible();
    await regionsTab.click();
    await page.waitForTimeout(300);

    // Verify Layout & Regions Inspector
    await expect(page.locator("text=Phân Đoạn Vùng Bố Cục (Layout & Regions)")).toBeVisible();
    await expect(page.locator("text=4. Các ngành, tổ hợp môn xét tuyển").first()).toBeVisible();
    await expect(page.locator("text=Độ tin cậy OCR: 99%")).toBeVisible();

    // Take screenshot of Regions Inspector
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/knowledge_regions_scan_inspector.png",
      fullPage: false,
    });

    // 5. Switch back to Markdown tab & test "Sửa tay" (Manual Edit)
    const markdownTab = page.getByRole("tab", { name: /Markdown/i });
    await markdownTab.click();
    await page.waitForTimeout(200);

    const editBtn = page.getByRole("button", { name: /Sửa tay/i });
    await expect(editBtn).toBeVisible();
    await editBtn.click();
    await page.waitForTimeout(200);

    // Verify Textarea mode
    const textarea = page.locator("textarea");
    await expect(textarea).toBeVisible();
    await expect(page.locator("text=Chế độ Sửa tay (Human-in-the-loop)")).toBeVisible();

    // Save manual edit
    const saveEditBtn = page.getByRole("button", { name: /Lưu sửa/i });
    await saveEditBtn.click();
    await page.waitForTimeout(200);

    // 6. Click "Xác nhận & Nạp vào Vector DB"
    const commitBtn = page.getByRole("button", { name: /Xác nhận & Nạp vào Vector DB/i });
    await expect(commitBtn).toBeVisible();
    await commitBtn.click();

    // Verify Success Banner
    await expect(page.locator("text=Đã nạp Vector DB thành công!")).toBeVisible({ timeout: 5000 });
  });
});
