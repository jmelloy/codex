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

  // After registration the app auto-logs in and redirects to home
  await expect(page).toHaveURL("/", { timeout: 15_000 });
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

/**
 * Register a user via the API directly (faster than UI, useful for setup).
 */
export async function registerUserViaAPI(
  page: Page,
  user: TestUser,
): Promise<string> {
  const baseURL = page.url().startsWith("http")
    ? new URL(page.url()).origin
    : "http://localhost:8065";

  // Register
  await page.request.post(`${baseURL}/api/v1/users/register`, {
    data: {
      username: user.username,
      email: user.email,
      password: user.password,
    },
  });

  // Get token
  const tokenResponse = await page.request.post(
    `${baseURL}/api/v1/users/token`,
    {
      form: {
        username: user.username,
        password: user.password,
      },
    },
  );

  const tokenData = await tokenResponse.json();
  return tokenData.access_token;
}

/**
 * Inject an auth token into the browser so the app treats the user as logged in.
 */
export async function injectAuthToken(
  page: Page,
  token: string,
): Promise<void> {
  await page.goto("/login"); // need a page loaded to set localStorage
  await page.evaluate((t) => {
    localStorage.setItem("access_token", t);
  }, token);
}

/**
 * Extended test fixture that provides a pre-registered, logged-in page.
 */
export const test = base.extend<{ authedPage: Page; testUser: TestUser }>({
  testUser: async ({}, use) => {
    const user = generateTestUser();
    await use(user);
  },
  authedPage: async ({ page, testUser }, use) => {
    // Go to the app first so we have a base URL context
    await page.goto("/login");

    const baseURL = new URL(page.url()).origin;

    // Register via API
    const regResponse = await page.request.post(
      `${baseURL}/api/v1/users/register`,
      {
        data: {
          username: testUser.username,
          email: testUser.email,
          password: testUser.password,
        },
      },
    );

    if (!regResponse.ok()) {
      throw new Error(
        `Registration failed: ${regResponse.status()} ${await regResponse.text()}`,
      );
    }

    // Get token
    const tokenResponse = await page.request.post(
      `${baseURL}/api/v1/users/token`,
      {
        form: {
          username: testUser.username,
          password: testUser.password,
        },
      },
    );

    const tokenData = await tokenResponse.json();

    // Inject token into localStorage and navigate to home
    await page.evaluate((t) => {
      localStorage.setItem("access_token", t);
    }, tokenData.access_token);

    await page.goto("/");
    await expect(page).toHaveURL("/", { timeout: 15_000 });

    await use(page);
  },
});

export { expect } from "@playwright/test";
