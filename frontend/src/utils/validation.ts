/**
 * Form validation utilities
 */

export interface ValidationResult {
  valid: boolean
  error?: string
}

/**
 * Validate password requirements
 */
export function validatePassword(password: string): ValidationResult {
  if (password.length < 8) {
    return {
      valid: false,
      error: 'Password must be at least 8 characters'
    }
  }
  return { valid: true }
}

/**
 * Validate username requirements
 */
export function validateUsername(username: string): ValidationResult {
  if (username.length < 3) {
    return {
      valid: false,
      error: 'Username must be at least 3 characters'
    }
  }
  if (username.length > 50) {
    return {
      valid: false,
      error: 'Username must be at most 50 characters'
    }
  }
  return { valid: true }
}

/**
 * Validate that two passwords match
 */
export function validatePasswordsMatch(password: string, confirmPassword: string): ValidationResult {
  if (password !== confirmPassword) {
    return {
      valid: false,
      error: 'Passwords do not match'
    }
  }
  return { valid: true }
}

/**
 * Validate email format (basic)
 */
export function validateEmail(email: string): ValidationResult {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(email)) {
    return {
      valid: false,
      error: 'Invalid email format'
    }
  }
  return { valid: true }
}
