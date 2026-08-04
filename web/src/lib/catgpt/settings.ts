import type { CatGptMode } from "./types.ts";

export type Theme = "night" | "paper";
export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}
export type StorageGetter = () => StorageLike;

export const CATGPT_MODE_CHANGE_EVENT = "catgpt:modechange";
export const CATGPT_HISTORY_KEY = "wirtelprimpf-catgpt-history";
const THEME_KEY = "wirtelprimpf-theme";
const MODE_KEY = "wirtelprimpf-catgpt-mode";

export function readTheme(storage: StorageLike): Theme {
  return storage.getItem(THEME_KEY) === "paper" ? "paper" : "night";
}

export function writeTheme(storage: StorageLike, theme: Theme): void {
  storage.setItem(THEME_KEY, theme);
}

export function readMode(storage: StorageLike): CatGptMode {
  return storage.getItem(MODE_KEY) === "light" ? "light" : "static";
}

export function writeMode(storage: StorageLike, mode: CatGptMode): void {
  storage.setItem(MODE_KEY, mode);
}

export function initializeCatGptMode(
  getStorage: StorageGetter,
  lightAvailable: boolean,
): CatGptMode {
  if (!lightAvailable) {
    try { writeMode(getStorage(), "static"); } catch {}
    return "static";
  }
  try { return readMode(getStorage()); } catch { return "static"; }
}

export function clearChatSession(storage: StorageLike): void {
  storage.removeItem(CATGPT_HISTORY_KEY);
}

export function changeCatGptMode(
  getModeStorage: StorageGetter,
  getChatStorage: StorageGetter,
  mode: CatGptMode,
  eventTarget: Pick<EventTarget, "dispatchEvent">,
): void {
  try { writeMode(getModeStorage(), mode); } catch {}
  try { clearChatSession(getChatStorage()); } catch {}
  eventTarget.dispatchEvent(new CustomEvent(CATGPT_MODE_CHANGE_EVENT, { detail: { mode } }));
}
