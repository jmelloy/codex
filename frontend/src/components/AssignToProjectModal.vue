<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/50" @click="emit('close')"></div>

      <!-- Modal panel -->
      <div
        class="relative rounded-lg shadow-xl p-6 w-full max-w-md mx-4"
        style="background: var(--notebook-bg); border: 1px solid var(--page-border); color: var(--notebook-text)"
      >
        <h2 class="m-0 mb-5 text-lg font-semibold">Assign to Project</h2>

        <!-- Project slug -->
        <div class="mb-4">
          <label class="block text-sm font-medium mb-1" style="color: var(--pen-gray)">
            Project
          </label>
          <div class="flex gap-2">
            <input
              v-model="projectSlugInput"
              type="text"
              placeholder="my-project"
              list="existing-projects"
              class="flex-1 px-3 py-2 rounded text-sm"
              style="background: var(--page-bg); border: 1px solid var(--page-border); color: var(--notebook-text)"
            />
            <datalist id="existing-projects">
              <option v-for="p in projectsStore.projects" :key="p.slug" :value="p.slug">
                {{ p.name }}
              </option>
            </datalist>
          </div>
          <p class="text-xs mt-1" style="color: var(--pen-gray)">
            Use lowercase letters, numbers, and hyphens (e.g. <code>my-film</code>). A new project is created automatically.
          </p>
        </div>

        <!-- Roles -->
        <div class="mb-5">
          <label class="block text-sm font-medium mb-2" style="color: var(--pen-gray)">
            Role(s) in this project
          </label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="role in DEFAULT_ROLES"
              :key="role"
              type="button"
              :class="[
                'px-3 py-1 rounded-full text-xs font-medium border transition cursor-pointer',
                selectedRoles.includes(role)
                  ? roleBadgeClass(role) + ' border-transparent'
                  : 'border-current opacity-50',
              ]"
              @click="toggleRole(role)"
            >
              {{ role }}
            </button>
          </div>

          <!-- Custom role input -->
          <div class="flex gap-2 mt-3">
            <input
              v-model="customRole"
              type="text"
              placeholder="Add custom role…"
              class="flex-1 px-3 py-1.5 rounded text-sm"
              style="background: var(--page-bg); border: 1px solid var(--page-border); color: var(--notebook-text)"
              @keyup.enter="addCustomRole"
            />
            <button
              type="button"
              @click="addCustomRole"
              class="notebook-button px-3 py-1.5 rounded text-sm text-white border-none cursor-pointer"
            >
              Add
            </button>
          </div>
          <div v-if="customRoles.length" class="flex flex-wrap gap-2 mt-2">
            <span
              v-for="role in customRoles"
              :key="role"
              class="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-gray-500 text-white"
            >
              {{ role }}
              <button
                type="button"
                @click="removeCustomRole(role)"
                class="ml-0.5 opacity-70 hover:opacity-100 cursor-pointer bg-transparent border-none text-white"
              >
                ×
              </button>
            </span>
          </div>
        </div>

        <!-- Selected images info -->
        <div v-if="imageIds.length" class="mb-5 text-sm" style="color: var(--pen-gray)">
          Assigning {{ imageIds.length }} image{{ imageIds.length !== 1 ? "s" : "" }}.
        </div>

        <!-- Actions -->
        <div class="flex gap-3 justify-end">
          <button
            type="button"
            @click="emit('close')"
            class="px-4 py-2 rounded text-sm cursor-pointer border-none"
            style="background: var(--page-border); color: var(--notebook-text)"
          >
            Cancel
          </button>
          <button
            type="button"
            :disabled="!canSubmit || submitting"
            @click="submit"
            class="notebook-button px-4 py-2 rounded text-sm text-white border-none cursor-pointer transition disabled:opacity-50"
          >
            {{ submitting ? "Assigning…" : "Assign" }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { useProjectsStore } from "../stores/projects"

const DEFAULT_ROLES = ["character", "scene", "background", "prop", "concept", "reference", "other"]

const ROLE_COLORS: Record<string, string> = {
  character: "bg-blue-500 text-white",
  scene: "bg-green-600 text-white",
  background: "bg-purple-600 text-white",
  prop: "bg-orange-500 text-white",
  concept: "bg-yellow-500 text-black",
  reference: "bg-slate-500 text-white",
  other: "bg-gray-500 text-white",
}

const props = withDefaults(
  defineProps<{
    workspaceSlug: string
    /** Pre-fill the project slug (e.g. when triggered from ProjectView). */
    initialProjectSlug?: string
    /** Block IDs to assign. When empty the modal just shows the form. */
    imageIds?: string[]
  }>(),
  {
    initialProjectSlug: "",
    imageIds: () => [],
  }
)

const emit = defineEmits<{
  (e: "close"): void
  (e: "assigned", projectSlug: string): void
}>()

const projectsStore = useProjectsStore()

const projectSlugInput = ref(props.initialProjectSlug)
const selectedRoles = ref<string[]>([])
const customRole = ref("")
const customRoles = ref<string[]>([])
const submitting = ref(false)

const allRoles = computed(() => [...selectedRoles.value, ...customRoles.value])
const canSubmit = computed(
  () => projectSlugInput.value.trim().length > 0 && allRoles.value.length > 0
)

function slugify(s: string) {
  return s
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
}

function roleBadgeClass(role: string) {
  return ROLE_COLORS[role] ?? "bg-gray-500 text-white"
}

function toggleRole(role: string) {
  const idx = selectedRoles.value.indexOf(role)
  if (idx >= 0) {
    selectedRoles.value.splice(idx, 1)
  } else {
    selectedRoles.value.push(role)
  }
}

function addCustomRole() {
  const r = slugify(customRole.value)
  if (r && !customRoles.value.includes(r) && !DEFAULT_ROLES.includes(r)) {
    customRoles.value.push(r)
  }
  customRole.value = ""
}

function removeCustomRole(role: string) {
  customRoles.value = customRoles.value.filter((r) => r !== role)
}

async function submit() {
  const slug = slugify(projectSlugInput.value)
  if (!slug || allRoles.value.length === 0) return

  submitting.value = true
  try {
    await projectsStore.assign(props.workspaceSlug, slug, props.imageIds, allRoles.value)
    await projectsStore.fetchProjects(props.workspaceSlug)
    emit("assigned", slug)
  } catch (e) {
    console.error("Failed to assign to project:", e)
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  if (props.workspaceSlug) {
    projectsStore.fetchProjects(props.workspaceSlug)
  }
})
</script>
