import type { APIRoute } from "astro";

import { sortStoryPartsNewestFirst } from "../lib/content.ts";
import { loadSiteData } from "../lib/data.ts";
import { chapterPath } from "../lib/story-routes.ts";

function escapeXml(value: string): string {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

export const GET: APIRoute = ({ site }) => {
  const data = loadSiteData();
  const base = site ?? new URL(`https://${data.domain}`);
  const parts = data.currentStory ? sortStoryPartsNewestFirst(data.currentStory.parts).slice(0, 20) : [];
  const updated = parts[0] ? `${parts[0].timestamp.replace(" ", "T")}+02:00` : new Date(0).toISOString();
  const entries = parts.map((part) => {
    const path = data.currentStory ? chapterPath(data.currentStory.volume, part.id) : "/geschichten/";
    const url = new URL(path, base);
    return `<entry><id>${url}</id><title>Teil ${part.sequence}: ${escapeXml(data.currentStory?.title ?? "Wirtelprimpf")}</title><updated>${escapeXml(part.timestamp.replace(" ", "T") + "+02:00")}</updated><link href="${url}"/><content type="html">${escapeXml(part.html)}</content></entry>`;
  }).join("");
  const body = `<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom"><id>${base}</id><title>${escapeXml(data.title)}</title><updated>${updated}</updated><link href="${new URL("/feed.xml", base)}" rel="self"/>${entries}</feed>`;
  return new Response(body, { headers: { "Content-Type": "application/atom+xml; charset=utf-8" } });
};
