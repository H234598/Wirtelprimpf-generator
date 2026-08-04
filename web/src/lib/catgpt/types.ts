export type CatGptMode = "static" | "light";
export type ChatRole = "user" | "assistant";

export const MAX_CHAT_MESSAGE_CODE_POINTS = 1000;

export function isValidChatContent(value: unknown): value is string {
  return typeof value === "string"
    && value.trim().length > 0
    && Array.from(value).length <= MAX_CHAT_MESSAGE_CODE_POINTS;
}

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ReplyRequest {
  message: string;
  history: readonly ChatMessage[];
}

export interface ReplyProvider {
  reply(request: ReplyRequest): Promise<string>;
}
