import { test as base, expect, type Page } from "@playwright/test";

/** Test user credentials generated per test run to avoid conflicts. */
export interface TestUser {
  username: string;
  password: string;
  email: string;
}

let userCounter = 0;

/** Generate a unique test user for each call. */
export function generateTestUser(): TestUser {
  const id = `${Date.now()}_${++userCounter}`;
  return {
    username: `e2euser_${id}`,
    password: `TestPass_${id}!`,
    email: `e2e_${id}@example.com`,
  };
}

/**
 * Register a new user via the UI and return credentials.
 * Leaves the browser on the home page, logged in.
 */
export async function registerUser(page: Page, user: TestUser): Promise<void> {
  await page.goto("/register");
  await page.getByLabel("Username").fill(user.username);
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password", { exact: true }).fill(user.password);
  await page.getByLabel("Confirm Password").fill(user.password);
  await page.getByRole("button", { name: "Register" }).click();

  await page.waitForURL("/", { timeout: 15_000 });
}

/**
 * Log in an existing user via the UI.
 * Leaves the browser on the home page, logged in.
 */
export async function loginUser(page: Page, user: TestUser): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Username").fill(user.username);
  await page.getByLabel("Password").fill(user.password);
  await page.getByRole("button", { name: "Login" }).click();

  await expect(page).toHaveURL("/", { timeout: 15_000 });
}

/** Ensure a notebook is expanded in the sidebar. */
export async function ensureNotebookExpanded(
  page: Page,
  notebookName: string,
) {
  const notebookRow = page
    .locator(".notebook-item")
    .filter({ hasText: notebookName });
  await expect(notebookRow).toBeVisible({ timeout: 10_000 });
  const arrow = await notebookRow.locator("span").first().textContent();
  if (arrow?.trim() !== "▼") {
    await notebookRow.click();
  }
  return notebookRow;
}

/**
 * Extended test fixture that provides a pre-authenticated page.
 *
 * The storageState from global-setup already has the auth token, so
 * authedPage just navigates to home and waits for the app to be ready.
 */
export const test = base.extend<{ authedPage: Page }>({
  authedPage: async ({ page }, use) => {
    await page.goto("/");
    await expect(page).toHaveURL("/", { timeout: 15_000 });
    await use(page);
  },
});

export { expect } from "@playwright/test";
