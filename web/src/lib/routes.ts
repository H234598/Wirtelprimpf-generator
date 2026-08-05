import type { MediaItem, MediaKind } from "./data.ts";


export const GALLERY_PAGE_SIZE = 24;
export const GALLERY_TYPES = ["all", "story", "classic", "legacy", "unknown"] as const;
export type GalleryType = typeof GALLERY_TYPES[number];

export interface GalleryState {
  typ: GalleryType;
  seite: number;
  jahr: number | null;
}

const TYPE_SET = new Set<string>(GALLERY_TYPES);


function parsePage(value: string | null): number {
  if (!value || !/^\d+$/.test(value)) return 1;
  const page = Number(value);
  return Number.isSafeInteger(page) && page > 0 ? page : 1;
}


function parseYear(value: string | null): number | null {
  if (!value || !/^\d{4}$/.test(value)) return null;
  const year = Number(value);
  return year >= 1000 && year <= 9999 ? year : null;
}


export function parseGalleryQuery(input: string | URLSearchParams): GalleryState {
  const params = typeof input === "string" ? new URLSearchParams(input.replace(/^\?/, "")) : input;
  const type = params.get("typ");
  return {
    typ: type && TYPE_SET.has(type) ? type as GalleryType : "all",
    seite: parsePage(params.get("seite")),
    jahr: parseYear(params.get("jahr")),
  };
}


export function filterGalleryMedia(items: readonly MediaItem[], state: GalleryState): MediaItem[] {
  return items.filter((item) => {
    const typeMatches = state.typ === "all" || item.kind === state.typ as MediaKind;
    const yearMatches = state.jahr === null || item.year === state.jahr;
    return typeMatches && yearMatches;
  });
}


export function galleryPageCount(items: readonly MediaItem[], state: GalleryState): number {
  return Math.max(1, Math.ceil(filterGalleryMedia(items, state).length / GALLERY_PAGE_SIZE));
}


export function normalizeGalleryState(
  state: GalleryState,
  options: { items?: readonly MediaItem[]; page?: number } = {},
): GalleryState {
  const validYears = options.items
    ? new Set(options.items.map((item) => item.year).filter((year): year is number => year !== null))
    : null;
  const year = state.jahr !== null && (!validYears || validYears.has(state.jahr)) ? state.jahr : null;
  const next = { ...state, jahr: year, seite: options.page ?? state.seite };
  if (!options.items) return next;
  const pageCount = galleryPageCount(options.items, next);
  return { ...next, seite: Math.min(Math.max(1, next.seite), pageCount) };
}


export function galleryPageItems(items: readonly MediaItem[], state: GalleryState): MediaItem[] {
  const filtered = filterGalleryMedia(items, state);
  const start = (state.seite - 1) * GALLERY_PAGE_SIZE;
  return filtered.slice(start, start + GALLERY_PAGE_SIZE);
}


export function availableGalleryYears(items: readonly MediaItem[]): number[] {
  return [...new Set(items.map((item) => item.year).filter((year): year is number => year !== null))]
    .sort((left, right) => right - left);
}


export function serializeGalleryQuery(state: GalleryState): string {
  const params = new URLSearchParams();
  if (state.typ !== "all") params.set("typ", state.typ);
  if (state.seite > 1) params.set("seite", String(state.seite));
  if (state.jahr !== null) params.set("jahr", String(state.jahr));
  const query = params.toString();
  return query ? `?${query}` : "";
}


export function galleryPagePath(page: number): string {
  return page <= 1 ? "/bilder/" : `/bilder/seite/${page}/`;
}


export function galleryUrl(pathname: string, state: GalleryState): string {
  return `${pathname}${serializeGalleryQuery(state)}`;
}


export function neighboringMedia(
  items: readonly MediaItem[],
  assetId: string,
): { previous: MediaItem | null; next: MediaItem | null } {
  const index = items.findIndex((item) => item.asset_id === assetId);
  if (index < 0) return { previous: null, next: null };
  return {
    previous: items[index - 1] ?? null,
    next: items[index + 1] ?? null,
  };
}
