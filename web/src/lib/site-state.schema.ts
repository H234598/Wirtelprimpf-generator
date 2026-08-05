import type { Theme } from "./catgpt/settings.ts";
import type { GalleryType } from "./routes.ts";


export const SITE_STATE_KEY = "wirtelprimpf.site-state.v1";
export const SITE_STATE_VERSION = 1 as const;
export const MAX_SITE_STATE_BYTES = 64 * 1024;
export const MAX_PROGRESS_ENTRIES = 500;
export const MAX_FAVORITES = 100;

export type ReadingView = "band" | "chapter";

export interface GalleryReturnState {
  typ: GalleryType;
  seite: number;
  jahr: number | null;
  focus_id: string | null;
  scroll_y: number;
}

export interface ReadingProgress {
  position: number;
  anchor: string | null;
}

export interface SiteState {
  schema_version: typeof SITE_STATE_VERSION;
  theme: Theme;
  reading_view: ReadingView;
  gallery: GalleryReturnState;
  progress: Record<string, ReadingProgress>;
  favorites: string[];
}
