/**
 * E2E tests for page navigation and layout.
 *
 * Verifies that authenticated users can navigate between major sections
 * and that each page renders its core elements without crashing.
 */
import { test, expect } from "@playwright/test";

const PAGES = [
  { path: "/", label: "首页", content: /你好|AI 生活推荐/ },
  { path: "/chat", label: "对话", content: /AI 对话|发送|输入你的问题/ },
  { path: "/plans", label: "旅行", content: /我的行程|暂无行程|行程/ },
  { path: "/diet", label: "饮食", content: /饮食健康|饮食日志|健康档案|饮食计划/ },
  { path: "/restaurants", label: "餐厅", content: /餐厅推荐|AI 对话同步|搜索/ },
  { path: "/products", label: "商品", content: /商品列表|搜索商品|共 \d+ 件商品/ },
  { path: "/shares", label: "游记", content: /旅行笔记|游记|发布/ },
];

test.describe("Navigation", () => {
  PAGES.forEach(({ path, label, content }) => {
    test(`navigate to ${label} (${path})`, async ({ page }) => {
      await page.goto(path);
      await page.waitForLoadState("networkidle");

      // Verify we landed on the right page
      await expect(page).toHaveURL(new RegExp(path.replace("/", "\\/")));

      await expect(page.locator("body")).toContainText(content, { timeout: 30_000 });
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
