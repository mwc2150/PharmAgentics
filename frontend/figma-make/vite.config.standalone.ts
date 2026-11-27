// Build config for running this UI outside Figma Make (local Vite, container image).
// vite.config.ts stays the Figma Make config; it imports .figma/make/site.json, which
// only exists inside Figma Make. This file fills the figma:* placeholders in index.html.
import { defineConfig, loadEnv, type Plugin } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import path from "node:path"
import { execSync } from "node:child_process"

// The theme a browser with no saved choice gets: VITE_PHARMAGENTICS_DEFAULT_THEME (light | dark | system); unset or anything else is dark.
function defaultTheme(value: string | undefined): "light" | "dark" | "system" {
  const v = (value || "").trim().toLowerCase()
  return v === "light" || v === "system" ? v : "dark"
}

// The app version shown under Settings > About: the git short sha, or "dev" when there is no git (a container build without .git).
function appVersion(override: string | undefined): string {
  if (override && /^[\w.-]{1,40}$/.test(override)) return override
  try { return execSync("git rev-parse --short HEAD", { cwd: __dirname, stdio: ["ignore", "pipe", "ignore"] }).toString().trim() || "dev" } catch { return "dev" }
}

function standaloneHtml(theme: string): Plugin {
  return {
    name: "pharmagentics-standalone-html",
    transformIndexHtml(html) {
      return html
        .replace("<!-- figma:lang -->", "en")
        .replace("<!-- figma:title -->", "PharmAgentics")
        .replace("<!-- pa:default-theme -->", theme)
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
    plugins: [react(), tailwindcss(), standaloneHtml(defaultTheme(env.VITE_PHARMAGENTICS_DEFAULT_THEME))],
    resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
    // Same origin unless set (the Dockerfile sets "." too); the dev server proxies /api and /auth.
    define: {
      "import.meta.env.VITE_PHARMAGENTICS_API_BASE_URL": JSON.stringify(env.VITE_PHARMAGENTICS_API_BASE_URL || "."),
      "import.meta.env.VITE_PHARMAGENTICS_DEFAULT_THEME": JSON.stringify(defaultTheme(env.VITE_PHARMAGENTICS_DEFAULT_THEME)),
      __PA_APP_VERSION__: JSON.stringify(appVersion(env.PHARMAGENTICS_APP_VERSION)),
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
