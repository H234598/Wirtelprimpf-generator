import { createHash } from "node:crypto";

import { marked } from "marked";
import sanitizeHtml from "sanitize-html";


export interface StoryPart {
  id: string;
  timestamp: string;
  markdown: string;
  html: string;
  sequence: number;
}

export interface StoryDocument {
  volume: number;
  book: number;
  storyInBook: number;
  filename: string;
  title: string;
  parts: StoryPart[];
}

export interface StoryBook {
  number: number;
  storyStart: number;
  storyEnd: number;
  stories: StoryDocument[];
}

export const STORIES_PER_BOOK = 10;


export function fallbackStoryTitle(volume: number): string {
  return `Wirtelprimpf · Story ${volume}`;
}


export type StoryPartState = "ready" | "empty";


export function classifyStoryPart(part: Pick<StoryPart, "markdown" | "html">): StoryPartState {
  return part.markdown.trim() && part.html.trim() ? "ready" : "empty";
}


export function renderSafeMarkdown(markdown: string): string {
  const rendered = marked.parse(markdown, {
    async: false,
    breaks: false,
    gfm: true,
  });
  return sanitizeHtml(String(rendered), {
    allowedTags: [
      "p", "strong", "em", "del", "blockquote", "ul", "ol", "li", "hr",
      "h2", "h3", "h4", "code", "pre", "a", "br",
    ],
    allowedAttributes: {
      a: ["href", "title"],
    },
    allowedSchemes: ["https", "http", "mailto"],
    allowProtocolRelative: false,
    disallowedTagsMode: "discard",
    transformTags: {
      a: (_tagName, attributes) => ({
        tagName: "a",
        attribs: {
          ...attributes,
          ...(attributes.href?.startsWith("http") ? { rel: "noopener noreferrer" } : {}),
        },
      }),
    },
  });
}


export function parseStoryDocument(markdown: string, filename: string, volume: number): StoryDocument {
  if (!Number.isSafeInteger(volume) || volume < 1) {
    throw new Error(`invalid story volume: ${volume}`);
  }
  const normalized = markdown.replace(/\r\n?/g, "\n");
  const titleMatch = normalized.match(/^#\s+(.+?)\s*$/m);
  const title = titleMatch?.[1]?.trim() || fallbackStoryTitle(volume);
  const heading = /^##\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*$/gm;
  const matches = [...normalized.matchAll(heading)];
  const parts = matches.map((match, index): StoryPart => {
    const timestamp = match[1];
    if (!timestamp || match.index === undefined) {
      throw new Error(`invalid story heading in ${filename}`);
    }
    const start = match.index + match[0].length;
    const end = matches[index + 1]?.index ?? normalized.length;
    const partMarkdown = normalized.slice(start, end).trim();
    const digest = createHash("sha256")
      .update(`${volume}\u0000${timestamp}\u0000${partMarkdown}`, "utf8")
      .digest("hex")
      .slice(0, 12);
    return {
      id: `band-${String(volume).padStart(4, "0")}-teil-${digest}`,
      timestamp,
      markdown: partMarkdown,
      html: renderSafeMarkdown(partMarkdown),
      sequence: index + 1,
    };
  });
  return {
    volume,
    book: Math.floor((volume - 1) / STORIES_PER_BOOK) + 1,
    storyInBook: ((volume - 1) % STORIES_PER_BOOK) + 1,
    filename,
    title,
    parts,
  };
}


export function groupStoriesByBook(stories: readonly StoryDocument[]): StoryBook[] {
  const groups = new Map<number, StoryDocument[]>();
  for (const story of [...stories].sort((left, right) => left.volume - right.volume)) {
    const group = groups.get(story.book) ?? [];
    group.push(story);
    groups.set(story.book, group);
  }
  return [...groups.entries()].map(([number, groupedStories]) => ({
    number,
    storyStart: ((number - 1) * STORIES_PER_BOOK) + 1,
    storyEnd: number * STORIES_PER_BOOK,
    stories: groupedStories,
  }));
}


export function sortStoryPartsNewestFirst(parts: readonly StoryPart[]): StoryPart[] {
  return [...parts].sort((left, right) => {
    const byTimestamp = right.timestamp.localeCompare(left.timestamp);
    return byTimestamp || right.sequence - left.sequence;
  });
}


export function assertReleaseAssetUrl(url: string, owner: string, repository: string): string {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch (error) {
    throw new Error(`invalid release asset URL: ${String(error)}`);
  }
  const segments = parsed.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  const common = parsed.protocol === "https:"
    && parsed.hostname === "github.com"
    && parsed.username === ""
    && parsed.password === ""
    && parsed.search === ""
    && parsed.hash === ""
    && segments.length === 6
    && segments[0] === owner
    && segments[1] === repository
    && segments[2] === "releases"
    && segments[3] === "download";
  const tag = segments[4] ?? "";
  const asset = segments[5] ?? "";
  const validMedia = /^archive-\d{4}-media-\d{4}$/.test(tag)
    && /^[A-Za-z0-9._-]*[a-f0-9]{16}[A-Za-z0-9._-]*$/.test(asset);
  const validEpub = /^archive-\d{4}-epub-\d{4}$/.test(tag)
    && /^[A-Za-z0-9._-]+\.epub$/i.test(asset);
  const valid = common && (validMedia || validEpub);
  if (!valid) {
    throw new Error(`release asset URL violates archive contract: ${url}`);
  }
  return url;
}
