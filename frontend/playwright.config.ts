import { defineConfig, devices } from "@playwright/test";
import path from "path";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const FRONTEND_URL = process.env.FRONTEND_URL || "http://localhost:3000";
const BACKEND_DIR = path.resolve(__dirname, "../backend");
const BACKEND_PYTHON =
  process.env.BACKEND_PYTHON ||
  path.join(BACKEND_DIR, "venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const BROWSER_CHANNEL = process.env.PLAYWRIGHT_CHANNEL || (process.env.CI ? undefined : "chrome");
const SERVER_LOG_MODE = process.env.PLAYWRIGHT_SHOW_WEBSERVER_LOGS === "1" ? "pipe" : "ignore";

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
    ...(BROWSER_CHANNEL ? { channel: BROWSER_CHANNEL } : {}),
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
        ...(BROWSER_CHANNEL ? { channel: BROWSER_CHANNEL } : {}),
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
          command: `"${BACKEND_PYTHON}" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env`,
          url: `${BACKEND_URL}/health`,
          reuseExistingServer: !process.env.CI,
          timeout: 30_000,
          cwd: BACKEND_DIR,
          stdout: SERVER_LOG_MODE,
          stderr: SERVER_LOG_MODE,
        },
        {
          command: `npm run dev`,
          url: FRONTEND_URL,
          reuseExistingServer: !process.env.CI,
          timeout: 60_000,
          cwd: ".",
          stdout: SERVER_LOG_MODE,
          stderr: SERVER_LOG_MODE,
        },
      ],
});
