const { test, expect } = require("@playwright/test");

test("@critical admin can create an event from the admin console", async ({ page }) => {
  const title = `Verification Demo ${Date.now()}`;

  await page.goto("/");
  await page.getByTestId("login-email").fill("admin@example.com");
  await page.getByTestId("login-password").fill("Admin123!");
  await page.getByTestId("login-submit").click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByTestId("admin-section")).toBeVisible();
  await page.getByTestId("admin-open-create").click();
  await expect(page.getByTestId("admin-event-modal")).toBeVisible();
  await page.getByTestId("admin-title").fill(title);
  await page.locator("#admin-description").fill("Created by Playwright for the admin regression scenario.");
  await page.locator("#admin-location").fill("Automation Lab");
  await page.locator("#admin-start-at").fill("2026-05-20T09:30");
  await page.locator("#admin-capacity").fill("25");
  await page.locator("#admin-price").fill("150000");
  await page.getByTestId("admin-save").click();

  await expect(page.getByTestId("dashboard-message")).toContainText("Event created successfully.");
  await page.getByRole("button", { name: `Show ${title}` }).click();
  await expect(page.getByTestId("event-grid")).toContainText(title);
});
