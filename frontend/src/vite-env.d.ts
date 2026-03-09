/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_SITE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare global {
  interface Window {
    __APP_CONFIG__?: {
      API_BASE_URL?: string
      SITE_URL?: string
    }
  }
}

export {}
