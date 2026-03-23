import { test, expect } from "@playwright/test";

const BASE = process.env.BASE_URL || "http://localhost:8065";

async function getAuthToken(request: any): Promise<string> {
  const username = `api_nb_${Date.now()}`;
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

test.describe("API: Notebooks", () => {
  let token: string;
  let headers: Record<string, string>;
  let ws: any;

  test.beforeAll(async ({ request }) => {
    token = await getAuthToken(request);
    headers = { Authorization: `Bearer ${token}` };
    ws = await (
      await request.post(`${BASE}/api/v1/workspaces/`, {
        headers,
        data: { name: "NB Test WS" },
      })
    ).json();
  });

  test.afterAll(async ({ request }) => {
    await request.delete(`${BASE}/api/v1/workspaces/${ws.id}`, { headers });
  });

  test("create a notebook", async ({ request }) => {
    const resp = await request.post(
      `${BASE}/api/v1/workspaces/${ws.slug}/notebooks/`,
      { headers, data: { name: "My Notebook" } }
    );
    expect(resp.status()).toBe(200);
    const nb = await resp.json();
    expect(nb.name).toBe("My Notebook");
    expect(nb.id).toBeTruthy();
  });

  test("list notebooks", async ({ request }) => {
    // Ensure at least one notebook exists
    await request.post(
      `${BASE}/api/v1/workspaces/${ws.slug}/notebooks/`,
      { headers, data: { name: "List Test NB" } }
    );

    const resp = await request.get(
      `${BASE}/api/v1/workspaces/${ws.slug}/notebooks/`,
      { headers }
    );
    expect(resp.status()).toBe(200);
    const nbs = await resp.json();
    expect(Array.isArray(nbs)).toBeTruthy();
    expect(nbs.length).toBeGreaterThanOrEqual(1);
  });

  test("get notebook by slug", async ({ request }) => {
    const nb = await (
      await request.post(
        `${BASE}/api/v1/workspaces/${ws.slug}/notebooks/`,
        { headers, data: { name: "Slug NB" } }
      )
    ).json();

    const resp = await request.get(
      `${BASE}/api/v1/workspaces/${ws.slug}/notebooks/${nb.slug}`,
      { headers }
    );
    expect(resp.status()).toBe(200);
    expect((await resp.json()).id).toBe(nb.id);
  });

  test("delete notebook", async ({ request }) => {
    const nb = await (
      await request.post(
        `${BASE}/api/v1/workspaces/${ws.slug}/notebooks/`,
        { headers, data: { name: "Delete NB" } }
      )
    ).json();

    const del = await request.delete(
      `${BASE}/api/v1/workspaces/${ws.slug}/notebooks/${nb.id}`,
      { headers }
    );
    expect(del.status()).toBe(200);

    const get = await request.get(
      `${BASE}/api/v1/workspaces/${ws.slug}/notebooks/${nb.id}`,
      { headers }
    );
    expect(get.status()).toBe(404);
  });

  test("slug collision handled", async ({ request }) => {
    const nb1 = await (
      await request.post(
        `${BASE}/api/v1/workspaces/${ws.slug}/notebooks/`,
        { headers, data: { name: "Same Name" } }
      )
    ).json();
    const nb2 = await (
      await request.post(
        `${BASE}/api/v1/workspaces/${ws.slug}/notebooks/`,
        { headers, data: { name: "Same Name" } }
      )
    ).json();

    expect(nb1.id).not.toBe(nb2.id);
  });
});
