// Per-browser display settings (Settings workspace, 2026-11-27). They live in this browser's localStorage under one key and
// never reach the server: teammates share UAT sign-ins, so a choice belongs to the browser, not the login. Every storage
// access is wrapped, and the defaults below apply when storage is unavailable.
//
// public/theme-init.js reads the same key before first paint (a classic external script, because the page's CSP allows
// scripts from 'self' only) and sets the same attributes on <html>; applySettings() keeps them in step afterwards.
import { useSyncExternalStore } from "react"

export type ThemePref = "light" | "dark" | "system"
export type MotionPref = "system" | "on" | "off"       // "Reduce motion": follow the system, always reduce, never reduce
export type Density = "comfortable" | "compact"
export type DateStyle = "long" | "iso"                   // "Oct 5, 2026" or "2026-10-05"
export type Footnotes = "show" | "hide"
export type Engine = "scripted" | "agent"

export type Settings = {
  theme: ThemePref
  motion: MotionPref
  density: Density
  dateStyle: DateStyle
  footnotes: Footnotes
  defaultBrand: string       // "" = the first brand the API lists
  defaultEngine: Engine
}

export const SETTINGS_KEY = "pa-settings"

/** The theme a browser with no saved choice gets. Set at build time with VITE_PHARMAGENTICS_DEFAULT_THEME (light | dark | system); unset or anything else is dark. */
export const BUILD_DEFAULT_THEME: ThemePref = (() => {
  const v = String(import.meta.env.VITE_PHARMAGENTICS_DEFAULT_THEME ?? "").trim().toLowerCase()
  return v === "light" || v === "system" ? v : "dark"
})()

/** The app version: the git short sha injected at build, else "dev". */
export const APP_VERSION: string = typeof __PA_APP_VERSION__ === "string" && __PA_APP_VERSION__ ? __PA_APP_VERSION__ : "dev"

export const DEFAULTS: Settings = {
  theme: BUILD_DEFAULT_THEME, motion: "system", density: "comfortable", dateStyle: "long", footnotes: "show",
  defaultBrand: "", defaultEngine: "scripted",
}

const oneOf = <T extends string>(v: unknown, allowed: readonly T[], fallback: T): T => (allowed as readonly unknown[]).includes(v) ? v as T : fallback

function clean(raw: unknown): Settings {
  const o = raw && typeof raw === "object" ? raw as Record<string, unknown> : {}
  return {
    theme: oneOf(o.theme, ["light", "dark", "system"], DEFAULTS.theme),
    motion: oneOf(o.motion, ["system", "on", "off"], DEFAULTS.motion),
    density: oneOf(o.density, ["comfortable", "compact"], DEFAULTS.density),
    dateStyle: oneOf(o.dateStyle, ["long", "iso"], DEFAULTS.dateStyle),
    footnotes: oneOf(o.footnotes, ["show", "hide"], DEFAULTS.footnotes),
    defaultBrand: typeof o.defaultBrand === "string" && /^[A-Za-z0-9_-]{0,24}$/.test(o.defaultBrand) ? o.defaultBrand : "",
    defaultEngine: oneOf(o.defaultEngine, ["scripted", "agent"], DEFAULTS.defaultEngine),
  }
}

function read(): Settings {
  try { return clean(JSON.parse(window.localStorage.getItem(SETTINGS_KEY) || "null")) } catch { return clean(null) }
}

let current: Settings = read()
const listeners = new Set<() => void>()

export const getSettings = (): Settings => current

/** What the theme resolves to now ("system" follows the browser's colour scheme). */
export function resolvedTheme(pref: ThemePref = current.theme): "light" | "dark" {
  if (pref !== "system") return pref
  try { return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark" } catch { return "dark" }
}

/** Reflects the settings on <html>: theme, density, motion and footnotes become attributes the stylesheet reads. */
export function applySettings(s: Settings = current): void {
  try {
    const root = document.documentElement, theme = resolvedTheme(s.theme)
    root.setAttribute("data-theme", theme)
    root.style.colorScheme = theme
    root.setAttribute("data-density", s.density)
    root.setAttribute("data-motion", s.motion)
    root.setAttribute("data-footnotes", s.footnotes)
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "light" ? "#f4f5f8" : "#0e0e10")
  } catch { /* no document (tests): nothing to reflect */ }
}

