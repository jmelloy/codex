import { createApp } from "vue";
import { createPinia } from "pinia";
import "./style.css";
import App from "./App.vue";
import router from "./router";
import { useAuthStore } from "./stores/auth";
import { useThemeStore } from "./stores/theme";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);

// Initialize auth state
const authStore = useAuthStore();
authStore.initialize();

// Initialize theme preference
const themeStore = useThemeStore();
themeStore.initialize();

app.mount("#app");
