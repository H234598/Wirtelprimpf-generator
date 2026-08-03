import type { CatGptMode } from "./types.ts";

export type Theme = "night" | "paper";
export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

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

export function clearChatSession(storage: StorageLike): void {
  storage.removeItem(CATGPT_HISTORY_KEY);
}
