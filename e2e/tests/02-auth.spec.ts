import { test, expect } from "@playwright/test";
import { generateTestUser, registerUser, loginUser } from "../fixtures/auth";

test.describe.serial("Authentication", () => {
  const user = generateTestUser();

  test("register a new user", async ({ page }) => {
    await page.goto("/register");

    await expect(page.getByRole("heading", { name: "Register" })).toBeVisible();
    await expect(page.getByLabel("Username")).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();

    await page.getByLabel("Username").fill(user.username);
    await page.getByLabel("Email").fill(user.email);
    await page.getByLabel("Password", { exact: true }).fill(user.password);
    await page.getByLabel("Confirm Password").fill(user.password);
    await page.getByRole("button", { name: "Register" }).click();

    // Should redirect to home after registration + auto-login
    await expect(page).toHaveURL("/", { timeout: 15_000 });
    // Should display the username in the sidebar user section
    await expect(
      page.getByRole("button", { name: "Logout" })
    ).toBeVisible({ timeout: 5_000 });
  });

  test("logout and login again", async ({ page }) => {
    // Use a fresh user to avoid conflicts with the previous test
    const freshUser = generateTestUser();
    await registerUser(page, freshUser);

    // Click the logout button (SVG icon in sidebar)
    await page.getByTitle("Logout").click();
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });

    // Log back in
    await loginUser(page, freshUser);

    // Verify we're on the home page
    await expect(page).toHaveURL("/", { timeout: 10_000 });
  });

  test("login with wrong password shows error", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Username").fill(user.username);
    await page.getByLabel("Password").fill("wrong_password_123");
    await page.getByRole("button", { name: "Login" }).click();

    // Should show an error and stay on login page
    await expect(page.locator(".error")).toBeVisible({ timeout: 5_000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test("register with mismatched passwords shows error", async ({ page }) => {
    const newUser = generateTestUser();
    await page.goto("/register");
    await page.getByLabel("Username").fill(newUser.username);
    await page.getByLabel("Email").fill(newUser.email);
    await page.getByLabel("Password", { exact: true }).fill(newUser.password);
    await page.getByLabel("Confirm Password").fill("different_password!");

    await page.getByRole("button", { name: "Register" }).click();

    // Should show a validation error
    await expect(page.getByText(/match/i)).toBeVisible({ timeout: 5_000 });
    await expect(page).toHaveURL(/\/register/);
  });

  test("navigate between login and register", async ({ page }) => {
    await page.goto("/login");
    await page.getByText("Register here").click();
    await expect(page).toHaveURL(/\/register/);

    await page.getByText("Login here").click();
    await expect(page).toHaveURL(/\/login/);
  });

  test("unauthenticated user is redirected to login", async ({ page }) => {
    // Clear any stored tokens
    await page.goto("/login");
    await page.evaluate(() => localStorage.clear());

    await page.goto("/");
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });
  });
});
