import { existsSync, readFileSync, readdirSync } from "node:fs";
import { basename, resolve } from "node:path";

import {
  STORIES_PER_BOOK,
  assertReleaseAssetUrl,
  parseStoryDocument,
  type StoryDocument,
} from "./content.ts";


export type SiteProfile = "hub" | "archive";

export interface ArchiveEntry {
  archive_index: number;
  repository: string;
  github_url: string;
  pages_url: string;
  volume_start: number;
  volume_end: number;
  book_start: number;
  book_end: number;
  active: boolean;
  sealed: boolean;
  verified: boolean;
  revision: string | null;
}


export function archiveBookRange(archiveIndex: number): { bookStart: number; bookEnd: number } {
  if (!Number.isSafeInteger(archiveIndex) || archiveIndex < 1) {
    throw new Error(`archive index must be a positive integer: ${archiveIndex}`);
  }
  const firstStory = ((archiveIndex - 1) * 50) + 1;
  const lastStory = firstStory + 49;
  return {
    bookStart: Math.floor((firstStory - 1) / STORIES_PER_BOOK) + 1,
    bookEnd: Math.floor((lastStory - 1) / STORIES_PER_BOOK) + 1,
  };
}

export interface MediaVariant {
  requested_width: number;
  actual_width: number;
  actual_height: number;
  url: string;
  mime_type: string;
}

export interface MediaItem {
  asset_id: string;
  source_path: string;
  kind: "story" | "classic" | "legacy";
  width: number;
  height: number;
  release_tag: string;
  original: { asset_name: string; url: string };
  variants: MediaVariant[];
}

export interface SiteData {
  profile: SiteProfile;
  archiveIndex: number;
  repository: string;
  domain: string;
  title: string;
  intro: string;
  catalog: ArchiveEntry[];
  stories: StoryDocument[];
  currentStory: StoryDocument | null;
  media: MediaItem[];
  generatedAt: string | null;
}


function readJson(path: string, required = true): unknown {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    if (!required && (error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw new Error(`cannot read validated site data ${path}: ${String(error)}`);
  }
}


function objectValue(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${label} must be an object`);
  return value as Record<string, unknown>;
}


function stringValue(value: unknown, label: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${label} must be a non-empty string`);
  return value;
}


function integerValue(value: unknown, label: string): number {
  if (!Number.isSafeInteger(value) || Number(value) < 1) throw new Error(`${label} must be a positive integer`);
  return Number(value);
}


function romanToInteger(value: string): number {
  const map: Record<string, number> = { I: 1, V: 5, X: 10, L: 50, C: 100, D: 500, M: 1000 };
  if (!/^[IVXLCDM]+$/.test(value)) throw new Error(`invalid Roman volume: ${value}`);
  let result = 0;
  let previous = 0;
  for (const character of [...value].reverse()) {
    const current = map[character];
    if (!current) throw new Error(`invalid Roman volume: ${value}`);
    result += current < previous ? -current : current;
    previous = Math.max(previous, current);
  }
  return result;
}


