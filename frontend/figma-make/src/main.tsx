import React from "react"
import ReactDOM from "react-dom/client"
import App from "./App"
import { HoverTips } from "./HoverTips"
import "./index.css"

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
    <HoverTips />
  </React.StrictMode>,
)
