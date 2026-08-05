import {
  GALLERY_TYPES,
  type GalleryType,
} from "./routes.ts";
import type { StorageLike } from "./catgpt/settings.ts";
import {
  MAX_FAVORITES,
  MAX_PROGRESS_ENTRIES,
  MAX_SITE_STATE_BYTES,
  SITE_STATE_KEY,
  SITE_STATE_VERSION,
  type ReadingProgress,
  type SiteState,
} from "./site-state.schema.ts";


const LEGACY_THEME_KEY = "wirtelprimpf-theme";
const SAFE_ID = /^[A-Za-z0-9._-]{1,200}$/;
const SAFE_ANCHOR = /^[A-Za-z0-9._-]{1,200}$/;
const GALLERY_TYPE_SET = new Set<string>(GALLERY_TYPES);


export type SiteStateAliases = Readonly<Record<string, string>>;


export function defaultSiteState(): SiteState {
  return {
    schema_version: SITE_STATE_VERSION,
    theme: "night",
    reading_view: "chapter",
    gallery: {
      typ: "all",
      seite: 1,
      jahr: null,
      focus_id: null,
      scroll_y: 0,
    },
    progress: {},
    favorites: [],
  };
}


function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}


function isSafeId(value: unknown): value is string {
  return typeof value === "string" && SAFE_ID.test(value);
}


function isSafeAnchor(value: unknown): value is string {
  return typeof value === "string" && SAFE_ANCHOR.test(value);
}


function isPositivePage(value: unknown): value is number {
  return Number.isSafeInteger(value) && Number(value) > 0;
}


function isScroll(value: unknown): value is number {
  return Number.isSafeInteger(value) && Number(value) >= 0 && Number(value) <= 100_000_000;
}


function resolveAlias(value: string, aliases: SiteStateAliases): string | null {
  let current = value;
  const seen = new Set<string>();
  for (let step = 0; step <= 8; step += 1) {
    if (seen.has(current)) return null;
    seen.add(current);
    const next = aliases[current];
    if (!next) return current;
    if (!isSafeId(next)) return null;
    current = next;
  }
  return null;
}


function migrateProgress(value: unknown, aliases: SiteStateAliases): Record<string, ReadingProgress> | null {
  if (!isRecord(value) || Object.keys(value).length > MAX_PROGRESS_ENTRIES) return null;
  const result: Record<string, ReadingProgress> = {};
  for (const [rawId, rawProgress] of Object.entries(value)) {
    if (!isSafeId(rawId)) return null;
    const id = resolveAlias(rawId, aliases);
    if (!id || !isSafeId(id) || !isRecord(rawProgress)) return null;
    const position = rawProgress.position;
    const anchor = rawProgress.anchor;
    if (!Number.isSafeInteger(position) || Number(position) < 0 || Number(position) > 100_000_000) return null;
    if (anchor !== null && !isSafeAnchor(anchor)) return null;
    result[id] = { position: Number(position), anchor: anchor as string | null };
  }
  return result;
}


function migrateFavorites(value: unknown, aliases: SiteStateAliases): string[] | null {
  if (!Array.isArray(value) || value.length > MAX_FAVORITES) return null;
  const result: string[] = [];
  for (const rawId of value) {
    if (!isSafeId(rawId)) return null;
    const id = resolveAlias(rawId, aliases);
    if (!id) return null;
    if (!result.includes(id)) result.push(id);
  }
  return result;
}


export function migrateSiteState(value: unknown, aliases: SiteStateAliases = {}): SiteState | null {
  if (!isRecord(value) || value.schema_version !== SITE_STATE_VERSION) return null;
  const gallery = value.gallery;
  if (!isRecord(gallery)) return null;
  if (!GALLERY_TYPE_SET.has(String(gallery.typ)) || !isPositivePage(gallery.seite)) return null;
  if (gallery.jahr !== null && (!Number.isSafeInteger(gallery.jahr) || Number(gallery.jahr) < 1000 || Number(gallery.jahr) > 9999)) return null;
  if (gallery.focus_id !== null && !isSafeId(gallery.focus_id)) return null;
  if (!isScroll(gallery.scroll_y)) return null;
  if (value.theme !== "night" && value.theme !== "paper") return null;
  if (value.reading_view !== "band" && value.reading_view !== "chapter") return null;
  const progress = migrateProgress(value.progress, aliases);
  const favorites = migrateFavorites(value.favorites, aliases);
  if (!progress || !favorites) return null;
  const year: number | null = gallery.jahr === null ? null : Number(gallery.jahr);
  return {
    schema_version: SITE_STATE_VERSION,
    theme: value.theme,
    reading_view: value.reading_view,
    gallery: {
      typ: gallery.typ as GalleryType,
      seite: gallery.seite,
      jahr: year,
      focus_id: gallery.focus_id,
      scroll_y: gallery.scroll_y,
    },
    progress,
    favorites,
  };
}


export function serializeSiteState(state: SiteState): string {
  const migrated = migrateSiteState(state);
  if (!migrated) throw new Error("cannot serialize invalid site state");
  const serialized = JSON.stringify(migrated);
  if (new TextEncoder().encode(serialized).byteLength > MAX_SITE_STATE_BYTES) {
    throw new Error("site state exceeds 64 KiB");
  }
  return serialized;
}


export function parseSiteState(raw: string | null, aliases: SiteStateAliases = {}): SiteState {
  if (!raw) return defaultSiteState();
  try {
    const parsed: unknown = JSON.parse(raw);
    return migrateSiteState(parsed, aliases) ?? defaultSiteState();
  } catch {
    return defaultSiteState();
  }
}


export function readSiteState(storage: StorageLike, aliases: SiteStateAliases = {}): SiteState {
  try {
    const raw = storage.getItem(SITE_STATE_KEY);
    if (raw) return parseSiteState(raw, aliases);
    const legacyTheme = storage.getItem(LEGACY_THEME_KEY);
    return legacyTheme === "paper" ? { ...defaultSiteState(), theme: "paper" } : defaultSiteState();
  } catch {
    return defaultSiteState();
  }
}


export function writeSiteState(storage: StorageLike, state: SiteState): boolean {
  try {
    storage.setItem(SITE_STATE_KEY, serializeSiteState(state));
    return true;
  } catch {
    return false;
  }
}


export function updateSiteState(
  storage: StorageLike,
  update: (state: SiteState) => SiteState,
  aliases: SiteStateAliases = {},
): boolean {
  const next = update(readSiteState(storage, aliases));
  return writeSiteState(storage, next);
}


export function clearSiteState(storage: StorageLike): boolean {
  try {
    storage.removeItem(SITE_STATE_KEY);
    return true;
  } catch {
    return false;
  }
}
