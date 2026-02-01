import { createApp } from "vue"
import { createPinia } from "pinia"
import "./style.css"
import App from "./App.vue"
import router from "./router"

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

app.mount("#app")

// Initialize stores after app is mounted
import { useAuthStore } from "./stores/auth"
import { useThemeStore } from "./stores/theme"
import { viewPluginService } from "./services/viewPluginService"
import { pluginRegistry } from "./services/pluginRegistry"

const authStore = useAuthStore()
authStore.initialize()

const themeStore = useThemeStore()
themeStore.initialize()

// Register plugins with backend (frontend-led plugin architecture)
// This tells the backend which plugins exist so it can store config/state
pluginRegistry.registerPlugins().catch((err) => {
  console.warn("Failed to register plugins with backend:", err)
  // Continue anyway - frontend can work without backend registration
})

// Initialize view plugin service globally
viewPluginService.initialize().catch((err) => {
  console.error("Failed to initialize view plugin service:", err)
})
