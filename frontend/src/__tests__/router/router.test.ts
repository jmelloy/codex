import { describe, it, expect, beforeEach, vi } from "vitest"
import { createRouter, createWebHistory, type Router } from "vue-router"
import { setActivePinia, createPinia } from "pinia"
import { useAuthStore } from "../../stores/auth"

// Mock the view components
vi.mock("../../views/HomeView.vue", () => ({ default: { template: "<div>Home</div>" } }))
vi.mock("../../views/LoginView.vue", () => ({ default: { template: "<div>Login</div>" } }))
vi.mock("../../views/RegisterView.vue", () => ({ default: { template: "<div>Register</div>" } }))
vi.mock("../../views/OAuthCallbackView.vue", () => ({
  default: { template: "<div>OAuth</div>" },
}))
vi.mock("../../views/CalendarView.vue", () => ({
  default: { template: "<div>Calendar</div>" },
}))

// Mock auth service used by authStore.initialize()
vi.mock("../../services/auth", () => ({
  authService: {
    login: vi.fn(),
    getCurrentUser: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    isAuthenticated: vi.fn().mockReturnValue(false),
    saveToken: vi.fn(),
  },
}))

vi.mock("../../stores/integration", () => ({
  useIntegrationStore: () => ({
    loadIntegrations: vi.fn().mockResolvedValue(undefined),
    reset: vi.fn(),
  }),
}))

vi.mock("../../services/pluginRegistry", () => ({
  pluginRegistry: {
    registerPlugins: vi
      .fn()
      .mockResolvedValue({ registered: 0, updated: 0, failed: 0, results: [] }),
  },
}))

vi.mock("../../services/viewPluginService", () => ({
  viewPluginService: { initialize: vi.fn().mockResolvedValue(undefined) },
}))

function createTestRouter(): Router {
  const HomeView = { template: "<div>Home</div>" }
  const LoginView = { template: "<div>Login</div>" }
  const RegisterView = { template: "<div>Register</div>" }
  const OAuthCallbackView = { template: "<div>OAuth</div>" }
  const CalendarView = { template: "<div>Calendar</div>" }

  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: "/", name: "home", component: HomeView, meta: { requiresAuth: true } },
      { path: "/markdown", redirect: "/" },
      {
        path: "/w/:workspaceSlug/:notebookSlug/:filePath*",
        name: "file-view",
        component: HomeView,
        meta: { requiresAuth: true },
      },
      {
        path: "/calendar",
        name: "calendar",
        component: CalendarView,
        meta: { requiresAuth: true },
      },
      { path: "/oauth/callback", name: "oauth-callback", component: OAuthCallbackView },
      { path: "/login", name: "login", component: LoginView },
      { path: "/register", name: "register", component: RegisterView },
    ],
  })

  router.beforeEach(async (to, _from, next) => {
    const authStore = useAuthStore()

    if (!authStore.isAuthenticated && localStorage.getItem("access_token")) {
      await authStore.initialize()
    }

    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
      next("/login")
    } else if ((to.path === "/login" || to.path === "/register") && authStore.isAuthenticated) {
      next("/")
    } else {
      next()
    }
  })

  return router
}

describe("Router", () => {
  let router: Router

  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
    router = createTestRouter()
  })

  describe("route definitions", () => {
    it("has all expected routes", () => {
      const routeNames = router.getRoutes().map((r) => r.name).filter(Boolean)
      expect(routeNames).toContain("home")
      expect(routeNames).toContain("login")
      expect(routeNames).toContain("register")
      expect(routeNames).toContain("oauth-callback")
      expect(routeNames).toContain("calendar")
      expect(routeNames).toContain("file-view")
    })

    it("marks protected routes with requiresAuth", () => {
      const home = router.getRoutes().find((r) => r.name === "home")
      const calendar = router.getRoutes().find((r) => r.name === "calendar")
      const fileView = router.getRoutes().find((r) => r.name === "file-view")
      const login = router.getRoutes().find((r) => r.name === "login")

      expect(home?.meta.requiresAuth).toBe(true)
      expect(calendar?.meta.requiresAuth).toBe(true)
      expect(fileView?.meta.requiresAuth).toBe(true)
      expect(login?.meta.requiresAuth).toBeFalsy()
    })
  })

  describe("auth guard", () => {
    it("redirects unauthenticated users to login for protected routes", async () => {
      await router.push("/")
      await router.isReady()

      expect(router.currentRoute.value.path).toBe("/login")
    })

    it("allows unauthenticated users to access login", async () => {
      await router.push("/login")
      await router.isReady()

      expect(router.currentRoute.value.path).toBe("/login")
    })

    it("allows unauthenticated users to access register", async () => {
      await router.push("/register")
      await router.isReady()

      expect(router.currentRoute.value.path).toBe("/register")
    })

    it("allows unauthenticated users to access oauth callback", async () => {
      await router.push("/oauth/callback")
      await router.isReady()

      expect(router.currentRoute.value.path).toBe("/oauth/callback")
    })

    it("allows authenticated users to access protected routes", async () => {
      const authStore = useAuthStore()
      authStore.isAuthenticated = true

      await router.push("/")
      await router.isReady()

      expect(router.currentRoute.value.path).toBe("/")
    })

    it("redirects authenticated users away from login to home", async () => {
      const authStore = useAuthStore()
      authStore.isAuthenticated = true

      await router.push("/login")
      await router.isReady()

      expect(router.currentRoute.value.path).toBe("/")
    })

    it("redirects authenticated users away from register to home", async () => {
      const authStore = useAuthStore()
      authStore.isAuthenticated = true

      await router.push("/register")
      await router.isReady()

      expect(router.currentRoute.value.path).toBe("/")
    })

    it("redirects unauthenticated users from calendar to login", async () => {
      await router.push("/calendar")
      await router.isReady()

      expect(router.currentRoute.value.path).toBe("/login")
    })

    it("allows authenticated users to access calendar", async () => {
      const authStore = useAuthStore()
      authStore.isAuthenticated = true

      await router.push("/calendar")
      await router.isReady()

      expect(router.currentRoute.value.path).toBe("/calendar")
    })

    it("attempts to initialize auth store when token exists in localStorage", async () => {
      const { authService } = await import("../../services/auth")
      localStorage.setItem("access_token", "some-token")
      vi.mocked(authService.isAuthenticated).mockReturnValue(true)
      vi.mocked(authService.getCurrentUser).mockResolvedValue({
        id: 1,
        username: "test",
        email: "test@test.com",
        is_active: true,
      })

      // Create a fresh router so the guard fires
      router = createTestRouter()
      await router.push("/")
      await router.isReady()

      // Since initialize sets isAuthenticated=true via fetchCurrentUser,
      // the user should be allowed through to home
      expect(router.currentRoute.value.path).toBe("/")
    })
  })

  describe("file-view route", () => {
    it("matches workspace/notebook/file paths", async () => {
      const authStore = useAuthStore()
      authStore.isAuthenticated = true

      await router.push("/w/my-workspace/my-notebook/docs/readme.md")
      await router.isReady()

      const route = router.currentRoute.value
      expect(route.name).toBe("file-view")
      expect(route.params.workspaceSlug).toBe("my-workspace")
      expect(route.params.notebookSlug).toBe("my-notebook")
    })
  })
})
