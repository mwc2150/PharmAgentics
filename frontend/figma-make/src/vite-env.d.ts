/// <reference types="vite/client" />
interface ImportMetaEnv { readonly VITE_PHARMAGENTICS_API_BASE_URL?: string; readonly VITE_PHARMAGENTICS_DEFAULT_THEME?: string }
interface ImportMeta { readonly env: ImportMetaEnv }
declare const __PA_APP_VERSION__: string | undefined  // the git short sha, injected by vite.config.standalone.ts
