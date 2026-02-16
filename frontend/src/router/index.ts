import { createRouter, createWebHistory } from "vue-router"
import { useAuthStore } from "../stores/auth"
import HomeView from "../views/HomeView.vue"
import LoginView from "../views/LoginView.vue"
import RegisterView from "../views/RegisterView.vue"
import PageDetailView from "../views/PageDetailView.vue"
import OAuthCallbackView from "../views/OAuthCallbackView.vue"
import CalendarView from "../views/CalendarView.vue"

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
      meta: { requiresAuth: true },
    },
    {
      // Redirect /markdown to / for backwards compatibility
      path: "/markdown",
      redirect: "/",
    },
    {
      // File/folder view with path-based URLs: /workspace/notebook/path/to/file
      path: "/w/:workspaceSlug/:notebookSlug/:filePath*",
      name: "file-view",
      component: HomeView,
      meta: { requiresAuth: true },
    },
    {
      path: "/page/:notebookId/:pagePath+",
      name: "page-detail",
      component: PageDetailView,
      meta: { requiresAuth: true },
    },
    {
      path: "/calendar",
      name: "calendar",
      component: CalendarView,
      meta: { requiresAuth: true },
    },
    {
      path: "/oauth/callback",
      name: "oauth-callback",
      component: OAuthCallbackView,
      meta: { requiresAuth: true },
    },
    {
      path: "/login",
      name: "login",
      component: LoginView,
    },
    {
      path: "/register",
      name: "register",
      component: RegisterView,
    },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // Ensure auth store is initialized on first navigation
  // This handles hot reload scenarios where the store may have been reset
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

export default router
