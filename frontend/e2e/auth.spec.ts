/**
 * E2E tests for authentication: registration, login, and session persistence.
 */
import { test, expect } from "@playwright/test";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const PASSWORD = "E2eTest123";

test.describe("Authentication", () => {
  test("register a new user and redirect to dashboard", async ({ page }) => {
    const username = `reg_${Date.now()}`;

    await page.goto("/");

    // Should see login form when not authenticated
    await expect(page.locator("form")).toBeVisible();

    // Switch to register mode
    await page.click("text=注册");
    await page.fill('input[name="username"]', username);
    await page.fill('input[name="password"]', PASSWORD);
    await page.fill('input[name="displayName"]', "Register Test");

    // Submit registration
    await page.click('button[type="submit"]');

    // Should see success toast and switch back to login
    await expect(page.locator("text=注册成功")).toBeVisible({ timeout: 10_000 });
  });

  test("login with valid credentials", async ({ page }) => {
    // Create a user via API first
    const username = `login_${Date.now()}`;
    await page.request.post(`${BACKEND_URL}/api/v1/auth/register`, {
      data: { username, password: PASSWORD, display_name: "Login Test" },
    });

    await page.goto("/");

    // Fill login form
    await page.fill('input[name="username"]', username);
    await page.fill('input[name="password"]', PASSWORD);
    await page.click('button[type="submit"]');

    // Should redirect to dashboard after login
    await expect(page.locator("text=登录成功")).toBeVisible({ timeout: 10_000 });
  });

  test("show error on invalid credentials", async ({ page }) => {
    await page.goto("/");
    await page.fill('input[name="username"]', "nonexistent_user");
    await page.fill('input[name="password"]', "WrongPass1");
    await page.click('button[type="submit"]');

    await expect(page.locator("text=失败")).toBeVisible({ timeout: 10_000 });
  });

  test("persist session across page reloads", async ({ page }) => {
    // Login first
    const username = `persist_${Date.now()}`;
    await page.request.post(`${BACKEND_URL}/api/v1/auth/register`, {
      data: { username, password: PASSWORD, display_name: "Persist Test" },
    });

    await page.goto("/");
    await page.fill('input[name="username"]', username);
    await page.fill('input[name="password"]', PASSWORD);
    await page.click('button[type="submit"]');
    await expect(page.locator("text=登录成功")).toBeVisible({ timeout: 10_000 });

    // Reload the page and verify still logged in
    await page.reload();
    await expect(page.locator("text=登出")).toBeVisible({ timeout: 10_000 });
  });
});
