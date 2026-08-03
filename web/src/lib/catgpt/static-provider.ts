import { STATIC_REPLIES } from "./static-replies.generated.ts";
import type { ReplyProvider, ReplyRequest } from "./types.ts";

type RandomSource = () => number;

function shuffle(values: readonly string[], random: RandomSource): string[] {
  const result = [...values];
  for (let index = result.length - 1; index > 0; index -= 1) {
    const choice = Math.floor(random() * (index + 1));
    [result[index], result[choice]] = [result[choice]!, result[index]!];
  }
  return result;
}

export class StaticReplyProvider implements ReplyProvider {
  private bag: string[] = [];
  private lastReply: string | undefined;
  private readonly replies: readonly string[];
  private readonly random: RandomSource;

  constructor(
    replies: readonly string[] = STATIC_REPLIES,
    random: RandomSource = Math.random,
  ) {
    if (replies.some((reply) => reply.trim().length === 0)) {
      throw new Error("StaticReplyProvider requires non-empty replies");
    }
    const uniqueReplyCount = new Set(replies).size;
    if (uniqueReplyCount < 2) {
      throw new Error("StaticReplyProvider requires at least two unique replies");
    }
    if (uniqueReplyCount !== replies.length) {
      throw new Error("StaticReplyProvider requires unique replies");
    }
    this.replies = replies;
    this.random = random;
  }

  async reply(_request: ReplyRequest): Promise<string> {
    if (this.bag.length === 0) {
      this.bag = shuffle(this.replies, this.random);
      const nextIndex = this.bag.length - 1;
      if (this.lastReply && this.bag[nextIndex] === this.lastReply) {
        [this.bag[0], this.bag[nextIndex]] = [this.bag[nextIndex]!, this.bag[0]!];
      }
    }
    const next = this.bag.pop();
    if (!next) throw new Error("StaticReplyProvider produced an empty bag");
    this.lastReply = next;
    return next;
  }
}
