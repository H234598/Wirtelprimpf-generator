import type { APIRoute } from "astro";

import { loadSiteData } from "../lib/data.ts";
import { chapterPath } from "../lib/story-routes.ts";

export const GET: APIRoute = ({ site }) => {
  const data=loadSiteData();
  const paths=["/","/bilder/","/geschichten/","/projekt/","/projekt/status/",...data.media.map((item)=>`/bilder/${item.asset_id}/`),...data.stories.flatMap((story)=>[`/geschichten/${story.volume}/`,...story.parts.map((part)=>chapterPath(story.volume, part.id))])];
  const urls=paths.map((path)=>`<url><loc>${new URL(path,site)}</loc></url>`).join("");
  return new Response(`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls}</urlset>`,{headers:{"Content-Type":"application/xml; charset=utf-8"}});
};
