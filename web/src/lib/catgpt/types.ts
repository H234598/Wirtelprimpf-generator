export type CatGptMode = "static" | "light";
export type ChatRole = "user" | "assistant";

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
