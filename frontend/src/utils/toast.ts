/**
 * Toast notification utility
 */

export interface ToastOptions {
  message: string
  duration?: number
  type?: 'success' | 'error' | 'info'
}

const TOAST_COLORS = {
  success: '#48bb78',
  error: '#f56565',
  info: '#667eea'
}

/**
 * Show a toast notification
 */
export function showToast(options: ToastOptions) {
  const { message, duration = 2000, type = 'success' } = options
  
  const toast = document.createElement('div')
  toast.textContent = message
  toast.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: ${TOAST_COLORS[type]};
    color: white;
    padding: 12px 24px;
    border-radius: 6px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    z-index: 1000;
    transition: opacity 0.3s ease-out;
  `
  
  document.body.appendChild(toast)
  
  setTimeout(() => {
    toast.style.opacity = '0'
    toast.style.transition = 'opacity 0.3s ease-out'
    setTimeout(() => {
      toast.remove()
    }, 300)
  }, duration)
}
