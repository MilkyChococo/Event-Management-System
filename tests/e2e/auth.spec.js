const { test, expect } = require("@playwright/test");

test("@smoke student can login and move from auth page to dashboard then detail page", async ({ page }) => {
  await page.goto("/");

  await page.getByTestId("login-email").fill("student@example.com");
  await page.getByTestId("login-password").fill("Student123!");
  await page.getByTestId("login-submit").click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByTestId("account-trigger")).toBeVisible();
  await expect(page.getByTestId("event-grid")).toContainText("AI Career Night");

  const aiCareerNightCard = page
    .locator("#event-match-list .event-match-card")
    .filter({ hasText: "AI Career Night" })
    .first();

  await expect(aiCareerNightCard).toBeVisible();
  await aiCareerNightCard.getByRole("link", { name: "View detail" }).click();

  await expect(page).toHaveURL(/\/events\/\d+\/view$/);
  await expect(page.getByTestId("detail-title")).toContainText("AI Career Night");
  await expect(page.getByTestId("event-price")).not.toBeEmpty();
});



test("@smoke account menu opens billing and security on separate pages", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("login-email").fill("student@example.com");
  await page.getByTestId("login-password").fill("Student123!");
  await page.getByTestId("login-submit").click();

  await page.getByTestId("account-trigger").click();
  await page.getByTestId("account-billing-link").click();
  await expect(page).toHaveURL(/\/account\/billing$/);
  await expect(page.locator("h1")).toContainText("Billing");

  await page.getByTestId("account-trigger").click();
  await page.getByTestId("account-security-link").click();
  await expect(page).toHaveURL(/\/account\/security$/);
  await expect(page.locator("h1")).toContainText("Security and privacy");
});
