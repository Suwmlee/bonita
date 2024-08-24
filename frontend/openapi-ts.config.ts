import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./openapi.json",
  output: {
    format: "prettier",
    path: "./src/client",
  },
  client: "axios",
  services: {
    asClass: true,
  },
})
