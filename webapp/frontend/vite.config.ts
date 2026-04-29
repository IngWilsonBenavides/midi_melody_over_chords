import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendUrl = env.BACKEND_URL || "http://localhost:8000";

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      watch: {
        // Needed for Docker bind-mount file watching
        usePolling: true,
      },
      proxy: {
        "/api": {
          target: backendUrl,
          changeOrigin: true,
        },
        // Proxy admin and static from Django too (convenience)
        "/admin": {
          target: backendUrl,
          changeOrigin: true,
        },
      },
    },
  };
});
