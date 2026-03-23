import { test, expect } from "@playwright/test";

const BASE = process.env.BASE_URL || "http://localhost:8065";

async function getAuthToken(request: any): Promise<string> {
  const username = `api_blk_${Date.now()}`;
  await request.post(`${BASE}/api/v1/users/register`, {
    data: {
      username,
      email: `${username}@example.com`,
      password: "testpass123",
    },
  });
  const login = await request.post(`${BASE}/api/v1/users/token`, {
    form: { username, password: "testpass123" },
  });
  return (await login.json()).access_token;
}

test.describe("API: Blocks & Pages", () => {
  let token: string;
  let headers: Record<string, string>;
  let ws: any;
  let nb: any;
  let blocksUrl: string;

  test.beforeAll(async ({ request }) => {
    token = await getAuthToken(request);
    headers = { Authorization: `Bearer ${token}` };
    ws = await (
      await request.post(`${BASE}/api/v1/workspaces/`, {
        headers,
        data: { name: "Blocks WS" },
      })
    ).json();
    nb = await (
      await request.post(
        `${BASE}/api/v1/workspaces/${ws.slug}/notebooks/`,
        { headers, data: { name: "Blocks NB" } }
      )
    ).json();
    blocksUrl = `${BASE}/api/v1/workspaces/${ws.slug}/notebooks/${nb.id}/blocks`;
  });

  test.afterAll(async ({ request }) => {
    // Best-effort cleanup of all workspaces and the test user created for this suite.
    if (!token) {
      return;
    }

    try {
      // Fetch all workspaces for this user.
      const listResp = await request.get(`${BASE}/api/v1/workspaces/`, {
        headers,
      });

      if (listResp.ok()) {
        const workspaces = await listResp.json();

        if (Array.isArray(workspaces)) {
          for (const workspace of workspaces) {
            if (workspace && workspace.id) {
              await request.delete(
                `${BASE}/api/v1/workspaces/${workspace.id}`,
                { headers }
              );
            }
          }
        }
      }

      // After attempting to delete all workspaces, check if any remain for this user.
      const remainingResp = await request.get(`${BASE}/api/v1/workspaces/`, {
        headers,
      });

      if (remainingResp.ok()) {
        const remaining = await remainingResp.json();
        if (Array.isArray(remaining) && remaining.length === 0) {
          // No workspaces remain; safe to delete the user account.
          await request.delete(`${BASE}/api/v1/users/me`, { headers });
        }
      }
    } catch {
      // Ignore teardown errors to avoid masking test failures.
    }
  });

  async function createPage(
    request: any,
    title: string,
    parentPath?: string
  ) {
    const data: any = { title };
    if (parentPath) data.parent_path = parentPath;
    const resp = await request.post(`${blocksUrl}/pages`, { headers, data });
    expect(resp.status()).toBe(200);
    return resp.json();
  }

  async function createBlock(
    request: any,
    parentBlockId: string,
    content: string
  ) {
    const resp = await request.post(`${blocksUrl}/`, {
      headers,
      data: {
        parent_block_id: parentBlockId,
        block_type: "text",
        content,
      },
    });
    expect(resp.status()).toBe(200);
    return resp.json();
  }

  // ── Pages ─────────────────────────────────────────────────────────

  test("create a page", async ({ request }) => {
    const page = await createPage(request, "Test Page");
    expect(page.block_id).toBeTruthy();
    expect(page.title).toBe("Test Page");
  });

  test("create nested page", async ({ request }) => {
    const parent = await createPage(request, "Parent");
    const child = await createPage(request, "Child", parent.path);
    expect(child.path).toContain(parent.path);
  });

  // ── Blocks ────────────────────────────────────────────────────────

  test("create and get a text block", async ({ request }) => {
    const page = await createPage(request, "Block Host");
    const block = await createBlock(request, page.block_id, "Hello!");
    expect(block.block_type || block.type).toBe("text");

    const get = await request.get(`${blocksUrl}/${block.block_id}`, {
      headers,
    });
    expect(get.status()).toBe(200);
    expect((await get.json()).block_id).toBe(block.block_id);
  });

  test("update block content", async ({ request }) => {
    const page = await createPage(request, "Update Host");
    const block = await createBlock(request, page.block_id, "original");

    const upd = await request.put(`${blocksUrl}/${block.block_id}`, {
      headers,
      data: { content: "updated" },
    });
    expect(upd.status()).toBe(200);

    const fetched = await (
      await request.get(`${blocksUrl}/${block.block_id}`, { headers })
    ).json();
    expect(fetched.content).toBe("updated");
  });

  test("delete a block", async ({ request }) => {
    const page = await createPage(request, "Delete Host");
    const block = await createBlock(request, page.block_id, "bye");

    const del = await request.delete(`${blocksUrl}/${block.block_id}`, {
      headers,
    });
    expect(del.status()).toBe(200);

    const get = await request.get(`${blocksUrl}/${block.block_id}`, {
      headers,
    });
    expect(get.status()).toBe(404);
  });

  // ── Tree & Children ───────────────────────────────────────────────

  test("block tree", async ({ request }) => {
    await createPage(request, "Tree Page");
    const resp = await request.get(`${blocksUrl}/tree`, { headers });
    expect(resp.status()).toBe(200);
    expect((await resp.json()).tree).toBeDefined();
  });

  test("list root blocks", async ({ request }) => {
    const resp = await request.get(`${blocksUrl}/`, { headers });
    expect(resp.status()).toBe(200);
    expect((await resp.json()).blocks).toBeDefined();
  });

  test("get children", async ({ request }) => {
    const page = await createPage(request, "Children Host");
    await createBlock(request, page.block_id, "c1");
    await createBlock(request, page.block_id, "c2");

    const resp = await request.get(
      `${blocksUrl}/${page.block_id}/children`,
      { headers }
    );
    expect(resp.status()).toBe(200);
    const children = (await resp.json()).children;
    expect(children.length).toBeGreaterThanOrEqual(2);
  });

  // ── Move & Reorder ────────────────────────────────────────────────

  test("move block between pages", async ({ request }) => {
    const p1 = await createPage(request, "Src");
    const p2 = await createPage(request, "Dst");
    const block = await createBlock(request, p1.block_id, "moveable");

    const resp = await request.patch(
      `${blocksUrl}/${block.block_id}/move`,
      { headers, data: { new_parent_block_id: p2.block_id } }
    );
    expect(resp.status()).toBe(200);

    const children = (
      await (
        await request.get(`${blocksUrl}/${p2.block_id}/children`, { headers })
      ).json()
    ).children;
    expect(children.some((c: any) => c.block_id === block.block_id)).toBe(
      true
    );
  });

  test("reorder children", async ({ request }) => {
    const page = await createPage(request, "Reorder Host");
    const b1 = await createBlock(request, page.block_id, "first");
    const b2 = await createBlock(request, page.block_id, "second");

    const resp = await request.patch(
      `${blocksUrl}/${page.block_id}/reorder`,
      { headers, data: { block_ids: [b2.block_id, b1.block_id] } }
    );
    expect(resp.status()).toBe(200);
  });

  // ── Properties ────────────────────────────────────────────────────

  test("update block properties", async ({ request }) => {
    const page = await createPage(request, "Props Host");
    const resp = await request.patch(
      `${blocksUrl}/${page.block_id}/properties`,
      { headers, data: { properties: { status: "draft" } } }
    );
    expect(resp.status()).toBe(200);
    expect((await resp.json()).properties).toBeDefined();
  });

  // ── File Upload ───────────────────────────────────────────────────

  test("upload a file", async ({ request }) => {
    const page = await createPage(request, "Upload Host");

    const resp = await request.post(`${blocksUrl}/upload`, {
      headers,
      multipart: {
        file: {
          name: "test.txt",
          mimeType: "text/plain",
          buffer: Buffer.from("Hello from e2e!"),
        },
        parent_block_id: page.block_id,
      },
    });
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.path).toContain("test.txt");
  });
});
