import { test, expect, ensureNotebookExpanded } from "../fixtures/auth";

/** Helper to create a file via the snippets API. */
async function createFileViaAPI(
  page: any,
  baseURL: string,
  token: string,
  workspaceSlug: string,
  notebookSlug: string,
  path: string,
  content: string
) {
  return page.request.post(`${baseURL}/api/v1/snippets/`, {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      workspace: workspaceSlug,
      notebook: notebookSlug,
      filename: path,
      content,
      title: path.replace(".md", ""),
    },
  });
}

test.describe("File Operations", () => {
  test("create a markdown file in a notebook", async ({
    authedPage: page,
  }) => {
    const notebookName = `Files NB ${Date.now()}`;
    const fileName = "hello.md";

    // Create a notebook
    await expect(page.locator("text=Notebooks")).toBeVisible({ timeout: 10_000 });
    await page
      .locator("text=Notebooks")
      .locator("..")
      .getByTitle("Create Notebook")
      .click();
    await page.locator('input[required]').last().fill(notebookName);
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.getByText(notebookName)).toBeVisible({ timeout: 10_000 });

    // Ensure notebook is expanded (may be auto-expanded after creation)
    const notebookRow = await ensureNotebookExpanded(page, notebookName);
    await expect(notebookRow.getByText("No files yet")).toBeVisible({ timeout: 5_000 });

    // Click the "+" button to create a file within this notebook
    await notebookRow.getByTitle("New File").click();

    // Fill in the name in the New Page dialog
    await expect(page.getByText("New Page")).toBeVisible();
    await page.getByPlaceholder("My Page").fill(fileName.replace(".md", ""));
    await page.getByRole("button", { name: "Create" }).click();

    // The new page should appear in the sidebar
    await expect(notebookRow.getByText(fileName.replace(".md", ""))).toBeVisible({ timeout: 10_000 });
  });

  test("view a markdown file content", async ({ authedPage: page }) => {
    const notebookName = `View NB ${Date.now()}`;

    // Create notebook and file via API for speed
    const baseURL = new URL(page.url()).origin;
    const token = await page.evaluate(() =>
      localStorage.getItem("access_token")
    );

    // Get workspaces
    const wsResponse = await page.request.get(
      `${baseURL}/api/v1/workspaces/`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    const workspaces = await wsResponse.json();
    const ws = workspaces[0];

    // Create notebook
    const nbResponse = await page.request.post(
      `${baseURL}/api/v1/workspaces/${ws.id}/notebooks/`,
      {
        headers: { Authorization: `Bearer ${token}` },
        data: { name: notebookName },
      }
    );
    const notebook = await nbResponse.json();

    // Create file via snippets API
    await createFileViaAPI(
      page, baseURL, token!, ws.slug, notebook.slug,
      "readme.md",
      "# Hello World\n\nThis is a test file for E2E testing."
    );

    // Navigate to the workspace/notebook URL to ensure the correct workspace is shown
    await page.goto(`/w/${ws.slug}/${notebook.slug}`);
    await expect(page.locator("text=Notebooks")).toBeVisible({ timeout: 10_000 });

    // Ensure notebook is expanded
    await ensureNotebookExpanded(page, notebookName);
    await expect(page.getByText("readme")).toBeVisible({ timeout: 10_000 });

    // Click the file
    await page.getByText("readme").click();

    // Should display the rendered markdown content
    await expect(page.locator("main")).toContainText("Hello World", {
      timeout: 10_000,
    });
    await expect(page.locator("main")).toContainText(
      "This is a test file for E2E testing."
    );
  });

  test("view and verify markdown file content", async ({ authedPage: page }) => {
    const notebookName = `Edit NB ${Date.now()}`;
    const baseURL = new URL(page.url()).origin;
    const token = await page.evaluate(() =>
      localStorage.getItem("access_token")
    );

    // Setup: create notebook and file via API
    const wsResponse = await page.request.get(
      `${baseURL}/api/v1/workspaces/`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    const workspaces = await wsResponse.json();
    const ws = workspaces[0];

    const nbResponse = await page.request.post(
      `${baseURL}/api/v1/workspaces/${ws.id}/notebooks/`,
      {
        headers: { Authorization: `Bearer ${token}` },
        data: { name: notebookName },
      }
    );
    const notebook = await nbResponse.json();

    await createFileViaAPI(
      page, baseURL, token!, ws.slug, notebook.slug,
      "editable.md",
      "# Original Content\n\nSome body text here."
    );

    // Navigate to the workspace/notebook URL
    await page.goto(`/w/${ws.slug}/${notebook.slug}`);
    await expect(page.locator("text=Notebooks")).toBeVisible({ timeout: 10_000 });

    // Ensure notebook is expanded
    await ensureNotebookExpanded(page, notebookName);
    await expect(page.getByText("editable")).toBeVisible({ timeout: 10_000 });
    await page.getByText("editable").click();

    // Verify content is displayed in the main area
    await expect(page.locator("main")).toContainText("Original Content", {
      timeout: 10_000,
    });
    await expect(page.locator("main")).toContainText("Some body text here.");
  });
});
