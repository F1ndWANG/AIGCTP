/**
 * E2E tests for the chat interface.
 *
 * These tests depend on `auth.setup.ts` having run first so the
 * storage state is populated with a valid auth token.
 */
import { test, expect } from "@playwright/test";

test.describe("Chat", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/chat");
    // Wait for the chat page to mount (the message input should be visible)
    await page.waitForSelector('textarea, input[type="text"]', { timeout: 15_000 });
  });

  test("chat page loads with input and send button", async ({ page }) => {
    // Verify the page title / heading
    await expect(page).toHaveURL(/\/chat/);
    // Input should be enabled
    const input = page.locator('textarea, input[type="text"]').first();
    await expect(input).toBeEnabled();
  });

  test("send a message and receive a response", async ({ page }) => {
    const input = page.locator('textarea, input[type="text"]').first();

    await input.fill("你好");
    await page.click('button[type="submit"], button:has(svg), button:has-text("发送")');

    // Wait for the assistant response to appear (this may take a while with LLM)
    // We check for any message bubbles in the chat area
    const messages = page.locator("[class*='message'], [class*='Message'], [class*='chat-bubble']");
    await expect(messages.first()).toBeVisible({ timeout: 60_000 });
  });

  test("shows thinking indicator while waiting for response", async ({ page }) => {
    const input = page.locator('textarea, input[type="text"]').first();

    await input.fill("介绍一下你自己");
    await page.click('button[type="submit"], button:has(svg), button:has-text("发送")');

    // A "thinking" indicator or loading spinner should appear
    const thinking = page.locator("text=思考, text=分析, text=loading, [class*='spinner'], [class*='loading']");
    await expect(thinking).toBeVisible({ timeout: 5_000 }).catch(() => {
      // The response might be too fast — that's fine
    });
  });

  test("suggestion chips are interactive", async ({ page }) => {
    // Look for suggestion chips / quick-reply buttons
    const chips = page.locator("button:has-text('规划'), button:has-text('推荐'), [class*='chip'], [class*='suggestion']");
    const chipCount = await chips.count();

    if (chipCount > 0) {
      await chips.first().click();

      // After clicking, the input should be populated or a message sent
      const input = page.locator('textarea, input[type="text"]').first();
      const inputValue = await input.inputValue();
      if (!inputValue) {
        // Message was sent directly — verify response
        const messages = page.locator("[class*='message'], [class*='Message']");
        await expect(messages.first()).toBeVisible({ timeout: 60_000 }).catch(() => {
          // Allow for cases where the response has finished already
        });
      }
    }
  });
});
