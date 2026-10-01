import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The built portal is served by FastAPI (src/api/static.py); `npm run dev` proxies /api to it.
export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist", emptyOutDir: true },
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000", "/health": "http://127.0.0.1:8000" },
  },
});
