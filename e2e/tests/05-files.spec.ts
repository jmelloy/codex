import { test, expect, ensureNotebookExpanded } from "../fixtures/auth";

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

    // Fill in the filename in the Create File dialog
    await expect(page.getByText("Create File")).toBeVisible();
    await page.getByPlaceholder("example.md").fill(fileName);
    await page.getByRole("button", { name: "Create" }).click();

    // The new file should appear in the sidebar
    await expect(notebookRow.getByText(fileName)).toBeVisible({ timeout: 10_000 });
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
    const wsId = workspaces[0].id;

    // Create notebook
    const nbResponse = await page.request.post(
      `${baseURL}/api/v1/workspaces/${wsId}/notebooks`,
      {
        headers: { Authorization: `Bearer ${token}` },
        data: { name: notebookName, path: notebookName.toLowerCase().replace(/ /g, "-") },
      }
    );
    const notebook = await nbResponse.json();

    // Create file
    await page.request.post(
      `${baseURL}/api/v1/workspaces/${wsId}/notebooks/${notebook.id}/files/`,
      {
        headers: { Authorization: `Bearer ${token}` },
        data: {
          filename: "readme.md",
          path: "readme.md",
          content: "# Hello World\n\nThis is a test file for E2E testing.",
          content_type: "text/markdown",
        },
      }
    );

    // Reload and wait for sidebar to be ready
    await page.reload();
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

  test("edit a markdown file", async ({ authedPage: page }) => {
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
          filename: "editable.md",
          path: "editable.md",
          content: "# Original Content",
          content_type: "text/markdown",
        },
      }
    );

    // Reload and navigate to the file
    await page.reload();
    await expect(page.locator("text=Notebooks")).toBeVisible({ timeout: 10_000 });

    // Ensure notebook is expanded
    await ensureNotebookExpanded(page, notebookName);
    await expect(page.getByText("editable")).toBeVisible({ timeout: 10_000 });
    await page.getByText("editable").click();

    // Verify original content is displayed (markdown files open in live edit mode)
    await expect(page.locator("main")).toContainText("Original Content", {
      timeout: 10_000,
    });

    // Switch to Raw mode for plain text editing (file opens in edit mode automatically)
    await page.getByRole("button", { name: "Raw" }).click();

    // Find the textarea and modify content
    const editor = page.locator("textarea.markdown-textarea");
    await expect(editor).toBeVisible({ timeout: 5_000 });
    await editor.fill("# Updated Content\n\nEdited via E2E test.");

    // Wait for autosave to trigger (1.5s delay + buffer)
    await page.waitForTimeout(3_000);

    // Exit edit mode
    await page.getByRole("button", { name: "Done" }).click();

    // Verify updated content is displayed in the viewer
    await expect(page.locator("main")).toContainText("Updated Content", {
      timeout: 10_000,
    });
  });
});
