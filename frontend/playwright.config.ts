import { defineConfig, devices } from "@playwright/test";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const FRONTEND_URL = process.env.FRONTEND_URL || "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  timeout: 60_000,
  expect: { timeout: 15_000 },

  use: {
    baseURL: FRONTEND_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    extraHTTPHeaders: {
      "X-Test-Session": "e2e",
    },
  },

  projects: [
    {
      name: "setup",
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        storageState: "e2e/.auth/user.json",
      },
      dependencies: ["setup"],
    },
  ],

  /* Run the full stack before tests (CI: services managed by Docker Compose). */
  webServer: process.env.CI
    ? undefined
    : [
        {
          command: `cd ../backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env`,
          url: `${BACKEND_URL}/health`,
          reuseExistingServer: !process.env.CI,
          timeout: 30_000,
        },
        {
          command: `npm run dev`,
          url: FRONTEND_URL,
          reuseExistingServer: !process.env.CI,
          timeout: 60_000,
          cwd: ".",
        },
      ],
});
