// Build config for running this UI outside Figma Make (local Vite, container image).
// vite.config.ts stays the Figma Make config; it imports .figma/make/site.json, which
// only exists inside Figma Make. This file fills the figma:* placeholders in index.html.
import { defineConfig, loadEnv, type Plugin } from "vite"
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
        // The design tool's scaffold markers (figma:head-start, body-end ...) are not served (UAT review 5.7).
        .replace(/[ \t]*<!-- figma:[\w-]+ -->[ \t]*\r?\n?/g, "")
    },
  }
}

export default defineConfig(({ mode }) => {
  // The shell environment and .env files (shell wins), so a value set either way is honoured.
  const env = loadEnv(mode, __dirname, "")
  const api = env.PHARMAGENTICS_API || "http://127.0.0.1:8000"
  const port = Number(env.PHARMAGENTICS_UI_PORT || 5173)
  if (!Number.isInteger(port)) throw new Error(`PHARMAGENTICS_UI_PORT must be a port number, got "${env.PHARMAGENTICS_UI_PORT}"`)
  return {
    base: "/",
    plugins: [react(), tailwindcss(), standaloneHtml()],
    resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
    // Same origin unless set (the Dockerfile sets "." too); the dev server proxies /api and /auth.
    define: {
      "import.meta.env.VITE_PHARMAGENTICS_API_BASE_URL": JSON.stringify(env.VITE_PHARMAGENTICS_API_BASE_URL || "."),
    },
    server: {
      // PHARMAGENTICS_UI_PORT lets several worktrees serve side by side against one API.
      port,
      strictPort: true,
      // Local dev: forward API and sign-in calls to
      // `PHARMAGENTICS_AUTH=dev uv run uvicorn pharmagentics.api.app:app --app-dir src --port 8000`.
      proxy: { "/api": api, "/auth": api },
    },
  }
})
