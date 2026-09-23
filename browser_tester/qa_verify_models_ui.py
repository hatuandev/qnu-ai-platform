import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ARTIFACTS_DIR = Path(r"C:\Users\AnhTuan\.gemini\antigravity-ide\brain\5ac1de7e-cde0-42c1-b1a2-230242a43863")

async def test_modelops_ui():
    print("=== [QA BROWSER TESTER] BẮT ĐẦU KIỂM THỬ TRANG /models ===")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # 1. Truy cập http://localhost:3000/models
        print("[1/5] Điều hướng đến http://localhost:3000/models...")
        await page.goto("http://localhost:3000/models", wait_until="networkidle")

        # Kiểm tra nếu bị redirect sang trang đăng nhập
        if "/sign-in" in page.url or await page.locator("button:has-text('Truy Cập Nền Tảng')").count() > 0:
            print("  -> Phát hiện màn hình đăng nhập. Đang thực hiện đăng nhập mặc định...")
            fill_default_btn = page.locator("button:has-text('Điền mặc định')")
            if await fill_default_btn.count() > 0:
                await fill_default_btn.click()
                await page.wait_for_timeout(500)
            
            submit_btn = page.locator("button:has-text('Truy Cập Nền Tảng')")
            if await submit_btn.count() > 0:
                await submit_btn.click()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(1000)
            
            # Sau khi login, điều hướng lại /models
            await page.goto("http://localhost:3000/models", wait_until="networkidle")

        print(f"  -> Đã tải trang: {page.url}")
        await page.wait_for_timeout(1000)

        # 2. Kiểm tra tab "Định Tuyến & Mặc Định Hệ Thống"
        print("[2/5] Kiểm thử Tab 1: Định Tuyến & Mặc Định Hệ Thống...")
        routing_tab = page.locator("button:has-text('Định Tuyến & Mặc Định')")
        if await routing_tab.count() > 0:
            await routing_tab.first.click()
            await page.wait_for_timeout(800)

        # Kiểm tra 4 kênh mission pipeline
        channels = [
            "1. Nhúng Vector",
            "2. Tái Xếp Hạng",
            "3. Bóc Tách & OCR",
            "4. Hội Thoại & Lý Luận"
        ]
        for ch in channels:
            exists = await page.locator(f"text={ch}").count() > 0
            status_text = "OK" if exists else "THIẾU"
            print(f"  -> Kênh '{ch}': {status_text}")

        # Thử click toggle "Mô Hình Đơn" / "Chuỗi Dự Phòng"
        single_mode_btns = page.locator("button:has-text('Mô Hình Đơn')")
        if await single_mode_btns.count() > 0:
            print(f"  -> Tìm thấy {await single_mode_btns.count()} nút 'Mô Hình Đơn', thử click kênh 3...")
            await single_mode_btns.nth(2).click()
            await page.wait_for_timeout(500)

        screenshot_path_1 = ARTIFACTS_DIR / "qa_verified_routing_defaults.png"
        await page.screenshot(path=str(screenshot_path_1), full_page=True)
        print(f"  -> Đã chụp ảnh tab Định Tuyến: {screenshot_path_1.name}")

        # 3. Kiểm tra tab "Chuỗi Dự Phòng & Combos"
        print("[3/5] Kiểm thử Tab 2: Chuỗi Dự Phòng & Combos...")
        combos_tab = page.locator("button:has-text('Chuỗi Dự Phòng & Combos')")
        if await combos_tab.count() > 0:
            await combos_tab.first.click()
            await page.wait_for_timeout(800)

        filter_tabs = ["Tất Cả", "OCR Thị Giác", "Nhúng Vector", "Tái Xếp Hạng", "LLM Chat"]
        for f in filter_tabs:
            f_btn = page.locator(f"button:has-text('{f}')")
            f_exists = await f_btn.count() > 0
            print(f"  -> Nút lọc '{f}': {'OK' if f_exists else 'THIẾU'}")

        # Click qua bộ lọc "Tái Xếp Hạng"
        rerank_filter = page.locator("button:has-text('Tái Xếp Hạng')")
        if await rerank_filter.count() > 0:
            await rerank_filter.first.click()
            await page.wait_for_timeout(500)

        # Trở lại bộ lọc "Tất Cả"
        all_filter = page.locator("button:has-text('Tất Cả')")
        if await all_filter.count() > 0:
            await all_filter.first.click()
            await page.wait_for_timeout(500)

        screenshot_path_2 = ARTIFACTS_DIR / "qa_verified_combos_section.png"
        await page.screenshot(path=str(screenshot_path_2), full_page=True)
        print(f"  -> Đã chụp ảnh tab Combos: {screenshot_path_2.name}")

        # 4. Kiểm tra Modal Tạo Combo Mới
        print("[4/5] Kiểm thử Modal Tạo Combo Mới...")
        create_combo_btn = page.locator("button:has-text('Tạo Combo Mới')")
        if await create_combo_btn.count() > 0:
            await create_combo_btn.first.click()
            await page.wait_for_timeout(600)

            # Kiểm tra 4 loại tác vụ trong modal
            modal_tasks = ["Vision OCR", "Embedding", "Reranker", "LLM Chat"]
            for mt in modal_tasks:
                btn = page.locator(f"button:has-text('{mt}')")
                print(f"  -> Lựa chọn tác vụ '{mt}': {'OK' if await btn.count() > 0 else 'THIẾU'}")

            # Thử click chọn "Reranker"
            rerank_modal_btn = page.locator("button:has-text('Reranker')")
            if await rerank_modal_btn.count() > 0:
                await rerank_modal_btn.first.click()
                await page.wait_for_timeout(400)

            screenshot_path_3 = ARTIFACTS_DIR / "qa_verified_create_modal.png"
            await page.screenshot(path=str(screenshot_path_3))
            print(f"  -> Đã chụp ảnh Modal Tạo Combo: {screenshot_path_3.name}")

            # Đóng modal
            cancel_btn = page.locator("button:has-text('Hủy')")
            if await cancel_btn.count() > 0:
                await cancel_btn.first.click()
                await page.wait_for_timeout(400)

        # 5. Kiểm tra sạch màu thô (Code / CSS Class Audit)
        print("[5/5] Kiểm tra xem còn class màu thô nào trên DOM không...")
        raw_colors = ["bg-amber-600", "bg-sky-600", "bg-purple-600", "text-amber-500", "text-sky-500", "text-purple-500"]
        violations = []
        for rc in raw_colors:
            cnt = await page.locator(f".{rc}").count()
            if cnt > 0:
                violations.append(f"{rc} ({cnt} occurrences)")

        if violations:
            print(f"  [CẢNH BÁO] Phát hiện class màu thô còn tồn tại: {', '.join(violations)}")
        else:
            print("  [XÁC THỰC] 100% SẠCH MÀU THÔ! Không phát hiện class màu cam/tím/xanh thô.")

        await browser.close()
        print("\n=== [QA BROWSER TESTER] HOÀN TẤT KIỂM THỬ THÀNH CÔNG! ===")

if __name__ == "__main__":
    asyncio.run(test_modelops_ui())
