import type { APIRoute } from "astro";

import { loadSiteData } from "../lib/data.ts";

export const GET: APIRoute = ({ site }) => {
  const data=loadSiteData();
  const paths=["/","/bilder/","/geschichten/","/projekt/","/projekt/status/",...data.media.map((item)=>`/bilder/${item.asset_id}/`),...data.stories.map((story)=>`/geschichten/${story.volume}/`)];
  const urls=paths.map((path)=>`<url><loc>${new URL(path,site)}</loc></url>`).join("");
  return new Response(`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls}</urlset>`,{headers:{"Content-Type":"application/xml; charset=utf-8"}});
};
