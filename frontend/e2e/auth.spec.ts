/**
 * E2E tests for authentication: registration, login, and session persistence.
 */
import { test, expect, request as playwrightRequest } from "@playwright/test";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:9000";
const PASSWORD = "E2eTest123";

async function createUser(username: string, display_name: string) {
  const api = await playwrightRequest.newContext({ baseURL: BACKEND_URL });
  const response = await api.post("/api/v1/auth/register", {
    data: { username, password: PASSWORD, display_name },
  });
  expect([201, 409]).toContain(response.status());
  await api.dispose();
}

test.describe("Authentication", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("register a new user and redirect to dashboard", async ({ page }) => {
    const username = `reg_${Date.now()}`;

    await page.goto("/");

    // Should see login form when not authenticated
    await expect(page.locator("form")).toBeVisible();

    // Switch to register mode
    await page.click("text=注册");
    await page.fill("#username", username);
    await page.fill("#password", PASSWORD);
    await page.fill("#displayName", "Register Test");

    // Submit registration
    await page.click('button[type="submit"]');

    await expect(page.locator("text=注册成功")).toBeVisible({ timeout: 10_000 });
    await expect(page.locator("text=你好，Register Test")).toBeVisible({ timeout: 10_000 });
  });

  test("login with valid credentials", async ({ page }) => {
    // Create a user via API first
    const username = `login_${Date.now()}`;
    await createUser(username, "Login Test");

    await page.goto("/");

    // Fill login form
    await page.fill("#username", username);
    await page.fill("#password", PASSWORD);
    await page.click('button[type="submit"]');

    await expect(page.locator("text=登录成功")).toBeVisible({ timeout: 10_000 });
    await expect(page.locator("text=你好，Login Test")).toBeVisible({ timeout: 10_000 });
  });

  test("show error on invalid credentials", async ({ page }) => {
    await page.goto("/");
    await page.fill("#username", "nonexistent_user");
    await page.fill("#password", "WrongPass1");
    await page.click('button[type="submit"]');

    await expect(page.locator("text=/失败|错误|无效|Invalid|密码/")).toBeVisible({ timeout: 10_000 });
  });

  test("persist session across page reloads", async ({ page }) => {
    // Login first
    const username = `persist_${Date.now()}`;
    await createUser(username, "Persist Test");

    await page.goto("/");
    await page.fill("#username", username);
    await page.fill("#password", PASSWORD);
    await page.click('button[type="submit"]');
    await expect(page.locator("text=登录成功")).toBeVisible({ timeout: 10_000 });

    // Reload the page and verify still logged in
    await page.reload();
    await expect(page.locator("text=你好，Persist Test")).toBeVisible({ timeout: 10_000 });
  });
});
