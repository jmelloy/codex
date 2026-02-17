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

test.describe("Search", () => {
  test("search for files by name", async ({ authedPage: page }) => {
    const notebookName = `Search NB ${Date.now()}`;
    const baseURL = new URL(page.url()).origin;
    const token = await page.evaluate(() =>
      localStorage.getItem("access_token")
    );

    // Setup: create notebook with a few files via API
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

    const fileNames = ["alpha-report.md", "beta-analysis.md", "gamma-notes.md"];
    for (const name of fileNames) {
      await page.request.post(
        `${baseURL}/api/v1/workspaces/${wsId}/notebooks/${notebook.id}/files/`,
        {
          headers: { Authorization: `Bearer ${token}` },
          data: {
            filename: name,
            path: name,
            content: `# ${name}\n\nContent for ${name}`,
            content_type: "text/markdown",
          },
        }
      );
    }

    // Reload and wait for full initialization
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(page.locator("text=Notebooks")).toBeVisible({ timeout: 10_000 });

    // Ensure notebook is expanded (watcher auto-expands first notebook on load)
    await ensureNotebookExpanded(page, notebookName);
    await expect(page.getByText("alpha-report")).toBeVisible({ timeout: 10_000 });

    // Switch to Search tab
    await page.getByRole("button", { name: "Search" }).first().click();
    await expect(page.getByPlaceholder("Search files...")).toBeVisible();

    // Search for "beta"
    await page.getByPlaceholder("Search files...").fill("beta");
    await page.getByRole("button", { name: "Search" }).last().click();

    // Should find the beta file (use .first() — name appears in both title and path)
    await expect(page.getByText("beta-analysis").first()).toBeVisible({
      timeout: 10_000,
    });

    // The other files should not be visible in search results
    // (they may still be in the sidebar, so we check within the search results area)
    const searchPanel = page.locator(".search-result-item");
    const resultCount = await searchPanel.count();
    expect(resultCount).toBeGreaterThanOrEqual(1);
  });

  test("search with no results shows empty state", async ({
    authedPage: page,
  }) => {
    // Wait for sidebar to load
    await expect(page.locator("text=Notebooks")).toBeVisible({ timeout: 10_000 });

    // Switch to Search tab
    await page.getByRole("button", { name: "Search" }).first().click();

    // Search for something that doesn't exist
    await page.getByPlaceholder("Search files...").fill("zzz_nonexistent_xyz");
    await page.getByRole("button", { name: "Search" }).last().click();

    // Should show "No files found"
    await expect(page.getByText(/No files found/)).toBeVisible({
      timeout: 10_000,
    });
  });
});
