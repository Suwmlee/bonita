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
import { registerPlugins } from "@core/utils/plugins"
import authCheck from "./hook/authCheck"

// Styles
import "@core/scss/template/index.scss"
import "@layouts/styles/index.scss"
import "@styles/styles.scss"

OpenAPI.BASE = import.meta.env.VITE_API_URL || window.location.origin
OpenAPI.TOKEN = async () => {
  return localStorage.getItem("access_token") || ""
}

const app = createApp(App)

registerPlugins(app)
app.use(authCheck)

app.mount("#app")
