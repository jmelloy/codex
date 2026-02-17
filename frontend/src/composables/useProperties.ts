import { ref, computed, type Ref } from "vue"

/** Standard property fields handled separately from custom metadata */
const STANDARD_FIELDS = ["title", "description", "tags", "view_mode", "sort_by", "sort_direction"] as const
type StandardField = (typeof STANDARD_FIELDS)[number]

interface PropertiesSource {
  properties?: Record<string, any> | null
  title?: string
  description?: string
}

/**
 * Composable for managing editable properties (title, description, tags, custom metadata).
 * Shared between FilePropertiesPanel and FolderPropertiesPanel.
 */
export function useProperties(
  source: Ref<PropertiesSource | null>,
  emit: (event: "updateProperties", properties: Record<string, any>) => void,
) {
  const editableTitle = ref("")
  const editableDescription = ref("")
  const newTag = ref("")

  // Custom property editing state
  const newPropertyKey = ref("")
  const newPropertyValue = ref("")
  const editingProperty = ref<string | null>(null)
  const editPropertyValue = ref("")
  const valueInputRef = ref<HTMLInputElement | null>(null)

  const currentProperties = computed(() => source.value?.properties || {})

  const tags = computed(() => {
    const t = source.value?.properties?.tags
    return Array.isArray(t) ? t : []
  })

  const metadata = computed(() => {
    if (!source.value?.properties) return {}
    const result: Record<string, unknown> = {}
    for (const [key, value] of Object.entries(source.value.properties)) {
      if (!STANDARD_FIELDS.includes(key as StandardField)) {
        result[key] = value
      }
    }
    return result
  })

  function syncFromSource() {
    if (source.value) {
      editableTitle.value = source.value.properties?.title || source.value.title || ""
      editableDescription.value =
        source.value.properties?.description || source.value.description || ""
    }
  }

  function emitPropertiesUpdate(updates: Record<string, any>) {
    emit("updateProperties", { ...currentProperties.value, ...updates })
  }

  function updateTitle() {
    const current = source.value?.properties?.title || source.value?.title || ""
    if (source.value && editableTitle.value !== current) {
      emitPropertiesUpdate({ title: editableTitle.value })
    }
  }

  function updateDescription() {
    const current = source.value?.properties?.description || source.value?.description || ""
    if (source.value && editableDescription.value !== current) {
      emitPropertiesUpdate({ description: editableDescription.value })
    }
  }

  function addTag() {
    const tagToAdd = newTag.value.trim()
    if (!tagToAdd) return
    if (!tags.value.includes(tagToAdd)) {
      emitPropertiesUpdate({ tags: [...tags.value, tagToAdd] })
    }
    newTag.value = ""
  }

  function removeTag(tagToRemove: string) {
    emitPropertiesUpdate({ tags: tags.value.filter((t) => t !== tagToRemove) })
  }

  function parseValue(raw: string): unknown {
    const trimmed = raw.trim()
    if (trimmed) {
      try {
        return JSON.parse(trimmed)
      } catch {
        // Keep as string
      }
    }
    return trimmed
  }

  function addProperty() {
    const key = newPropertyKey.value.trim()
    if (!key) return
    emitPropertiesUpdate({ [key]: parseValue(newPropertyValue.value) })
    newPropertyKey.value = ""
    newPropertyValue.value = ""
  }

  function focusValueInput() {
    valueInputRef.value?.focus()
  }

  function startEditProperty(key: string, value: unknown) {
    editingProperty.value = key
    editPropertyValue.value = typeof value === "object" ? JSON.stringify(value) : String(value ?? "")
  }

  function savePropertyEdit(key: string) {
    if (editingProperty.value !== key) return
    emitPropertiesUpdate({ [key]: parseValue(editPropertyValue.value) })
    editingProperty.value = null
    editPropertyValue.value = ""
  }

  function cancelPropertyEdit() {
    editingProperty.value = null
    editPropertyValue.value = ""
  }

  function removeProperty(key: string) {
    const newProperties = { ...currentProperties.value }
    delete newProperties[key]
    emit("updateProperties", newProperties)
  }

  return {
    editableTitle,
    editableDescription,
    newTag,
    newPropertyKey,
    newPropertyValue,
    editingProperty,
    editPropertyValue,
    valueInputRef,
    currentProperties,
    tags,
    metadata,
    syncFromSource,
    emitPropertiesUpdate,
    updateTitle,
    updateDescription,
    addTag,
    removeTag,
    addProperty,
    focusValueInput,
    startEditProperty,
    savePropertyEdit,
    cancelPropertyEdit,
    removeProperty,
  }
}
