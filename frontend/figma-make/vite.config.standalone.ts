// Build config for running this UI outside Figma Make (local Vite, container image).
// vite.config.ts stays the Figma Make config; it imports .figma/make/site.json, which
// only exists inside Figma Make. This file fills the figma:* placeholders in index.html.
import { defineConfig, type Plugin } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import path from "node:path"

function standaloneHtml(): Plugin {
  return {
    name: "pharmagentics-standalone-html",
    transformIndexHtml(html) {
      return html
        .replace("<!-- figma:lang -->", "en")
        .replace("<!-- figma:title -->", "PharmAgentics")
    },
  }
}

export default defineConfig({
  base: "/",
  plugins: [react(), tailwindcss(), standaloneHtml()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  // Same origin by default (the Dockerfile sets "." too); the dev server proxies /api and /auth.
  define: {
    "import.meta.env.VITE_PHARMAGENTICS_API_BASE_URL": JSON.stringify(process.env.VITE_PHARMAGENTICS_API_BASE_URL ?? "."),
  },
  server: {
    // PORT lets several worktrees serve side by side against one API.
    port: Number(process.env.PORT ?? 5173),
    strictPort: true,
    // Local dev: forward API and sign-in calls to
    // `PHARMAGENTICS_AUTH=dev uv run uvicorn pharmagentics.api.app:app --app-dir src --port 8000`.
    proxy: {
      "/api": process.env.PHARMAGENTICS_API ?? "http://127.0.0.1:8000",
      "/auth": process.env.PHARMAGENTICS_API ?? "http://127.0.0.1:8000",
    },
  },
})
