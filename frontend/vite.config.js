import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";
export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            "@": fileURLToPath(new URL("./src", import.meta.url)),
        },
    },
    server: {
        port: 5174,
        host: true,
        watch: {
            usePolling: true,
        },
        proxy: {
            "/api": {
                target: process.env.VITE_API_URL || "http://localhost:8765",
                changeOrigin: true,
            },
        },
    },
});
