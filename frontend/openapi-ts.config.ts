import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./openapi.json",
  output: {
    path: "./src/client",
  },
  plugins: [
    {
      name: "@hey-api/client-axios",
      throwOnError: true,
    },
    "@hey-api/typescript",
    {
      name: "@hey-api/sdk",
      operations: {
        strategy: "byTags",
        containerName: "{{name}}Service",
      },
      paramsStructure: "flat",
    },
  ],
})
