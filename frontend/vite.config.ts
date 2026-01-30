/// <reference types="vitest" />
import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import path from "path"
import fs from "fs"

// Resolve plugins directory - check multiple locations
const resolvePluginsDir = () => {
  // Check environment variable first
  if (process.env.VITE_PLUGINS_DIR && fs.existsSync(process.env.VITE_PLUGINS_DIR)) {
    return process.env.VITE_PLUGINS_DIR
  }
  // Check parent directory (standard layout: codex/plugins when running from codex/frontend)
  const parentPlugins = path.resolve(__dirname, "../plugins")
  if (fs.existsSync(parentPlugins)) {
    return parentPlugins
  }
  // Docker mount location
  if (fs.existsSync("/plugins")) {
    return "/plugins"
  }
  // Fallback to a local plugins directory
  return path.resolve(__dirname, "./plugins")
}

const pluginsDir = resolvePluginsDir()

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@plugins": pluginsDir,
    },
  },
  server: {
    host: true, // Listen on all addresses
    port: 5173,
    strictPort: true,
    watch: {
      usePolling: true, // Needed for Docker on some systems
    },
    proxy: {
      // Proxy API requests to the backend server
      // Use VITE_PROXY_TARGET for Docker (http://backend:8000) or default to localhost
      "/api": {
        target: process.env.VITE_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
    // Watch plugins directory for changes
    fs: {
      allow: [path.resolve(__dirname, ".."), pluginsDir],
    },
  },
  // Allow importing from plugins directory
  optimizeDeps: {
    include: [],
    exclude: [],
  },
  build: {
    // Include plugins in the build
    rollupOptions: {
      external: [],
    },
  },
  // @ts-ignore - Vitest config: There's a known type conflict between vite and vitest versions
  // of defineConfig. Using @ts-ignore is the recommended workaround per Vitest documentation.
  test: {
    globals: true,
    environment: "happy-dom",
    setupFiles: ["./src/__tests__/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      exclude: ["node_modules/", "src/**/*.spec.ts", "src/**/*.test.ts"],
    },
  },
})
