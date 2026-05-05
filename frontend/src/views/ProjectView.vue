<template>
  <div class="h-screen flex flex-col notebook-page" style="background: var(--page-bg)">
    <!-- Header -->
    <header
      class="flex items-center gap-3 px-6 py-4 flex-shrink-0"
      style="border-bottom: 1px solid var(--page-border); background: var(--notebook-bg)"
    >
      <button
        @click="router.push('/')"
        class="sidebar-icon-button flex items-center gap-1 text-sm"
        title="Back to files"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <line x1="19" y1="12" x2="5" y2="12"></line>
          <polyline points="12 19 5 12 12 5"></polyline>
        </svg>
        Back
      </button>

      <div class="flex items-center gap-2 flex-1 min-w-0">
        <span class="text-xl">🎬</span>
        <h1 class="m-0 text-xl font-semibold truncate" style="color: var(--notebook-text)">
          {{ projectsStore.currentProject?.name ?? slug }}
        </h1>
        <span
          v-if="projectsStore.currentProject"
          class="text-sm flex-shrink-0"
          style="color: var(--pen-gray)"
        >
          {{ projectsStore.currentProject.total_images }} images
        </span>
      </div>

      <button
        @click="showAssignModal = true"
        class="notebook-button px-4 py-2 rounded text-sm text-white border-none cursor-pointer transition flex-shrink-0"
      >
        + Assign Images
      </button>
    </header>

    <!-- Loading -->
    <div
      v-if="projectsStore.loading"
      class="flex-1 flex items-center justify-center"
      style="color: var(--pen-gray)"
    >
      Loading project...
    </div>

    <!-- Error -->
    <div
      v-else-if="projectsStore.error"
      class="flex-1 flex items-center justify-center"
      style="color: var(--pen-gray)"
    >
      {{ projectsStore.error }}
    </div>

    <!-- Empty -->
    <div
      v-else-if="!projectsStore.currentProject?.roles?.length"
      class="flex-1 flex flex-col items-center justify-center gap-3"
      style="color: var(--pen-gray)"
    >
      <span class="text-4xl">📂</span>
      <p class="text-sm">No images in this project yet.</p>
      <p class="text-xs">
        Assign images using the
        <strong>+ Assign Images</strong>
        button, or apply
        <code>project:{{ slug }}</code>
        tags directly.
      </p>
    </div>

    <!-- Role swimlanes -->
    <div v-else class="flex-1 overflow-y-auto p-6 space-y-8">
      <section v-for="group in projectsStore.currentProject.roles" :key="group.role">
        <!-- Role header -->
        <div class="flex items-center gap-3 mb-4">
          <span :class="roleBadgeClass(group.role)" class="role-badge px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wide">
            {{ group.role }}
          </span>
          <span class="text-sm" style="color: var(--pen-gray)">{{ group.images.length }} image{{ group.images.length !== 1 ? 's' : '' }}</span>
          <div class="flex-1 h-px" style="background: var(--page-border)"></div>
        </div>

        <!-- Image grid -->
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-3">
          <div
            v-for="image in group.images"
            :key="image.block_id"
            class="image-card relative rounded-lg overflow-hidden cursor-pointer group"
            style="aspect-ratio: 1; background: var(--page-border)"
            @click="openImage(image)"
          >
            <!-- Image thumbnail -->
            <img
              v-if="isImageType(image)"
              :src="imageUrl(image)"
              :alt="image.title || image.filename || image.block_id"
              class="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
              loading="lazy"
            />
            <!-- Non-image file placeholder -->
            <div
              v-else
              class="w-full h-full flex items-center justify-center text-2xl"
              style="background: var(--notebook-bg)"
            >
              📄
            </div>

            <!-- Role badges overlay -->
            <div
              class="absolute bottom-0 left-0 right-0 p-1 flex flex-wrap gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
              style="background: linear-gradient(transparent, rgba(0,0,0,0.7))"
            >
              <span
                v-for="role in image.roles"
                :key="role"
                :class="roleBadgeClass(role)"
                class="role-badge text-[10px] px-1.5 py-0.5 rounded font-medium"
              >
                {{ role }}
              </span>
            </div>

            <!-- Unassign button -->
            <button
              class="absolute top-1 right-1 w-5 h-5 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity text-white text-xs"
              style="background: rgba(0,0,0,0.6)"
              title="Remove from project"
              @click.stop="unassignImage(image)"
            >
              ×
            </button>
          </div>
        </div>
      </section>
    </div>

    <!-- Assign modal -->
    <AssignToProjectModal
      v-if="showAssignModal"
      :workspace-slug="workspaceSlug"
      :initial-project-slug="slug"
      @close="showAssignModal = false"
      @assigned="onAssigned"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useProjectsStore } from "../stores/projects"
import { useWorkspaceStore } from "../stores/workspace"
import type { ImageInfo } from "../services/projects"
import AssignToProjectModal from "../components/AssignToProjectModal.vue"

const ROLE_COLORS: Record<string, string> = {
  character: "bg-blue-500 text-white",
  scene: "bg-green-600 text-white",
  background: "bg-purple-600 text-white",
  prop: "bg-orange-500 text-white",
  concept: "bg-yellow-500 text-black",
  reference: "bg-slate-500 text-white",
  other: "bg-gray-500 text-white",
}

const route = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()
const workspaceStore = useWorkspaceStore()

const showAssignModal = ref(false)

const workspaceSlug = computed(() => route.params.workspaceSlug as string)
const slug = computed(() => route.params.slug as string)

function roleBadgeClass(role: string) {
  return ROLE_COLORS[role] ?? "bg-gray-500 text-white"
}

function isImageType(image: ImageInfo) {
  return image.content_type?.startsWith("image/") ?? false
}

function imageUrl(image: ImageInfo) {
  return `/api/v1/workspaces/${image.workspace_slug}/notebooks/${image.notebook_slug}/blocks/${image.block_id}/content`
}

function openImage(image: ImageInfo) {
  router.push(`/w/${image.workspace_slug}/${image.notebook_slug}`)
}

async function unassignImage(image: ImageInfo) {
  if (!workspaceSlug.value) return
  try {
    await projectsStore.unassign(workspaceSlug.value, slug.value, [image.block_id])
    await projectsStore.fetchProject(workspaceSlug.value, slug.value)
  } catch {
    // ignore
  }
}

async function onAssigned() {
  showAssignModal.value = false
  if (workspaceSlug.value) {
    await projectsStore.fetchProject(workspaceSlug.value, slug.value)
  }
}

async function load() {
  if (workspaceSlug.value && slug.value) {
    await projectsStore.fetchProject(workspaceSlug.value, slug.value)
  }
}

onMounted(load)
watch([workspaceSlug, slug], load)
</script>

<style scoped>
.role-badge {
  display: inline-block;
}
</style>
