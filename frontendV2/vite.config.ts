import { fileURLToPath, URL } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import {
  devAutoLoginPlugin,
  resolveDevAutoLoginConfig,
} from "./dev/dev-auto-login.ts";

const API_V1_PREFIX = "/platform/v1alpha1";

export default defineConfig(({ command, mode, isPreview }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.QNU_API_PROXY_TARGET || "http://127.0.0.1:8002";

  const isDevServer =
    command === "serve" && !isPreview && mode !== "production";
  const autoLoginConfig = resolveDevAutoLoginConfig(env, {
    devServer: isDevServer,
  });

  return {
    plugins: [
      tanstackRouter({ target: "react", autoCodeSplitting: true }),
      react(),
      tailwindcss(),
      ...(isDevServer ? [devAutoLoginPlugin(autoLoginConfig)] : []),
    ],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    optimizeDeps: {
      exclude: ["pdfjs-dist"],
    },
    server: {
      host: "127.0.0.1",
      port: Number(env.FRONTEND_V2_PORT || 3002),
      strictPort: false,
      proxy: {
        [API_V1_PREFIX]: {
          target: apiTarget,
          changeOrigin: false,
          secure: false,
        },
      },
    },
    preview: {
      host: "127.0.0.1",
      port: 3002,
      strictPort: false,
    },
  };
});
