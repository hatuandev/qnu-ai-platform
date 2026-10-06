import { expect, test } from "@playwright/test";

/**
 * Suite 08: Administrative Document & Tool Studio E2E Tests.
 * Verifies:
 * 1. Decree 30/2020/ND-CP Document Formatter & Live Interactive Paper Sheet Preview.
 * 2. Bloom Taxonomies Question Bank Matrix & Excel (.xlsx) Exporter.
 * 3. Live UIS Admissions Data Explorer & Administrative Templates with 1-Click Fill.
 */
test.describe("08. Administrative Document & Tool Studio", () => {
  test("TC-TOOL-01: Formats administrative document under Decree 30 with live paper sheet and exports Word", async ({
    page,
  }) => {
    await page.goto("/tools");
    await page.waitForLoadState("domcontentloaded");

    // 1. Verify Page Header & Tab
    await expect(page.locator("text=Cổng Công Cụ Ngoại Vi & Xuất Bản Biểu Mẫu")).toBeVisible();
    await expect(page.getByRole("tab", { name: /Soạn Thảo Word NĐ 30/i })).toBeVisible();

    // 2. Verify Live Paper Sheet (A4 format)
    const paperPreview = page.getByTestId("nd30-paper-preview");
    await expect(paperPreview).toBeVisible();
    await expect(paperPreview).toContainText("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM");
    await expect(paperPreview).toContainText("Độc lập - Tự do - Hạnh phúc");
    await expect(paperPreview).toContainText("TRƯỜNG ĐẠI HỌC QUY NHƠN");
    await expect(paperPreview).toContainText("TỜ TRÌNH");
    await expect(paperPreview).toContainText("Nơi nhận:");

    // 3. Click "Xuất File Word (.docx)"
    const exportDocxBtn = page.getByRole("button", { name: /Xuất File Word \(\.docx\)/i });
    await expect(exportDocxBtn).toBeVisible();
    await exportDocxBtn.click();

    // 4. Verify success banner
    await expect(
      page.locator("text=Đã kết xuất thành công tệp Word (.docx) chuẩn NĐ 30!")
    ).toBeVisible({ timeout: 5000 });

    // Take screenshot of ND 30 Paper Preview
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/tools_nd30_paper_preview.png",
      fullPage: false,
    });
  });

  test("TC-TOOL-02: Designs Bloom exam matrix with visual distribution bar and exports Excel", async ({
    page,
  }) => {
    await page.goto("/tools");
    await page.waitForLoadState("domcontentloaded");

    // 1. Switch to Bloom Matrix Tab
    const bloomTab = page.getByRole("tab", { name: /Ma Trận Đề Thi Bloom/i });
    await expect(bloomTab).toBeVisible();
    await bloomTab.click();
    await page.waitForTimeout(300);

    // 2. Verify Bloom Table & Distribution Bar
    await expect(
      page.locator("text=Thiết Kế Ma Trận Đề Thi Chuẩn Tư Duy Bloom (4 Cấp Độ)")
    ).toBeVisible();
    await expect(page.locator("text=Biểu Đồ Phân Bổ Tỷ Lệ Cấp Độ Nhận Thức Bloom")).toBeVisible();
    await expect(page.locator("text=Nhận Biết").first()).toBeVisible();
    await expect(page.locator("text=Thông Hiểu").first()).toBeVisible();
    await expect(page.locator("text=Vận Dụng").first()).toBeVisible();
    await expect(page.locator("text=Vận Dụng Cao").first()).toBeVisible();

    // 3. Add a new topic
    const addTopicBtn = page.getByRole("button", { name: /Thêm chủ đề/i });
    await expect(addTopicBtn).toBeVisible();
    await addTopicBtn.click();
    await page.waitForTimeout(200);

    // Verify topic count increased to 5
    await expect(page.locator("text=5 Chủ Đề")).toBeVisible();

    // 4. Click "Xuất File Excel (.xlsx)"
    const exportExcelBtn = page.getByRole("button", { name: /Xuất File Excel \(\.xlsx\)/i });
    await expect(exportExcelBtn).toBeVisible();
    await exportExcelBtn.click();

    // 5. Verify success banner
    await expect(
      page.locator("text=Đã kết xuất thành công tệp bảng tính Excel (.xlsx) chuẩn khảo thí!")
    ).toBeVisible({ timeout: 5000 });

    // Take screenshot of Bloom Matrix
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/tools_bloom_exam_matrix.png",
      fullPage: false,
    });
  });

  test("TC-TOOL-03: Queries live UIS admissions data and loads administrative template with 1-click fill", async ({
    page,
  }) => {
    await page.goto("/tools");
    await page.waitForLoadState("domcontentloaded");

    // 1. Switch to UIS Tab
    const uisTab = page.getByRole("tab", { name: /Cổng Dữ Liệu UIS/i });
    await expect(uisTab).toBeVisible();
    await uisTab.click();
    await page.waitForTimeout(300);

    // 2. Select Sư phạm Toán học
    const mathMajorBtn = page.getByRole("button", { name: /Sư phạm Toán học/i });
    await expect(mathMajorBtn).toBeVisible();
    await mathMajorBtn.click();
    await page.waitForTimeout(200);

    // Verify benchmark and tuition exemption
    await expect(page.getByText("Mã: 7140209")).toBeVisible();
    await expect(page.locator("text=26.50")).toBeVisible();
    await expect(page.locator("text=Miễn 100% học phí").first()).toBeVisible();

    // Click "Truy Vấn Cổng UIS"
    const queryBtn = page.getByRole("button", { name: /Truy Vấn Cổng UIS/i });
    await expect(queryBtn).toBeVisible();
    await queryBtn.click();

    await expect(
      page.locator("text=Đã đồng bộ thời gian thực từ Cổng UIS thành công!")
    ).toBeVisible({ timeout: 5000 });

    // 3. Switch to Templates Tab
    const templatesTab = page.getByRole("tab", { name: /Thư Viện Phôi Mẫu/i });
    await expect(templatesTab).toBeVisible();
    await templatesTab.click();
    await page.waitForTimeout(300);

    // Verify templates catalog
    await expect(
      page.locator("text=Thư Viện Phôi Mẫu Văn Bản Hành Chính & Đề Thi Chuẩn QNU")
    ).toBeVisible();
    await expect(page.locator("text=Quyết định Khen thưởng Sinh viên Đạt giải NCKH")).toBeVisible();

    // Take screenshot of Templates Library
    await page.screenshot({
      path: "C:/Users/AnhTuan/.gemini/antigravity-ide/brain/744e6051-db17-49ba-b02b-56558fe5c873/tools_templates_library.png",
      fullPage: false,
    });

    // 4. Click "Nạp Vào Form" on Quyết định khen thưởng
    const loadAwardTplBtn = page
      .locator('[data-testid="template-card-tpl_quyet_dinh_khen_thuong"]')
      .getByRole("button", { name: /Nạp Vào Form/i });
    await expect(loadAwardTplBtn).toBeVisible();
    await loadAwardTplBtn.click();
    await page.waitForTimeout(400);

    // Verify active tab switched back to Word ND 30 editor and content updated
    const paperPreview = page.getByTestId("nd30-paper-preview");
    await expect(paperPreview).toBeVisible();
    await expect(paperPreview).toContainText("QUYẾT ĐỊNH");
    await expect(paperPreview).toContainText("Giấy khen của Hiệu trưởng");
  });
});
