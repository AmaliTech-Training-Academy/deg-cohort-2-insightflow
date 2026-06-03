import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Resolve a package from THIS project's node_modules regardless of where
// the importing test file lives in the monorepo.
function pkg(name: string) {
  return path.resolve(__dirname, "node_modules", name);
}

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
    include: [
      "src/**/*.{test,spec}.{ts,tsx}",
      "../qa/frontend-tests/unit/tests/**/*.{test,spec}.{ts,tsx}",
    ],
  },
  server: {
    fs: {
      // Allow serving files from anywhere inside the monorepo root.
      allow: [path.resolve(__dirname, "..")],
    },
  },
  resolve: {
    alias: {
      // Frontend source alias
      "@": path.resolve(__dirname, "./src"),

      // Explicit paths so that test files outside frontend/ resolve
      // these packages to frontend/node_modules rather than walking up
      // the directory tree and never finding them.
      "@testing-library/react":      pkg("@testing-library/react"),
      "@testing-library/user-event": pkg("@testing-library/user-event"),
      "@testing-library/jest-dom":   pkg("@testing-library/jest-dom"),
      "react":                       pkg("react"),
      "react-dom":                   pkg("react-dom"),
      "react/jsx-dev-runtime":       pkg("react/jsx-dev-runtime"),
      "react/jsx-runtime":           pkg("react/jsx-runtime"),
      "@tanstack/react-query":       pkg("@tanstack/react-query"),
      "next-themes":                 pkg("next-themes"),
    },
  },
});
