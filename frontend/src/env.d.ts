interface ImportMetaEnv {
  /** Backend origin, e.g. https://api.example.com (no trailing slash needed). */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
