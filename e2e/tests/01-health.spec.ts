import { test, expect } from "@playwright/test";

test.describe("Service Health", () => {
  test("backend health endpoint returns healthy", async ({ page }) => {
    const baseURL = process.env.BASE_URL || "http://localhost:8065";
    const healthResponse = await page.request.get(`${baseURL}/health`, {
      failOnStatusCode: false,
    });
    expect(healthResponse.status()).toBe(200);
    const body = await healthResponse.json();
    expect(body.status).toBe("healthy");
  });

  test("frontend serves the app shell", async ({ page }) => {
    await page.goto("/");
    // Unauthenticated users should be redirected to login
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });
    // The page should contain the Codex title
    await expect(page.locator("h1")).toContainText("Codex");
  });

  test("login page renders correctly", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByLabel("Username")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Login" })).toBeVisible();
    await expect(page.getByText("Register here")).toBeVisible();
  });
});
