import { test, expect } from "@playwright/test";

const BASE = process.env.BASE_URL || "http://localhost:8065";

test.describe("API: Full User Journey", () => {
  test("register → workspace → notebook → pages → blocks → edit → upload → cleanup", async ({
    request,
  }) => {
    const username = `api_journey_${Date.now()}`;

    // 1. Register
    const reg = await request.post(`${BASE}/api/v1/users/register`, {
      data: {
        username,
        email: `${username}@example.com`,
        password: "testpass123",
      },
    });
    expect(reg.status()).toBe(201);

    // 2. Login
    const login = await request.post(`${BASE}/api/v1/users/token`, {
      form: { username, password: "testpass123" },
    });
    expect(login.status()).toBe(200);
    const token = (await login.json()).access_token;
    const headers = { Authorization: `Bearer ${token}` };

    // 3. Profile
    const me = await request.get(`${BASE}/api/v1/users/me`, { headers });
    expect(me.status()).toBe(200);
    expect((await me.json()).username).toBe(username);

    // 4. Create workspace
    const ws = await (
      await request.post(`${BASE}/api/v1/workspaces/`, {
        headers,
        data: { name: "Journey WS" },
      })
    ).json();
    expect(ws.name).toBe("Journey WS");

    // 5. Create notebook
    const nb = await (
      await request.post(
        `${BASE}/api/v1/workspaces/${ws.slug}/notebooks/`,
        { headers, data: { name: "Lab Journal" } }
      )
    ).json();
    expect(nb.name).toBe("Lab Journal");
    const blocks = `${BASE}/api/v1/workspaces/${ws.slug}/notebooks/${nb.id}/blocks`;

    // 6. Create page
    const page = await (
      await request.post(`${blocks}/pages`, {
        headers,
        data: { title: "Experiment #1" },
      })
    ).json();
    expect(page.block_id).toBeTruthy();

    // 7. Add text blocks
    const b1 = await (
      await request.post(`${blocks}/`, {
        headers,
        data: {
          parent_block_id: page.block_id,
          block_type: "text",
          content: "## Hypothesis\n\nThroughput improves by 20%.",
        },
      })
    ).json();
    expect(b1.block_id).toBeTruthy();

    const b2 = await (
      await request.post(`${blocks}/`, {
        headers,
        data: {
          parent_block_id: page.block_id,
          block_type: "text",
          content: "## Method\n\nA/B test over 7 days.",
        },
      })
    ).json();

    // 8. Edit a block
    const upd = await request.put(`${blocks}/${b1.block_id}`, {
      headers,
      data: { content: "## Hypothesis (revised)\n\nThroughput improves by 30%." },
    });
    expect(upd.status()).toBe(200);

    const fetched = await (
      await request.get(`${blocks}/${b1.block_id}`, { headers })
    ).json();
    expect(fetched.content).toContain("30%");

    // 9. Upload a file
    const upload = await request.post(`${blocks}/upload`, {
      headers,
      multipart: {
        file: {
          name: "results.csv",
          mimeType: "text/csv",
          buffer: Buffer.from("name,value\nalpha,1\nbeta,2\n"),
        },
        parent_block_id: page.block_id,
      },
    });
    expect(upload.status()).toBe(200);

    // 10. Create sub-page
    const subPage = await (
      await request.post(`${blocks}/pages`, {
        headers,
        data: { title: "Appendix A", parent_path: page.path },
      })
    ).json();
    expect(subPage.block_id).toBeTruthy();

    // 11. Verify tree
    const tree = await (
      await request.get(`${blocks}/tree`, { headers })
    ).json();
    expect(tree.tree).toBeDefined();

    // 12. Get children
    const children = (
      await (
        await request.get(`${blocks}/${page.block_id}/children`, { headers })
      ).json()
    ).children;
    expect(children.length).toBeGreaterThanOrEqual(2);

    // 13. Delete a block
    expect(
      (await request.delete(`${blocks}/${b2.block_id}`, { headers })).status()
    ).toBe(200);

    // 14. Update properties
    const props = await request.patch(
      `${blocks}/${page.block_id}/properties`,
      { headers, data: { properties: { status: "complete" } } }
    );
    expect(props.status()).toBe(200);

    // 15. Create task
    const task = await (
      await request.post(`${BASE}/api/v1/tasks/`, {
        headers,
        params: { workspace_id: ws.id, title: "Review results" },
      })
    ).json();
    expect(task.title).toBe("Review results");

    // 16. Search
    const search = await request.get(
      `${BASE}/api/v1/workspaces/${ws.slug}/search/`,
      { headers, params: { q: "hypothesis" } }
    );
    expect(search.status()).toBe(200);

    // 17. Cleanup
    // Delete all workspaces owned by this user (including the auto-created default)
    const allWsResp = await request.get(`${BASE}/api/v1/workspaces/`, { headers });
    expect(allWsResp.status()).toBe(200);
    const allWorkspaces = await allWsResp.json();
    for (const w of allWorkspaces) {
      const delResp = await request.delete(`${BASE}/api/v1/workspaces/${w.id}`, {
        headers,
      });
      expect(delResp.status()).toBe(200);
    }

    // Verify the explicitly created workspace is gone
    expect(
      (
        await request.get(`${BASE}/api/v1/workspaces/${ws.id}`, { headers })
      ).status()
    ).toBe(404);

    // Finally, delete the user account to avoid accumulating users across runs
    await request.delete(`${BASE}/api/v1/users/me`, { headers });
  });
});
