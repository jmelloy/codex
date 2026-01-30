import { createRouter, createWebHistory } from "vue-router"
import { useAuthStore } from "../stores/auth"
import HomeView from "../views/HomeView.vue"
import LoginView from "../views/LoginView.vue"
import RegisterView from "../views/RegisterView.vue"
import IntegrationSettingsView from "../views/IntegrationSettingsView.vue"
import IntegrationConfigView from "../views/IntegrationConfigView.vue"
import PageDetailView from "../views/PageDetailView.vue"

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
      path: "/settings",
      redirect: { path: "/", query: { view: "settings" } },
    },
    {
      path: "/page/:notebookId/:pagePath+",
      name: "page-detail",
      component: PageDetailView,
      meta: { requiresAuth: true },
    },
    {
      path: "/integrations",
      name: "integrations",
      component: IntegrationSettingsView,
      meta: { requiresAuth: true },
    },
    {
      path: "/integrations/:integrationId",
      name: "integration-config",
      component: IntegrationConfigView,
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