export function loadStories(dataRoot: string, profile: SiteProfile): StoryDocument[] {
  const explicit = process.env.WIRTELPRIMPF_CURRENT_STORY;
  if (explicit) {
    const volume = integerValue(Number(process.env.WIRTELPRIMPF_CURRENT_VOLUME || "1"), "current volume");
    return [parseStoryDocument(readFileSync(explicit, "utf8"), basename(explicit), volume)];
  }
  if (profile === "hub") {
    const currentStory = resolve(dataRoot, "current-story.md");
    const hubSourceRaw = readJson(resolve(dataRoot, "hub-source.json"), false);
    if (existsSync(currentStory) || hubSourceRaw !== null) {
      if (!existsSync(currentStory) || hubSourceRaw === null) {
        throw new Error("hub current story and hub-source.json must exist together");
      }
      const hubSource = objectValue(hubSourceRaw, "hub source");
      if (hubSource.schema_version !== "1.0.0") throw new Error("unsupported hub source schema");
      const volume = integerValue(hubSource.current_volume, "hub current volume");
      const expectedRepository = `Wirtelprimpf-${String(Math.floor((volume - 1) / 50) + 1).padStart(4, "0")}`;
      if (stringValue(hubSource.repository, "hub repository") !== expectedRepository) {
        throw new Error("hub source repository does not match current volume");
      }
      return [parseStoryDocument(readFileSync(currentStory, "utf8"), "current-story.md", volume)];
    }
  }
  const candidates = [resolve(dataRoot, "Wirtelprimpf"), dataRoot];
  for (const directory of candidates) {
    let names: string[];
    try {
      names = readdirSync(directory);
    } catch {
      continue;
    }
    const stories = names
      .map((name) => ({ name, match: name.match(/^Wirtelprimpf_Story_([IVXLCDM]+)\.md$/) }))
      .filter((item): item is { name: string; match: RegExpMatchArray } => Boolean(item.match))
      .map((item) => {
        const volume = romanToInteger(item.match[1] ?? "");
        return parseStoryDocument(readFileSync(resolve(directory, item.name), "utf8"), item.name, volume);
      })
      .sort((left, right) => left.volume - right.volume);
    if (stories.length) return profile === "hub" ? [stories.at(-1)!] : stories;
  }
  return [];
}


function loadCatalog(dataRoot: string): ArchiveEntry[] {
  const path = process.env.WIRTELPRIMPF_CATALOG_PATH || resolve(dataRoot, "publication-catalog.json");
  const payload = readJson(path, false);
  if (payload === null) return [];
  const object = objectValue(payload, "publication catalog");
  if (object.schema_version !== "1.0.0" || !Array.isArray(object.archives)) {
    throw new Error("unsupported publication catalog schema");
  }
  return object.archives.map((raw, index) => {
    const entry = objectValue(raw, `catalog archive ${index}`);
    const archiveIndex = integerValue(entry.archive_index, "archive index");
    const repository = stringValue(entry.repository, "repository");
    if (repository !== `Wirtelprimpf-${String(archiveIndex).padStart(4, "0")}`) {
      throw new Error(`catalog repository naming mismatch: ${repository}`);
    }
    if (entry.verified !== true) throw new Error(`unverified archive leaked into catalog: ${repository}`);
    const volumeStart = integerValue(entry.volume_start, "volume start");
    const volumeEnd = integerValue(entry.volume_end, "volume end");
    const books = archiveBookRange(archiveIndex);
    if (entry.book_start !== undefined && integerValue(entry.book_start, "book start") !== books.bookStart) {
      throw new Error(`catalog book start mismatch: ${repository}`);
    }
    if (entry.book_end !== undefined && integerValue(entry.book_end, "book end") !== books.bookEnd) {
      throw new Error(`catalog book end mismatch: ${repository}`);
    }
    return {
      archive_index: archiveIndex,
      repository,
      github_url: stringValue(entry.github_url, "GitHub URL"),
      pages_url: stringValue(entry.pages_url, "Pages URL"),
      volume_start: volumeStart,
      volume_end: volumeEnd,
      book_start: books.bookStart,
      book_end: books.bookEnd,
      active: entry.active === true,
      sealed: entry.sealed === true,
      verified: true,
      revision: typeof entry.revision === "string" ? entry.revision : null,
    };
  }).sort((left, right) => left.archive_index - right.archive_index);
}


