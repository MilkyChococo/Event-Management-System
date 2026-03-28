const { test, expect } = require("@playwright/test");

test("@smoke student can reserve from dashboard modal then cancel on detail", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("login-email").fill("student@example.com");
  await page.getByTestId("login-password").fill("Student123!");
  await page.getByTestId("login-submit").click();

  const aiCareerNightCard = page
    .locator("#event-match-list .event-match-card")
    .filter({ hasText: "AI Career Night" })
    .first();

  await expect(aiCareerNightCard).toBeVisible();
  await aiCareerNightCard.getByRole("button", { name: "Reserve now" }).click();

  await expect(page.getByTestId("dashboard-registration-modal")).toBeVisible();
  await page.locator("#dashboard-registration-quantity").fill("2");
  await page.locator("#dashboard-registration-submit").click();
  await expect(page.getByTestId("dashboard-registration-modal")).toBeHidden();

  await aiCareerNightCard.getByRole("link", { name: "View detail" }).click();
  await expect(page.getByTestId("detail-status")).toContainText("Reserved");
  await expect(page.getByTestId("detail-cancel")).toBeVisible();

  await page.getByTestId("detail-cancel").click();
  await expect(page.getByTestId("detail-status")).toContainText("Not reserved yet");
  await expect(page.getByTestId("detail-register")).toBeVisible();
});
