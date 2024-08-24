/**
 * main.ts
 *
 * Bootstraps Vuetify and other plugins then mounts the App`
 */

import { OpenAPI } from "./client"

// Components
import App from "./App.vue"

// Composables
import { createApp } from "vue"

// Plugins
import { registerPlugins } from "./plugins"

// Styles
import "@core/scss/template/index.scss"
import "@layouts/styles/index.scss"
import "@styles/styles.scss"

OpenAPI.BASE = import.meta.env.VITE_API_URL
OpenAPI.TOKEN = async () => {
  return localStorage.getItem("access_token") || ""
}

const app = createApp(App)

registerPlugins(app)

app.mount("#app")
