import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [vue()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    fs: {
      allow: [".."],
    },
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@vue/test-utils": fileURLToPath(
        new URL(
          "./node_modules/@vue/test-utils/dist/vue-test-utils.esm-bundler.mjs",
          import.meta.url,
        ),
      ),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["../tests/frontend/**/*.spec.ts"],
  },
});
