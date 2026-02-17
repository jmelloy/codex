import { test, expect } from "../fixtures/auth";

test.describe("Workspaces", () => {
  test("default workspace exists after registration", async ({
    authedPage: page,
    testUser,
  }) => {
    // After registration, a default workspace named after the user is created
    await expect(page.locator("text=Workspaces")).toBeVisible({ timeout: 10_000 });
    // The default workspace should appear in the sidebar workspace list
    await expect(
      page.getByRole("listitem").filter({ hasText: testUser.username })
    ).toBeVisible({ timeout: 10_000 });
  });

  test("create a new workspace", async ({ authedPage: page }) => {
    const workspaceName = `Test Workspace ${Date.now()}`;

    // Click the "+" button next to Workspaces heading
    await page.locator("text=Workspaces").locator("..").getByTitle("Create Workspace").click();

    // Fill in the workspace name in the modal
    await expect(page.getByText("Create Workspace")).toBeVisible();
    await page.locator('input[required]').last().fill(workspaceName);
    await page.getByRole("button", { name: "Create" }).click();

    // The new workspace should appear in the sidebar
    await expect(page.locator(`text=${workspaceName}`)).toBeVisible({
      timeout: 10_000,
    });
  });

  test("switch between workspaces", async ({ authedPage: page, testUser }) => {
    const workspaceName = `Switch WS ${Date.now()}`;

    // Create a second workspace
    await page.locator("text=Workspaces").locator("..").getByTitle("Create Workspace").click();
    await page.locator('input[required]').last().fill(workspaceName);
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.locator(`text=${workspaceName}`)).toBeVisible({
      timeout: 10_000,
    });

    // Click back to the default workspace
    await page.getByText(testUser.username, { exact: false }).first().click();

    // Verify the Notebooks section is visible (workspace is selected)
    await expect(page.locator("text=Notebooks")).toBeVisible({ timeout: 5_000 });
  });
});
