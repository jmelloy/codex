import { test, expect } from "@playwright/test";

const BASE = process.env.BASE_URL || "http://localhost:8065";

/** Get an auth token for a fresh user. */
async function getAuthToken(request: any): Promise<string> {
  const username = `api_ws_${Date.now()}`;
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

test.describe("API: Workspaces", () => {
  let token: string;
  let headers: Record<string, string>;

  test.beforeAll(async ({ request }) => {
    token = await getAuthToken(request);
    headers = { Authorization: `Bearer ${token}` };
  });

  test.afterAll(async ({ request }) => {
    // Clean up all workspaces created for this user, including the default one.
    try {
      const listResp = await request.get(`${BASE}/api/v1/workspaces/`, {
        headers,
      });
      if (listResp.ok()) {
        const workspaces = await listResp.json();
        if (Array.isArray(workspaces)) {
          for (const ws of workspaces) {
            if (ws && typeof ws.id !== "undefined") {
              await request.delete(
                `${BASE}/api/v1/workspaces/${ws.id}`,
                { headers }
              );
            }
          }
        }
      }
    } finally {
      // Best-effort user cleanup after workspaces have been deleted.
      await request.delete(`${BASE}/api/v1/users/me`, { headers });
    }
  });
  test("create a workspace", async ({ request }) => {
    const resp = await request.post(`${BASE}/api/v1/workspaces/`, {
      headers,
      data: { name: "API Test WS" },
    });
    expect(resp.status()).toBe(200);
    const ws = await resp.json();
    expect(ws.name).toBe("API Test WS");
    expect(ws.slug).toBeTruthy();

    // Cleanup
    await request.delete(`${BASE}/api/v1/workspaces/${ws.id}`, { headers });
  });

  test("list workspaces", async ({ request }) => {
    const resp = await request.get(`${BASE}/api/v1/workspaces/`, { headers });
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(Array.isArray(body)).toBeTruthy();
  });

  test("get workspace by slug and id", async ({ request }) => {
    const ws = await (
      await request.post(`${BASE}/api/v1/workspaces/`, {
        headers,
        data: { name: "Slug ID WS" },
      })
    ).json();

    const bySlug = await request.get(
      `${BASE}/api/v1/workspaces/${ws.slug}`,
      { headers }
    );
    expect(bySlug.status()).toBe(200);
    expect((await bySlug.json()).id).toBe(ws.id);

    const byId = await request.get(
      `${BASE}/api/v1/workspaces/${ws.id}`,
      { headers }
    );
    expect(byId.status()).toBe(200);
    expect((await byId.json()).slug).toBe(ws.slug);

    await request.delete(`${BASE}/api/v1/workspaces/${ws.id}`, { headers });
  });

  test("delete workspace", async ({ request }) => {
    const ws = await (
      await request.post(`${BASE}/api/v1/workspaces/`, {
        headers,
        data: { name: "Delete WS" },
      })
    ).json();

    const del = await request.delete(
      `${BASE}/api/v1/workspaces/${ws.id}`,
      { headers }
    );
    expect(del.status()).toBe(200);

    const get = await request.get(
      `${BASE}/api/v1/workspaces/${ws.id}`,
      { headers }
    );
    expect(get.status()).toBe(404);
  });

  test("update workspace theme", async ({ request }) => {
    const ws = await (
      await request.post(`${BASE}/api/v1/workspaces/`, {
        headers,
        data: { name: "Theme WS" },
      })
    ).json();

    const resp = await request.patch(
      `${BASE}/api/v1/workspaces/${ws.slug}/theme`,
      { headers, data: { theme: "dark" } }
    );
    expect(resp.status()).toBe(200);
    expect((await resp.json()).theme_setting).toBe("dark");

    await request.delete(`${BASE}/api/v1/workspaces/${ws.id}`, { headers });
  });
});
