import { fileURLToPath, URL } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import {
  devAutoLoginPlugin,
  resolveDevAutoLoginConfig,
} from "./dev/dev-auto-login";

/**
 * Dev-only proxy for the QNU AI v1 API.
 *
 * Only the v1 prefix is forwarded, so the copied KTX screens cannot reach any
 * backend: their calls still die at `backend-fetch.ts`, and nothing here proxies
 * `/bff` or the KTX API.
 */
const API_V1_PREFIX = "/platform/v1alpha1";

export default defineConfig(({ command, mode, isPreview }) => {
  // Prefix "" keeps non-VITE variables in the config process only: Vite still
  // exposes nothing to the browser except VITE_* values.
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.QNU_API_PROXY_TARGET || "http://127.0.0.1:8002";
  const proxy = {
    [API_V1_PREFIX]: {
      target: apiTarget,
      changeOrigin: false,
      secure: false,
    },
  };

  // `vite build` and `vite preview` must never expose the local login bridge.
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
      port: Number(env.FRONTEND_PORT || 3001),
      strictPort: true,
      proxy,
    },
    preview: {
      host: "127.0.0.1",
      port: 3001,
      strictPort: true,
      proxy,
    },
  };
});