export function updateSettings(patch: Partial<Settings>): void {
  const before = resolvedTheme(current.theme)
  current = clean({ ...current, ...patch })
  try { window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(current)) } catch { /* the choice lasts for this page view only */ }
  // A theme change crossfades (a view transition) unless motion is reduced; everything else applies at once.
  const d = typeof document === "undefined" ? null : document as Document & { startViewTransition?: (cb: () => void) => unknown }
  if (d?.startViewTransition && resolvedTheme(current.theme) !== before && !motionReduced(current)) d.startViewTransition(() => applySettings(current))
  else applySettings(current)
  listeners.forEach(fn => fn())
}

const subscribe = (fn: () => void) => { listeners.add(fn); return () => { listeners.delete(fn) } }

/** The settings, re-rendering the caller whenever one changes. The app root calls it, so every date and label below follows. */
export function useSettings(): Settings {
  return useSyncExternalStore(subscribe, getSettings, getSettings)
}

/** The theme in force (light or dark), live: it follows the system setting while the choice is "Match system". */
export function useResolvedTheme(): "light" | "dark" {
  const s = useSettings()
  return useSyncExternalStore(subscribeSystem, () => resolvedTheme(s.theme), () => "dark")
}

function subscribeSystem(fn: () => void): () => void {
  try {
    const q = window.matchMedia("(prefers-color-scheme: light)")
    q.addEventListener("change", fn)
    return () => q.removeEventListener("change", fn)
  } catch { return () => {} }
}

/** Reduced motion in force: the choice, or the system's setting. Animation that runs from script asks this first. */
export function motionReduced(s: Settings = current): boolean {
  if (s.motion !== "system") return s.motion === "on"
  try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches } catch { return false }
}

// While the choice is "Match system" the attribute must follow the browser's scheme as it changes.
try {
  window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => { if (current.theme === "system") { applySettings(current); listeners.forEach(fn => fn()) } })
} catch { /* no matchMedia */ }
applySettings(current)

// ---- Dates -------------------------------------------------------------------------------------------------------

/** An ISO date (2026-10-05) as the reader's chosen style: "Oct 5, 2026" or the ISO form itself. */
export function fmtIsoDate(iso: string): string {
  if (current.dateStyle === "iso") return iso
  const [y, m, d] = iso.split("-").map(Number)
  const at = new Date(Date.UTC(y, m - 1, d))
  return Number.isNaN(at.getTime()) ? iso : at.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" })
}

/** A date or timestamp from the server, shown in the chosen style (a bare ISO date is read as a local day). */
export function fmtDate(iso: string): string {
  const day = /^\d{4}-\d{2}-\d{2}$/.test(iso)
  const at = new Date(day ? `${iso}T00:00` : iso)
  if (Number.isNaN(at.getTime())) return iso
  if (current.dateStyle === "iso") {
    const p = (n: number) => String(n).padStart(2, "0")
    return `${at.getFullYear()}-${p(at.getMonth() + 1)}-${p(at.getDate())}`
  }
  return at.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

/** A timestamp with its time and zone ("Nov 23, 10:15 AM EST"; "2026-11-23 10:15 EST" in the ISO style). */
export function fmtTime(iso: string): string {
  const at = new Date(iso)
  if (Number.isNaN(at.getTime())) return iso
  const zone = new Intl.DateTimeFormat("en-US", { timeZoneName: "short" }).formatToParts(at).find(p => p.type === "timeZoneName")?.value ?? ""
  if (current.dateStyle === "iso") return `${fmtDate(iso)} ${String(at.getHours()).padStart(2, "0")}:${String(at.getMinutes()).padStart(2, "0")} ${zone}`.trim()
  return at.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" })
}

/** A short month and day for chart axes ("Oct 5", or "10-05" in the ISO style). */
export function fmtShortDay(iso: string): string {
  const at = new Date(`${iso}T00:00:00`)
  if (Number.isNaN(at.getTime())) return iso
  if (current.dateStyle === "iso") return `${String(at.getMonth() + 1).padStart(2, "0")}-${String(at.getDate()).padStart(2, "0")}`
  return at.toLocaleDateString(undefined, { month: "short", day: "numeric" })
}
