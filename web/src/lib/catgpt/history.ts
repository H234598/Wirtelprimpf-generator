import {
  CATGPT_HISTORY_KEY,
  type StorageGetter,
  type StorageLike,
} from "./settings.ts";
import type { ChatMessage } from "./types.ts";

const MAX_HISTORY_LENGTH = 10;

function isChatMessage(value: unknown): value is ChatMessage {
  if (!value || typeof value !== "object") return false;
  const message = value as Record<string, unknown>;
  return Object.keys(message).length === 2
    && (message.role === "user" || message.role === "assistant")
    && typeof message.content === "string"
    && message.content.trim().length > 0;
}

export function readChatHistory(storage: StorageLike | StorageGetter): ChatMessage[] {
  try {
    const resolvedStorage = typeof storage === "function" ? storage() : storage;
    const value: unknown = JSON.parse(resolvedStorage.getItem(CATGPT_HISTORY_KEY) ?? "[]");
    if (!Array.isArray(value) || !value.every(isChatMessage)) return [];
    return value.slice(-MAX_HISTORY_LENGTH);
  } catch {
    return [];
  }
}

export function writeChatHistory(storage: StorageLike, history: readonly ChatMessage[]): void {
  storage.setItem(
    CATGPT_HISTORY_KEY,
    JSON.stringify(history.filter(isChatMessage).slice(-MAX_HISTORY_LENGTH)),
  );
}
