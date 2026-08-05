import { readSiteState, updateSiteState } from "../lib/site-state.ts";
import type { StorageLike } from "../lib/catgpt/settings.ts";


const SAFE_ID = /^[A-Za-z0-9._-]{1,200}$/;


export function toggleFavorite(storage: StorageLike, assetId: string): boolean | null {
  if (!SAFE_ID.test(assetId)) return null;
  let result: boolean | null = null;
  const written = updateSiteState(storage, (state) => {
    const active = state.favorites.includes(assetId);
    const favorites = active
      ? state.favorites.filter((id) => id !== assetId)
      : [...state.favorites, assetId].slice(-100);
    result = !active;
    return { ...state, favorites };
  });
  return written ? result : null;
}


function mount(): void {
  const buttons = [...document.querySelectorAll<HTMLButtonElement>("[data-favorite-id]")];
  if (!buttons.length) return;
  const storage = (() => { try { return localStorage; } catch { return null; } })();
  if (!storage) return;
  const sync = (button: HTMLButtonElement): void => {
    const id = button.dataset.favoriteId;
    if (!id) return;
    const active = readSiteState(storage).favorites.includes(id);
    button.hidden = false;
    button.setAttribute("aria-pressed", String(active));
    button.textContent = active ? "Aus Favoriten entfernen" : "Als Favorit merken";
  };
  for (const button of buttons) {
    sync(button);
    button.addEventListener("click", () => {
      const id = button.dataset.favoriteId;
      if (id) toggleFavorite(storage, id);
      sync(button);
    });
  }
}


if (typeof document !== "undefined") mount();
