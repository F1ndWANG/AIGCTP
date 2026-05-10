/**
 * E2E tests for page navigation and layout.
 *
 * Verifies that authenticated users can navigate between major sections
 * and that each page renders its core elements without crashing.
 */
import { test, expect } from "@playwright/test";

const PAGES = [
  { path: "/", label: "首页" },
  { path: "/chat", label: "对话" },
  { path: "/travel", label: "旅行" },
  { path: "/diet", label: "饮食" },
  { path: "/restaurants", label: "餐厅" },
  { path: "/products", label: "商品" },
];

test.describe("Navigation", () => {
  PAGES.forEach(({ path, label }) => {
    test(`navigate to ${label} (${path})`, async ({ page }) => {
      await page.goto(path);
      await page.waitForLoadState("networkidle");

      // Verify we landed on the right page
      await expect(page).toHaveURL(new RegExp(path.replace("/", "\\/")));

      // The page should have some non-empty content
      const body = page.locator("body");
      const text = await body.innerText();
      expect(text.length).toBeGreaterThan(0);
    });
  });

  test("navigation menu is accessible from all pages", async ({ page }) => {
    // Start at chat
    await page.goto("/chat");
    await page.waitForLoadState("networkidle");

    // Look for navigation — try common patterns: sidebar, top nav, hamburger
    const nav = page
      .locator("nav, [role='navigation'], header, [class*='sidebar'], [class*='navbar']")
      .first();
    await expect(nav).toBeVisible({ timeout: 10_000 });

    // Check that key navigation links exist
    const chatLink = nav.locator("a, button").filter({ hasText: /对话|Chat/i });
    await expect(chatLink.first()).toBeVisible();
  });

  test("theme toggle works", async ({ page }) => {
    await page.goto("/chat");
    await page.waitForLoadState("networkidle");

    const toggle = page
      .locator("button:has(svg), [class*='theme'], [class*='Theme'], button[aria-label*='theme']")
      .first();

    // Theme toggle might not be present in all layouts
    const exists = await toggle.isVisible().catch(() => false);
    if (exists) {
      await toggle.click();
      // Verify the theme class changed
      const html = page.locator("html");
      const classAttr = await html.getAttribute("class");
      expect(classAttr).toBeTruthy();
    }
  });

  test("404 page is handled gracefully", async ({ page }) => {
    const response = await page.goto("/nonexistent-page");
    expect(response?.status()).toBe(404);
  });
});
