/// <reference types="vitest/config" />
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: 5173,
    // In development the API runs on :8000. Proxying keeps cookies same-origin.
    // 127.0.0.1 rather than "localhost": uvicorn listens on IPv4 only, and on Windows
    // "localhost" can resolve to the IPv6 address ::1 first, which makes the proxy fail
    // with 502 Bad Gateway.
    proxy: {
      "/api": { target: process.env.VITE_PROXY_TARGET ?? "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
