/**
 * Global auth setup for Playwright E2E tests.
 *
 * Registers a test user once and saves the authenticated storage state
 * so every test file starts logged in without repeating the login flow.
 */
import { test as setup, expect } from "@playwright/test";

const TEST_USER = {
  username: `e2e_${Date.now()}`,
  password: "E2eTest123",
  display_name: "E2E Test User",
};

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

setup("register and login test user", async ({ page }) => {
  // Register
  const registerResp = await page.request.post(`${BACKEND_URL}/api/v1/auth/register`, {
    data: TEST_USER,
  });
  // 200 = ok, 409 = already exists (idempotent)
  expect([200, 409]).toContain(registerResp.status());

  // Login
  const loginResp = await page.request.post(`${BACKEND_URL}/api/v1/auth/login`, {
    data: {
      username: TEST_USER.username,
      password: TEST_USER.password,
    },
  });
  expect(loginResp.ok()).toBeTruthy();
  const body = await loginResp.json();
  expect(body.access_token).toBeTruthy();

  // Navigate to the app and inject the token via localStorage
  await page.goto("/");
  await page.evaluate((token) => {
    localStorage.setItem("auth_token", token);
  }, body.access_token);

  // Save authenticated state for other tests
  await page.context().storageState({ path: "e2e/.auth/user.json" });

  // Expose user info via a file so tests can reference it
  const fs = require("fs");
  fs.writeFileSync(
    "e2e/.auth/user-info.json",
    JSON.stringify({ ...TEST_USER, access_token: body.access_token }),
  );
});
