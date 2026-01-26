import { ref } from 'vue'

/**
 * Composable for copying text to clipboard
 * @returns copied - reactive boolean indicating if text was just copied
 * @returns copy - async function to copy text to clipboard
 */
export function useCopyToClipboard() {
  const copied = ref(false)
  let timeoutId: number | null = null

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      copied.value = true
      
      // Reset copied state after 2 seconds
      if (timeoutId !== null) {
        clearTimeout(timeoutId)
      }
      timeoutId = window.setTimeout(() => {
        copied.value = false
        timeoutId = null
      }, 2000)
      
      return true
    } catch (err) {
      console.error('Failed to copy to clipboard:', err)
      copied.value = false
      return false
    }
  }

  return {
    copied,
    copy
  }
}
