export interface GalleryHistoryEntry {
  focusId: string;
  scrollY: number;
}


const SAFE_FOCUS_ID = /^[A-Za-z0-9._-]{1,200}$/;


function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}


export function parseGalleryHistoryEntry(value: unknown): GalleryHistoryEntry | null {
  if (!isRecord(value)) return null;
  const focusId = value.focusId;
  const scrollY = value.scrollY;
  if (typeof focusId !== "string" || !SAFE_FOCUS_ID.test(focusId)) return null;
  if (typeof scrollY !== "number" || !Number.isSafeInteger(scrollY) || scrollY < 0 || scrollY > 100_000_000) return null;
  return { focusId, scrollY };
}


export function galleryHistoryEntry(value: unknown): GalleryHistoryEntry | null {
  if (!isRecord(value)) return null;
  return parseGalleryHistoryEntry(value.gallery);
}


export function withGalleryHistoryEntry(current: unknown, entry: GalleryHistoryEntry): Record<string, unknown> {
  const base = isRecord(current) ? current : {};
  return { ...base, gallery: entry };
}


export function replaceGalleryHistory(entry: GalleryHistoryEntry): void {
  if (typeof window === "undefined") return;
  try {
    window.history.replaceState(withGalleryHistoryEntry(window.history.state, entry), "");
  } catch {
    // A history implementation can reject state cloning; the URL remains authoritative.
  }
}


export function pushGalleryHistory(url: string, entry: GalleryHistoryEntry): void {
  if (typeof window === "undefined") return;
  try {
    window.history.pushState(withGalleryHistoryEntry(window.history.state, entry), "", url);
  } catch {
    window.location.assign(url);
  }
}


export function restoreGalleryHistory(entry: GalleryHistoryEntry, fallback: HTMLElement | null = null): void {
  if (typeof window === "undefined") return;
  window.requestAnimationFrame(() => {
    window.scrollTo({ top: entry.scrollY, behavior: "auto" });
    const target = document.getElementById(entry.focusId) ?? fallback;
    target?.focus({ preventScroll: true });
  });
}
