import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { renderSafeMarkdown } from "./content.ts";


export interface ReadmeSection {
  title: string;
  markdown: string;
  html: string;
}


const FENCE = /^ {0,3}(`{3,}|~{3,})/;
const HEADING = /^(#{1,6})[ \t]+(.+?)[ \t]*$/;
const REPOSITORY_DOCUMENT = "https://github.com/H234598/Wirtelprimpf-generator/blob/main/";


function readmePath(): string {
  return process.env.WIRTELPRIMPF_README_PATH || resolve(process.cwd(), "../README.md");
}


function renderSection(title: string, markdown: string): ReadmeSection {
  return { title, markdown, html: renderSafeMarkdown(publicMarkdown(markdown)) };
}


function publicMarkdown(markdown: string): string {
  return markdown.replace(/\]\((?![a-z][a-z0-9+.-]*:|\/|#)([^)\s]+)\)/gi, (_match, target: string) => {
    return `](${REPOSITORY_DOCUMENT}${target})`;
  });
}


export function parseReadmeSections(markdown: string): ReadmeSection[] {
  const lines = markdown.replace(/\r\n?/g, "\n").split("\n");
  const sections: Array<{ title: string; lines: string[] }> = [];
  let current: { title: string; lines: string[] } | null = null;
  let inFence = false;

  for (const line of lines) {
    if (FENCE.test(line)) {
      inFence = !inFence;
      if (current) current.lines.push(line);
      continue;
    }
    const heading = !inFence ? HEADING.exec(line) : null;
    if (heading) {
      if (current) sections.push(current);
      current = { title: heading[2]!.trim(), lines: [] };
    } else if (current) {
      current.lines.push(line);
    }
  }
  if (inFence) throw new Error("README contains an unclosed fenced code block");
  if (current) sections.push(current);

  return sections.map(({ title, lines }) => renderSection(title, lines.join("\n").trim()));
}


export function withoutFencedCodeBlocks(markdown: string): string {
  const lines = markdown.replace(/\r\n?/g, "\n").split("\n");
  const visible: string[] = [];
  let inFence = false;
  for (const line of lines) {
    if (FENCE.test(line)) {
      inFence = !inFence;
      continue;
    }
    if (!inFence) visible.push(line);
  }
  if (inFence) throw new Error("README contains an unclosed fenced code block");
  return visible.join("\n").trim();
}


export function loadReadmeSections(titles: readonly string[]): ReadmeSection[] {
  const source = readFileSync(readmePath(), "utf8");
  const sections = parseReadmeSections(source);
  const byTitle = new Map(sections.map((section) => [section.title, section]));
  const missing = titles.filter((title) => !byTitle.has(title));
  if (missing.length) throw new Error(`README sections missing: ${missing.join(", ")}`);
  return titles.map((title) => byTitle.get(title)!);
}


export function renderReadmeWithoutCodeBlocks(section: ReadmeSection): ReadmeSection {
  const markdown = withoutFencedCodeBlocks(section.markdown);
  return { ...section, markdown, html: renderSafeMarkdown(publicMarkdown(markdown)) };
}
