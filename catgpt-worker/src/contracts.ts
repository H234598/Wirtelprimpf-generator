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

function isIpv4(value: string): boolean {
  const octets = value.split(".");
  return octets.length === 4 && octets.every((octet) =>
    /^(?:0|[1-9]\d{0,2})$/.test(octet) && Number(octet) <= 255
  );
}

function isIpv6(value: string): boolean {
  let address = value;
  if (address.includes(".")) {
    const separator = address.lastIndexOf(":");
    if (separator < 0 || !isIpv4(address.slice(separator + 1))) return false;
    address = `${address.slice(0, separator + 1)}0:0`;
  }

  const halves = address.split("::");
  if (halves.length > 2) return false;
  const groups = halves.flatMap((half) => half ? half.split(":") : []);
  if (!groups.every((group) => /^[0-9a-fA-F]{1,4}$/.test(group))) return false;
  return halves.length === 2 ? groups.length < 8 : groups.length === 8;
}

export function isClientIpLiteral(value: string): boolean {
  if (!value || /\s/.test(value)) return false;
  return value.includes(":") ? isIpv6(value) : isIpv4(value);
}