function loadMedia(dataRoot: string, owner: string, repository: string): { media: MediaItem[]; generatedAt: string | null } {
  const path = process.env.WIRTELPRIMPF_MEDIA_MANIFEST || resolve(dataRoot, "media-manifest.json");
  const payload = readJson(path, false);
  if (payload === null) return { media: [], generatedAt: null };
  const object = objectValue(payload, "media manifest");
  if (object.schema_version !== "1.0.0" || !Array.isArray(object.media)) {
    throw new Error("unsupported media manifest schema");
  }
  const media = object.media.map((raw, index): MediaItem => {
    const item = objectValue(raw, `media ${index}`);
    const original = objectValue(item.original, `media ${index} original`);
    const kind = item.kind;
    if (kind !== "story" && kind !== "classic" && kind !== "legacy") throw new Error(`invalid media kind: ${kind}`);
    if (!Array.isArray(item.variants)) throw new Error(`media variants must be an array: ${index}`);
    return {
      asset_id: stringValue(item.asset_id, "asset ID"),
      source_path: stringValue(item.source_path, "source path"),
      kind,
      width: integerValue(item.width, "image width"),
      height: integerValue(item.height, "image height"),
      release_tag: stringValue(item.release_tag, "release tag"),
      original: {
        asset_name: stringValue(original.asset_name, "original asset name"),
        url: assertReleaseAssetUrl(stringValue(original.url, "original URL"), owner, repository),
      },
      variants: item.variants.map((rawVariant, variantIndex) => {
        const variant = objectValue(rawVariant, `media ${index} variant ${variantIndex}`);
        return {
          requested_width: integerValue(variant.requested_width, "requested width"),
          actual_width: integerValue(variant.actual_width, "actual width"),
          actual_height: integerValue(variant.actual_height, "actual height"),
          url: assertReleaseAssetUrl(stringValue(variant.url, "variant URL"), owner, repository),
          mime_type: stringValue(variant.mime_type, "variant MIME type"),
        };
      }).sort((left, right) => left.requested_width - right.requested_width),
    };
  });
  return {
    media: media.reverse(),
    generatedAt: typeof object.generated_at === "string" ? object.generated_at : null,
  };
}


let cached: SiteData | undefined;

export function loadSiteData(): SiteData {
  if (cached) return cached;
  const profile: SiteProfile = process.env.WIRTELPRIMPF_SITE_PROFILE === "archive" ? "archive" : "hub";
  const dataRoot = resolve(process.env.WIRTELPRIMPF_DATA_ROOT || "../data");
  const owner = process.env.WIRTELPRIMPF_GITHUB_OWNER || "H234598";
  const catalog = loadCatalog(dataRoot);
  const archiveManifestRaw = readJson(resolve(dataRoot, "archive-manifest.json"), false);
  const archiveManifest = archiveManifestRaw === null ? null : objectValue(archiveManifestRaw, "archive manifest");
  const archiveIndex = profile === "archive"
    ? integerValue(archiveManifest?.archive_index ?? 1, "archive index")
    : Number(catalog.find((entry) => entry.active)?.archive_index ?? 1);
  const repository = profile === "archive"
    ? stringValue(archiveManifest?.repository ?? `Wirtelprimpf-${String(archiveIndex).padStart(4, "0")}`, "repository")
    : "Wirtelprimpf-generator";
  const mediaRepository = profile === "archive"
    ? repository
    : (process.env.WIRTELPRIMPF_MEDIA_REPOSITORY
      || catalog.find((entry) => entry.active)?.repository
      || "Wirtelprimpf-0001");
  const domain = profile === "hub" ? "wirtelprimpf.telacore.org" : `wirtelprimpf-${String(archiveIndex).padStart(4, "0")}.telacore.org`;
  const stories = loadStories(dataRoot, profile);
  const media = loadMedia(dataRoot, owner, mediaRepository);
  cached = {
    profile,
    archiveIndex,
    repository,
    domain,
    title: process.env.WIRTELPRIMPF_SITE_TITLE || (profile === "hub" ? "Wirtelprimpfs Geschichtenatelier" : `Wirtelprimpf · Archiv ${String(archiveIndex).padStart(4, "0")}`),
    intro: process.env.WIRTELPRIMPF_SITE_INTRO || "Zwei Katzen, eine Möhre, eine Maus und ein fortlaufendes Abenteuer.",
    catalog,
    stories,
    currentStory: stories.at(-1) ?? null,
    media: media.media,
    generatedAt: media.generatedAt,
  };
  return cached;
}
