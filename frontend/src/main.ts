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

const authStore = useAuthStore()
authStore.initialize()

const themeStore = useThemeStore()
themeStore.initialize()

// Initialize view plugin service globally
viewPluginService.initialize().catch((err) => {
  console.error("Failed to initialize view plugin service:", err)
})
