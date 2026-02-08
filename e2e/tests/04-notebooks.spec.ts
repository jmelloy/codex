import { test, expect } from "../fixtures/auth";

test.describe("Notebooks", () => {
  test("create a notebook in the current workspace", async ({
    authedPage: page,
  }) => {
    const notebookName = `Notebook ${Date.now()}`;

    // Wait for the workspace sidebar to load
    await expect(page.locator("text=Notebooks")).toBeVisible({ timeout: 10_000 });

    // Click the "+" button next to Notebooks heading
    await page
      .locator("text=Notebooks")
      .locator("..")
      .getByTitle("Create Notebook")
      .click();

    // Fill in the notebook name
    await expect(page.getByText("Create Notebook")).toBeVisible();
    await page.locator('input[required]').last().fill(notebookName);
    await page.getByRole("button", { name: "Create" }).click();

    // The new notebook should appear in the sidebar
    await expect(page.getByText(notebookName)).toBeVisible({
      timeout: 10_000,
    });
  });

  test("expand and collapse a notebook", async ({ authedPage: page }) => {
    const notebookName = `Toggle NB ${Date.now()}`;

    await expect(page.locator("text=Notebooks")).toBeVisible({ timeout: 10_000 });

    // Create a notebook
    await page
      .locator("text=Notebooks")
      .locator("..")
      .getByTitle("Create Notebook")
      .click();
    await page.locator('input[required]').last().fill(notebookName);
    await page.getByRole("button", { name: "Create" }).click();

    await expect(page.getByText(notebookName)).toBeVisible({
      timeout: 10_000,
    });

    // Click the notebook name to expand it
    await page.getByText(notebookName).click();

    // Should show "No files yet" when empty
    await expect(page.getByText("No files yet")).toBeVisible({ timeout: 5_000 });

    // Click again to collapse
    await page.getByText(notebookName).click();

    // "No files yet" should no longer be visible
    await expect(page.getByText("No files yet")).not.toBeVisible({
      timeout: 3_000,
    });
  });
});
