/// <reference types="vitest" />
import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import path from "path"

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: true, // Listen on all addresses
    port: 5173,
    strictPort: true,
    watch: {
      usePolling: true, // Needed for Docker on some systems
    },
  },
  // @ts-ignore - Vitest config: There's a known type conflict between vite and vitest versions
  // of defineConfig. Using @ts-ignore is the recommended workaround per Vitest documentation.
  test: {
    globals: true,
    environment: "happy-dom",
    setupFiles: [],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      exclude: ["node_modules/", "src/**/*.spec.ts", "src/**/*.test.ts"],
    },
  },
})
