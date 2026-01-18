import { createApp } from "vue";
import { createPinia } from "pinia";
import "./style.css";
import App from "./App.vue";
import router from "./router";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);

app.mount("#app");

// Initialize stores after app is mounted
import { useAuthStore } from "./stores/auth";
import { useThemeStore } from "./stores/theme";

const authStore = useAuthStore();
authStore.initialize();

const themeStore = useThemeStore();
themeStore.initialize();
