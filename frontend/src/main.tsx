import { createRouter, RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { installAuthFetchInterceptor } from "@/app/auth/fetch-interceptor";
import { AppProviders } from "@/app/providers";
import { routeTree } from "./routeTree.gen";
import "@/styles/globals.css";

// Khởi chạy bộ chặn Fetch toàn cục để tự động gắn Bearer Token cho các API Backend
installAuthFetchInterceptor();

const router = createRouter({
  routeTree,
  defaultPreload: "intent",
  scrollRestoration: true,
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

const rootElement = document.getElementById("root");
if (rootElement) {
  createRoot(rootElement).render(
    <StrictMode>
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>
    </StrictMode>,
  );
}
