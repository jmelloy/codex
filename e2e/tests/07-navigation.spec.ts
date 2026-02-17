import { test, expect } from "../fixtures/auth";

/** Ensure a notebook is expanded in the sidebar (handles auto-expansion). */
async function ensureNotebookExpanded(page: import("@playwright/test").Page, notebookName: string) {
  const notebookRow = page.locator(".notebook-item").filter({ hasText: notebookName });
  await expect(notebookRow).toBeVisible({ timeout: 10_000 });
  const arrow = await notebookRow.locator("span").first().textContent();
  if (arrow?.trim() !== "▼") {
    await notebookRow.click();
  }
  return notebookRow;
}

test.describe("Navigation & URL Routing", () => {
  test("page title updates when viewing a file", async ({
    authedPage: page,
  }) => {
    const notebookName = `Nav NB ${Date.now()}`;
    const baseURL = new URL(page.url()).origin;
    const token = await page.evaluate(() =>
      localStorage.getItem("access_token")
    );

    // Setup via API
    const wsResponse = await page.request.get(
      `${baseURL}/api/v1/workspaces/`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    const workspaces = await wsResponse.json();
    const wsId = workspaces[0].id;

    const nbResponse = await page.request.post(
      `${baseURL}/api/v1/workspaces/${wsId}/notebooks`,
      {
        headers: { Authorization: `Bearer ${token}` },
        data: { name: notebookName, path: notebookName.toLowerCase().replace(/ /g, "-") },
      }
    );
    const notebook = await nbResponse.json();

    await page.request.post(
      `${baseURL}/api/v1/workspaces/${wsId}/notebooks/${notebook.id}/files/`,
      {
        headers: { Authorization: `Bearer ${token}` },
        data: {
          filename: "nav-test.md",
          path: "nav-test.md",
          content: "# Navigation Test",
          content_type: "text/markdown",
        },
      }
    );

    // Reload and wait for full initialization
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(page.locator("text=Notebooks")).toBeVisible({ timeout: 10_000 });

    // Ensure notebook is expanded (watcher auto-expands first notebook on load)
    await ensureNotebookExpanded(page, notebookName);
    await expect(page.getByText("nav-test")).toBeVisible({ timeout: 10_000 });
    await page.getByText("nav-test").click();

    // Page title should contain the file name
    await expect(page).toHaveTitle(/nav-test/, { timeout: 10_000 });

    // URL should include the file path
    await expect(page).toHaveURL(/nav-test/, { timeout: 5_000 });
  });

  test("welcome message shows when no file selected", async ({
    authedPage: page,
  }) => {
    await expect(page.getByText("Welcome to Codex")).toBeVisible({
      timeout: 10_000,
    });
  });

  test("files tab and search tab switching", async ({ authedPage: page }) => {
    await expect(page.locator("text=Notebooks")).toBeVisible({ timeout: 10_000 });

    // Switch to Search tab
    await page.getByRole("button", { name: "Search" }).first().click();
    await expect(page.getByPlaceholder("Search files...")).toBeVisible();

    // Switch back to Files tab
    await page.getByRole("button", { name: "Files" }).first().click();
    await expect(page.locator("text=Workspaces")).toBeVisible();
  });
});
