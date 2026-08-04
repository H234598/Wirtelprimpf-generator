export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ChatRequest {
  message: string;
  history: ChatMessage[];
}

const codepoints = (value: string): number => [...value].length;

function parseMessage(value: unknown): ChatMessage {
  if (!value || typeof value !== "object") throw new TypeError("invalid message");
  const item = value as Record<string, unknown>;
  if ((item.role !== "user" && item.role !== "assistant") || typeof item.content !== "string") {
    throw new TypeError("invalid message");
  }
  const content = item.content.trim();
  if (!content || codepoints(content) > 1_000) throw new TypeError("invalid message");
  return { role: item.role, content };
}

export function parseChatRequest(value: unknown): ChatRequest {
  if (!value || typeof value !== "object") throw new TypeError("invalid request");
  const item = value as Record<string, unknown>;
  if (typeof item.message !== "string" || !Array.isArray(item.history)) {
    throw new TypeError("invalid request");
  }
  const message = item.message.trim();
  if (!message || codepoints(message) > 1_000 || item.history.length > 10) {
    throw new TypeError("invalid request");
  }
  return { message, history: item.history.map(parseMessage) };
}

export function isAllowedOrigin(origin: string | null, extraOrigins: string): boolean {
  if (!origin) return false;
  if (origin === "https://wirtelprimpf.telacore.org") return true;
  if (/^https:\/\/wirtelprimpf-\d{4}\.telacore\.org$/.test(origin)) return true;
  const extras = extraOrigins.split(",").map((item) => item.trim()).filter(Boolean);
  return extras.includes(origin);
}
