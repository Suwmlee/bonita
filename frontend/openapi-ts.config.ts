import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./openapi.json",
  output: {
    path: "./src/client",
    postProcess: ["prettier"],
  },
  plugins: [
    "@hey-api/client-axios",
    "@hey-api/typescript",
    {
      name: "@hey-api/sdk",
      operations: { strategy: "byTags" },
    },
  ],
})
