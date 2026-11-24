/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API runs on :8000 (uvicorn); the dev server proxies /api to it.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": process.env.SPOTTED_API ?? "http://localhost:8000" },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
