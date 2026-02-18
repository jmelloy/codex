import { request, type FullConfig } from "@playwright/test";
import path from "path";

/**
 * Global setup: register a shared test user and save the authenticated
 * storageState so individual tests can skip the registration ceremony.
 */
export const STORAGE_STATE = path.join(__dirname, ".auth", "user.json");

export const SHARED_USER = {
  username: `e2e_shared_${Date.now()}`,
  password: "SharedPass_E2E!",
  email: `e2e_shared_${Date.now()}@example.com`,
};

async function globalSetup(config: FullConfig) {
  const baseURL =
    config.projects[0]?.use?.baseURL ||
    process.env.BASE_URL ||
    "http://localhost:8065";

  const ctx = await request.newContext({ baseURL });

  // Register
  await ctx.post("/api/v1/users/register", {
    data: {
      username: SHARED_USER.username,
      email: SHARED_USER.email,
      password: SHARED_USER.password,
    },
  });

  // Get token
  const tokenResponse = await ctx.post("/api/v1/users/token", {
    form: {
      username: SHARED_USER.username,
      password: SHARED_USER.password,
    },
  });
  const { access_token } = await tokenResponse.json();

  // Save the storageState with the token injected into localStorage.
  // Playwright's storageState captures cookies + localStorage per origin.
  // We need a browser context to set localStorage, so use a lightweight approach:
  // write the state file directly in the format Playwright expects.
  const origin = new URL(baseURL).origin;
  const state = {
    cookies: [],
    origins: [
      {
        origin,
        localStorage: [{ name: "access_token", value: access_token }],
      },
    ],
  };

  const fs = await import("fs");
  fs.mkdirSync(path.dirname(STORAGE_STATE), { recursive: true });
  fs.writeFileSync(STORAGE_STATE, JSON.stringify(state, null, 2));

  await ctx.dispose();
}

export default globalSetup;
