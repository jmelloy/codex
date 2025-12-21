import { createRouter, createWebHistory } from "vue-router";
import HomeView from "@/views/HomeView.vue";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
    },
    {
      path: "/notebooks",
      name: "notebooks",
      component: () => import("@/views/NotebooksView.vue"),
    },
    {
      path: "/notebooks/:notebookId",
      name: "notebook-detail",
      component: () => import("@/views/NotebookDetailView.vue"),
    },
    {
      path: "/notebooks/:notebookId/pages/:pageId",
      name: "page-detail",
      component: () => import("@/views/PageDetailView.vue"),
    },
    {
      path: "/search",
      name: "search",
      component: () => import("@/views/SearchView.vue"),
    },
    {
      path: "/files",
      name: "files",
      component: () => import("@/views/FileView.vue"),
    },
  ],
});

export default router;
