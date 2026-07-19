import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    css: true,
    exclude: ["node_modules", ".next", "e2e"],
    env: {
      // Matches src/test/msw/handlers.ts's API_BASE. Individual tests that
      // need a different value (e.g. client.test.ts's "unset" case) save
      // and restore process.env.NEXT_PUBLIC_API_BASE_URL themselves.
      NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000",
    },
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      exclude: [
        "node_modules/**",
        ".next/**",
        "**/*.config.*",
        "src/app/**/layout.tsx",
        "src/components/ui/**",
      ],
    },
  },
});
