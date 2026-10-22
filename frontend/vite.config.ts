import { defineConfig } from "vite";

// `npm run dev` proxies /api to the Python backend (python -m egx_monitor --server-only).
// `npm run build` writes straight into the Python package so the desktop app serves it.
export default defineConfig({
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8765" } },
  build: { outDir: "../backend/egx_monitor/static", emptyOutDir: true },
});
