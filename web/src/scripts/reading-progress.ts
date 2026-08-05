import { readSiteState, updateSiteState } from "../lib/site-state.ts";
import { isSafeChapterId } from "../lib/story-routes.ts";
import type { StorageLike } from "../lib/catgpt/settings.ts";


export function viewportProgress(scrollY: number, scrollHeight: number, viewportHeight: number): number {
  if (!Number.isFinite(scrollY) || !Number.isFinite(scrollHeight) || !Number.isFinite(viewportHeight)) return 0;
  const maximum = Math.max(0, scrollHeight - viewportHeight);
  if (maximum === 0) return 100;
  return Math.min(100, Math.max(0, Math.round((scrollY / maximum) * 100)));
}


export function saveReadingProgress(storage: StorageLike, chapterId: string, position: number): boolean {
  if (!isSafeChapterId(chapterId)) return false;
  return updateSiteState(storage, (state) => ({
    ...state,
    progress: {
      ...state.progress,
      [chapterId]: { position: Math.min(100, Math.max(0, Math.round(position))), anchor: null },
    },
  }));
}


function mount(root: HTMLElement): void {
  const chapterId = root.dataset.chapterId;
  const control = root.querySelector<HTMLElement>("[data-reading-control]");
  const save = root.querySelector<HTMLButtonElement>("[data-reading-save]");
  const status = root.querySelector<HTMLElement>("[data-reading-status]");
  if (!chapterId || !control || !save || !status || !isSafeChapterId(chapterId)) return;
  control.hidden = false;
  const storage = (() => { try { return localStorage; } catch { return null; } })();
  if (!storage) return;
  const existing = readSiteState(storage).progress[chapterId];
  if (existing && existing.position > 0 && existing.position < 100) {
    window.setTimeout(() => {
      const maximum = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
      window.scrollTo({ top: maximum * existing.position / 100, behavior: "auto" });
    }, 0);
  }
  const announce = (message: string): void => { status.textContent = message; };
  save.addEventListener("click", () => {
    if (saveReadingProgress(storage, chapterId, 100)) announce("Lesefortschritt gespeichert.");
  });
  let scheduled = false;
  window.addEventListener("scroll", () => {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(() => {
      scheduled = false;
      saveReadingProgress(storage, chapterId, viewportProgress(window.scrollY, document.documentElement.scrollHeight, window.innerHeight));
    });
  }, { passive: true });
}


const root = typeof document === "undefined" ? null : document.querySelector<HTMLElement>("[data-reading-progress]");
if (root) mount(root);
