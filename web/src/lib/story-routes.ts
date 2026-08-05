import type { StoryDocument, StoryPart } from "./content.ts";
import type { MediaItem } from "./data.ts";


const SAFE_CHAPTER_ID = /^band-\d{4}-teil-[a-f0-9]{12}$/;
const STORY_PART_TIMESTAMP = /(\d{4}-\d{2}-\d{2})[_T ](\d{2})[-:](\d{2})[-:](\d{2})/;


export interface ChapterNavigation {
  previous: StoryPart | null;
  next: StoryPart | null;
}


export interface StoryChapterRelation {
  story: StoryDocument;
  part: StoryPart;
}


export function isSafeChapterId(value: string): boolean {
  return SAFE_CHAPTER_ID.test(value);
}


export function storyBandPath(volume: number): string {
  if (!Number.isSafeInteger(volume) || volume < 1) {
    throw new Error(`story volume must be a positive integer: ${volume}`);
  }
  return `/geschichten/${volume}/`;
}


export function chapterPath(volume: number, chapterId: string): string {
  if (!isSafeChapterId(chapterId)) {
    throw new Error(`unsafe chapter id: ${chapterId}`);
  }
  return `${storyBandPath(volume)}${encodeURIComponent(chapterId)}/`;
}


export function chapterAnchor(chapterId: string): string {
  if (!isSafeChapterId(chapterId)) {
    throw new Error(`unsafe chapter id: ${chapterId}`);
  }
  return `#${encodeURIComponent(chapterId)}`;
}


export function findStoryPart(story: StoryDocument, chapterId: string): StoryPart | null {
  if (!isSafeChapterId(chapterId)) return null;
  return story.parts.find((part) => part.id === chapterId) ?? null;
}


export function chapterNavigation(story: StoryDocument, chapterId: string): ChapterNavigation {
  const index = story.parts.findIndex((part) => part.id === chapterId);
  if (index < 0) return { previous: null, next: null };
  return {
    previous: story.parts[index - 1] ?? null,
    next: story.parts[index + 1] ?? null,
  };
}


export function chapterMediaHref(item: MediaItem): string {
  return `/bilder/${encodeURIComponent(item.asset_id)}/`;
}


function timestampFromStoryPartPath(path: string): string | null {
  const match = STORY_PART_TIMESTAMP.exec(path);
  if (!match) return null;
  return `${match[1]} ${match[2]}:${match[3]}:${match[4]}`;
}


export function chapterForMedia(item: MediaItem, stories: readonly StoryDocument[]): StoryChapterRelation | null {
  if (!item.story_part_path) return null;
  if (item.story_part_id) {
    for (const story of stories) {
      const part = findStoryPart(story, item.story_part_id);
      if (part) return { story, part };
    }
  }
  const path = item.story_part_path.replaceAll("\\", "/");
  const fragment = path.match(/#([^#]+)$/)?.[1];
  if (fragment && isSafeChapterId(fragment)) {
    for (const story of stories) {
      const part = findStoryPart(story, fragment);
      if (part) return { story, part };
    }
  }
  const timestamp = timestampFromStoryPartPath(path);
  if (!timestamp) return null;
  const matches = stories.flatMap((story) => story.parts
    .filter((part) => part.timestamp === timestamp)
    .map((part) => ({ story, part })));
  return matches.length === 1 ? matches[0]! : null;
}


export function mediaForChapter(
  media: readonly MediaItem[],
  story: StoryDocument,
  part: StoryPart,
): MediaItem[] {
  return media.filter((item) => {
    const relation = chapterForMedia(item, [story]);
    return relation?.part.id === part.id;
  });
}
