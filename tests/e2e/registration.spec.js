const { test, expect } = require("@playwright/test");

test("@smoke student can register then cancel an event", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("login-email").fill("student@example.com");
  await page.getByTestId("login-password").fill("Student123!");
  await page.getByTestId("login-submit").click();

  await page.getByTestId("detail-link-1").click();
  await page.getByTestId("detail-register").click();
  await expect(page.getByTestId("detail-message")).toContainText("Seat reserved successfully.");
  await expect(page.getByTestId("detail-status")).toContainText("Reserved");

  await page.getByTestId("detail-cancel").click();
  await expect(page.getByTestId("detail-message")).toContainText("Reservation cancelled.");
  await expect(page.getByTestId("detail-status")).toContainText("Not reserved yet");
});
