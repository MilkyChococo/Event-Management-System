const { test, expect } = require("@playwright/test");

async function loginAsAdmin(page) {
  await page.goto("/");
  await page.getByTestId("login-email").fill("admin@example.com");
  await page.getByTestId("login-password").fill("Admin123!");
  await page.getByTestId("login-submit").click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByTestId("account-trigger")).toBeVisible();
}

async function openAdminManager(page) {
  await page.getByTestId("admin-manager-link").click();
  await expect(page).toHaveURL(/\/admin\/manager$/);
  await expect(page.getByTestId("admin-section")).toBeVisible();
}

async function fillAdminEventForm(page, { title, description, location, startAt, capacity, price, category = "Workshop" }) {
  await page.getByTestId("admin-title").fill(title);
  await page.locator("#admin-description").fill(description);
  await page.locator("#admin-category").fill(category);
  await page.locator("#admin-location").fill(location);
  await page.locator("#admin-start-at").fill(startAt);
  await page.locator("#admin-capacity").fill(String(capacity));
  await page.locator("#admin-price").fill(String(price));
}

function managerItem(page, title) {
  return page.locator("#admin-manager-list .admin-manager-item").filter({ hasText: title }).first();
}

test("@smoke @critical admin can sign in and open the manager console", async ({ page }) => {
  await loginAsAdmin(page);
  await openAdminManager(page);
  await expect(page.locator("#admin-manager-list")).toBeVisible();
});

test("@smoke @critical admin can create and edit an event from the manager console", async ({ page }) => {
  const timestamp = Date.now();
  const createdTitle = `Verification Create ${timestamp}`;
  const updatedTitle = `Verification Edit ${timestamp}`;

  await loginAsAdmin(page);
  await openAdminManager(page);

  await page.getByTestId("admin-open-create").click();
  await expect(page.getByTestId("admin-event-modal")).toBeVisible();
  await fillAdminEventForm(page, {
    title: createdTitle,
    description: "Created by Playwright for the admin create-and-edit scenario.",
    location: "Automation Lab",
    startAt: "2026-05-20T09:30",
    capacity: 25,
    price: 150,
  });
  await page.getByTestId("admin-save").click();

  const createdItem = managerItem(page, createdTitle);
  await expect(createdItem).toBeVisible();

  await createdItem.getByRole("button", { name: "Edit" }).click();
  await expect(page.getByTestId("admin-event-modal")).toBeVisible();
  await expect(page.getByTestId("admin-title")).toHaveValue(createdTitle);
  await fillAdminEventForm(page, {
    title: updatedTitle,
    description: "Edited by Playwright for the admin update scenario.",
    location: "Automation Loft",
    startAt: "2026-05-21T10:45",
    capacity: 40,
    price: 220,
  });
  await page.getByTestId("admin-save").click();

  const updatedItem = managerItem(page, updatedTitle);
  await expect(updatedItem).toBeVisible();
  await expect(updatedItem).toContainText("Automation Loft");
  await expect(updatedItem).toContainText("40 capacity");
});

test("@smoke @critical admin can delete an event from the manager console", async ({ page }) => {
  const title = `Verification Delete ${Date.now()}`;

  await loginAsAdmin(page);
  await openAdminManager(page);

  await page.getByTestId("admin-open-create").click();
  await expect(page.getByTestId("admin-event-modal")).toBeVisible();
  await fillAdminEventForm(page, {
    title,
    description: "Created by Playwright for the admin delete scenario.",
    location: "Automation Archive",
    startAt: "2026-05-22T08:15",
    capacity: 18,
    price: 80,
  });
  await page.getByTestId("admin-save").click();

  const createdItem = managerItem(page, title);
  await expect(createdItem).toBeVisible();
  await createdItem.getByRole("button", { name: "Delete" }).click();

  await expect(page.locator("#admin-manager-list")).not.toContainText(title);
});
