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
      path: "/notebooks/:notebookId/pages/:pageId/entries/new",
      name: "create-entry",
      component: () => import("@/views/CreateEntryView.vue"),
    },
    {
      path: "/comfyui",
      name: "comfyui",
      component: () => import("@/views/ComfyUIView.vue"),
    },
    {
      path: "/search",
      name: "search",
      component: () => import("@/views/SearchView.vue"),
    },
    {
      path: "/demo",
      name: "demo",
      component: () => import("@/views/DemoView.vue"),
    },
    {
      path: "/sql",
      name: "sql-viewer",
      component: () => import("@/views/SQLViewerView.vue"),
    },
    {
      path: "/files",
      name: "files",
      component: () => import("@/views/FileView.vue"),
    },
    {
      path: "/artifacts/:hash",
      name: "artifact-detail",
      component: () => import("@/views/ArtifactDetailView.vue"),
    },
  ],
});

export default router;
