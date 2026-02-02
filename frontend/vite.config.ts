/// <reference types="vitest" />
import { defineConfig, type Plugin } from "vite"
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

// Plugin to serve the plugins directory as static files at /plugins/
function servePluginsPlugin(): Plugin {
  return {
    name: "serve-plugins",
    configureServer(server) {
      server.middlewares.use("/plugins", (req, res, next) => {
        const filePath = path.join(pluginsDir, req.url || "")
        if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
          const ext = path.extname(filePath)
          const contentTypes: Record<string, string> = {
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".vue": "text/plain; charset=utf-8",
          }
          res.setHeader("Content-Type", contentTypes[ext] || "application/octet-stream")
          res.end(fs.readFileSync(filePath))
        } else {
          next()
        }
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), servePluginsPlugin()],
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
