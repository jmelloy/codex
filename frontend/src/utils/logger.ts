/**
 * Lightweight structured logger for the frontend.
 *
 * Emits one-line console messages prefixed with [codex:<category>] so
 * upload / import flows can be traced in the browser devtools.
 */

type Level = "debug" | "info" | "warn" | "error"

function format(category: string, message: string, data?: Record<string, unknown>): unknown[] {
  const prefix = `[codex:${category}]`
  if (data === undefined) return [prefix, message]
  return [prefix, message, data]
}

function emit(level: Level, category: string, message: string, data?: Record<string, unknown>) {
  const args = format(category, message, data)
  switch (level) {
    case "debug":
      console.debug(...args)
      break
    case "info":
      console.info(...args)
      break
    case "warn":
      console.warn(...args)
      break
    case "error":
      console.error(...args)
      break
  }
}

export function createLogger(category: string) {
  return {
    debug: (message: string, data?: Record<string, unknown>) => emit("debug", category, message, data),
    info: (message: string, data?: Record<string, unknown>) => emit("info", category, message, data),
    warn: (message: string, data?: Record<string, unknown>) => emit("warn", category, message, data),
    error: (message: string, data?: Record<string, unknown>) => emit("error", category, message, data),
  }
}

export type Logger = ReturnType<typeof createLogger>
