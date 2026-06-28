import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/app/",
  server: {
    port: 5173,
    proxy: {
      "/health": "http://127.0.0.1:8091",
      "/metrics": "http://127.0.0.1:8091",
      "/math": "http://127.0.0.1:8091",
      "/viz": "http://127.0.0.1:8091",
      "/data": "http://127.0.0.1:8091",
      "/observatory": "http://127.0.0.1:8091",
      "/stream": "http://127.0.0.1:8091",
    },
  },
});
