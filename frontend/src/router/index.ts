import { createRouter, createWebHistory } from "vue-router";
import HomeView from "@/views/HomeView.vue";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
    },
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
      meta: { requiresGuest: true },
    },
    {
      path: "/register",
      name: "register",
      component: () => import("@/views/RegisterView.vue"),
      meta: { requiresGuest: true },
    },
    {
      path: "/search",
      name: "search",
      component: () => import("@/views/SearchView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/files",
      name: "files",
      component: () => import("@/views/FileView.vue"),
      meta: { requiresAuth: true },
    },
  ],
});

// Navigation guard for authentication
router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore();

  // Check if route requires authentication
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next("/login");
  }
  // Check if route requires guest (login/register pages)
  else if (to.meta.requiresGuest && authStore.isAuthenticated) {
    next("/files");
  }
  // Allow navigation
  else {
    next();
  }
});

export default router;
