/// <reference types="astro/client" />

interface ImportMetaEnv {
  readonly PUBLIC_CATGPT_LIGHT_ENDPOINT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
