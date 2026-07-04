import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Dev: o Vite faz proxy de /api para o FastAPI (porta 8000).
// Prod: o FastAPI serve o build (frontend/dist) e a API na mesma origem.
// Produção: servido atrás do proxy nginx em /cenarios/tb-v2/ (prefixo
// stripado antes de chegar no FastAPI, mas o browser precisa ver os
// assets com o prefixo).
export default defineConfig(({ command }) => ({
  base: command === "build" ? "/cenarios/tb-v2/" : "/",
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks: {
          echarts: ["echarts/core", "echarts/charts", "echarts/components", "echarts/renderers"],
          react: ["react", "react-dom", "@tanstack/react-query"],
        },
      },
    },
  },
}));
