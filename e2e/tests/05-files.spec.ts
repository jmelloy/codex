import { test, expect, ensureNotebookExpanded } from "../fixtures/auth";

/** Helper: get the first workspace and auth token from the authed page. */
async function getWorkspaceContext(page: any) {
  const baseURL = new URL(page.url()).origin;
  const token = await page.evaluate(() =>
    localStorage.getItem("access_token")
  );
  const wsResponse = await page.request.get(`${baseURL}/api/v1/workspaces/`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const workspaces = await wsResponse.json();
  return { baseURL, token: token!, ws: workspaces[0] };
}

/** Helper: create a notebook via API. */
async function createNotebookViaAPI(
  page: any,
  baseURL: string,
  token: string,
  wsId: number,
  name: string
) {
  const resp = await page.request.post(
    `${baseURL}/api/v1/workspaces/${wsId}/notebooks/`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: { name },
    }
  );
  return resp.json();
}

/** Helper: create a page inside a notebook, then add a text block with content. */
async function createPageWithContent(
  page: any,
  baseURL: string,
  token: string,
  wsId: number,
  notebookSlug: string,
  title: string,
  content: string
) {
  const headers = { Authorization: `Bearer ${token}` };
  const blocksBase = `${baseURL}/api/v1/workspaces/${wsId}/notebooks/${notebookSlug}/blocks`;

  // Create the page
  const pageResp = await page.request.post(`${blocksBase}/pages`, {
    headers,
    data: { title },
  });
  const pageData = await pageResp.json();

  // Create a text block inside the page with markdown content
  await page.request.post(`${blocksBase}/`, {
    headers,
    data: {
      parent_block_id: pageData.block_id,
      block_type: "text",
      content,
      content_format: "markdown",
    },
  });

  return pageData;
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

    const { baseURL, token, ws } = await getWorkspaceContext(page);
    const notebook = await createNotebookViaAPI(page, baseURL, token, ws.id, notebookName);

    // Create a page with content (pages show in sidebar, leaf blocks don't)
    await createPageWithContent(
      page, baseURL, token, ws.id, notebook.slug,
      "readme",
      "# Hello World\n\nThis is a test file for E2E testing."
    );

    // Navigate to the workspace/notebook URL to ensure the correct workspace is shown
    await page.goto(`/w/${ws.slug}/${notebook.slug}`);
    await expect(page.locator("text=Notebooks")).toBeVisible({ timeout: 10_000 });

    // Ensure notebook is expanded
    await ensureNotebookExpanded(page, notebookName);
    await expect(page.getByText("readme")).toBeVisible({ timeout: 10_000 });

    // Click the page
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

    const { baseURL, token, ws } = await getWorkspaceContext(page);
    const notebook = await createNotebookViaAPI(page, baseURL, token, ws.id, notebookName);

    await createPageWithContent(
      page, baseURL, token, ws.id, notebook.slug,
      "editable",
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
