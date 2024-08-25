import Vue from "@vitejs/plugin-vue"
// Plugins
import AutoImport from "unplugin-auto-import/vite"
import Components from "unplugin-vue-components/vite"
import Layouts from "vite-plugin-vue-layouts"
import Vuetify, { transformAssetUrls } from "vite-plugin-vuetify"
import svgLoader from "vite-svg-loader"

import { URL, fileURLToPath } from "node:url"
// Utilities
import { defineConfig } from "vite"

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    Layouts(),
    Vue({
      template: { transformAssetUrls },
    }),
    // https://github.com/vuetifyjs/vuetify-loader/tree/master/packages/vite-plugin#readme
    Vuetify({
      autoImport: true,
      styles: {
        configFile: "src/assets/styles/variables/_vuetify.scss",
      },
    }),
    Components({
      dirs: ["src/@core/components", "src/components"],
      dts: "src/components.d.ts",
    }),
    // Docs: https://github.com/antfu/unplugin-auto-import#unplugin-auto-import
    AutoImport({
      imports: ["vue", "vue-router", "@vueuse/core", "pinia"],
      dts: "src/auto-imports.d.ts",
      vueTemplate: true,
      // ℹ️ Disabled to avoid confusion & accidental usage
      ignore: ["useCookies", "useStorage"],
    }),
    svgLoader(),
  ],
  define: { "process.env": {} },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@core": fileURLToPath(new URL("./src/@core", import.meta.url)),
      "@layouts": fileURLToPath(new URL("./src/@layouts", import.meta.url)),
      "@images": fileURLToPath(
        new URL("./src/assets/images/", import.meta.url),
      ),
      "@styles": fileURLToPath(
        new URL("./src/assets/styles/", import.meta.url),
      ),
      "@configured-variables": fileURLToPath(
        new URL(
          "./src/assets/styles/variables/_template.scss",
          import.meta.url,
        ),
      ),
    },
  },
  build: {
    chunkSizeWarningLimit: 5000,
  },
  server: {
    port: 3000,
  },
})
