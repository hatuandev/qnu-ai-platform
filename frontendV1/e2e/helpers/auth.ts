import { expect, type Page } from "@playwright/test";

/**
 * Ensures the page is loaded and local dev auto-login has succeeded.
 * Waits for the Topbar and main layout to be fully rendered.
 */
export async function loginAndEnsureDashboard(page: Page): Promise<void> {
  await page.goto("/dashboard");

  // Wait for the auto-login bridge to succeed and page content to appear
  // Topbar or Sidebar will be rendered once authenticated
  await expect(page.getByRole("banner")).toBeVisible({ timeout: 15000 });

  // Verify the user profile or workspace selector is present
  await expect(
    page.getByRole("navigation").or(page.getByText("Tổng quan")),
  ).toBeVisible({ timeout: 10000 });
}

/**
 * Selects a workspace from the Topbar WorkspaceSwitcher if not already selected.
 */
export async function selectWorkspace(
  page: Page,
  workspaceName: string,
): Promise<void> {
  // If we already see the workspace name in the header/topbar, nothing to do
  const currentSwitcher = page
    .getByRole("banner")
    .getByRole("combobox")
    .or(page.getByRole("banner").getByRole("button"));

  if (await currentSwitcher.filter({ hasText: workspaceName }).isVisible()) {
    return;
  }

  // Click switcher
  await currentSwitcher.click();
  const option = page.getByRole("option", { name: workspaceName });
  if (await option.isVisible({ timeout: 2000 })) {
    await option.click();
  }
}

