/* Runs before first paint (a classic, blocking script in <head>): puts the saved or default theme on <html>, so the page
   never flashes the other theme. It reads the same localStorage key as src/userSettings.ts ("pa-settings"); a saved
   choice wins, else the build default in <meta name="pa-default-theme"> (light | dark | system; anything else is dark).
   It is a file, not an inline script, because the page's Content-Security-Policy allows scripts from 'self' only. */
(function () {
  var root = document.documentElement
  try {
    var meta = document.querySelector('meta[name="pa-default-theme"]')
    var pref = meta ? meta.getAttribute("content") : ""
    var saved = {}
    try { saved = JSON.parse(window.localStorage.getItem("pa-settings") || "{}") || {} } catch (e) { saved = {} }
    if (saved.theme === "light" || saved.theme === "dark" || saved.theme === "system") pref = saved.theme
    if (pref !== "light" && pref !== "system") pref = "dark"
    var theme = pref === "system" ? (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark") : pref
    root.setAttribute("data-theme", theme)
    root.style.colorScheme = theme
    var density = saved.density === "compact" ? "compact" : "comfortable"
    root.setAttribute("data-density", density)
    root.setAttribute("data-motion", saved.motion === "on" || saved.motion === "off" ? saved.motion : "system")
    root.setAttribute("data-footnotes", saved.footnotes === "hide" ? "hide" : "show")
    var tc = document.querySelector('meta[name="theme-color"]')
    if (tc) tc.setAttribute("content", theme === "light" ? "#f4f5f8" : "#0e0e10")
  } catch (e) {
    root.setAttribute("data-theme", "dark")
  }
})()
