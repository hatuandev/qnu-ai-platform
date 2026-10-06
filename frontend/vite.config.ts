import { fileURLToPath, URL } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [
    tanstackRouter({
      target: "react",
      autoCodeSplitting: true,
    }),
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 3000,
    strictPort: true,
    host: true,
    proxy: {
      "/platform/v1alpha1": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
      "/health": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules")) {
            if (id.includes("@xyflow")) {
              return "vendor-xyflow";
            }
            if (id.includes("react-pdf") || id.includes("pdfjs-dist")) {
              return "vendor-pdf";
            }
            if (
              id.includes("react-markdown") ||
              id.includes("remark-gfm") ||
              id.includes("micromark") ||
              id.includes("mdast") ||
              id.includes("unist") ||
              id.includes("vfile")
            ) {
              return "vendor-markdown";
            }
            if (id.includes("xlsx")) {
              return "vendor-xlsx";
            }
            if (id.includes("recharts")) {
              return "vendor-charts";
            }
            if (id.includes("@tanstack")) {
              return "vendor-tanstack";
            }
            if (
              id.includes("@radix-ui") ||
              id.includes("lucide-react") ||
              id.includes("cmdk") ||
              id.includes("sonner")
            ) {
              return "vendor-ui";
            }
            if (id.includes("react") || id.includes("react-dom")) {
              return "vendor-react";
            }
          }
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
});
