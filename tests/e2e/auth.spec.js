const { test, expect } = require("@playwright/test");

test("@smoke student can login and move from auth page to dashboard then detail page", async ({ page }) => {
  await page.goto("/");

  await page.getByTestId("login-email").fill("student@example.com");
  await page.getByTestId("login-password").fill("Student123!");
  await page.getByTestId("login-submit").click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByTestId("account-trigger")).toBeVisible();
  await expect(page.getByTestId("event-grid")).toContainText("AI Career Night");

  await page.getByTestId("detail-link-1").click();
  await expect(page).toHaveURL(/\/events\/1\/view$/);
  await expect(page.getByTestId("detail-title")).toContainText("AI Career Night");
  await expect(page.getByTestId("event-price")).not.toBeEmpty();
});
