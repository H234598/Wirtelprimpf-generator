import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { renderSafeMarkdown } from "./content.ts";


export interface ReadmeSection {
  title: string;
  markdown: string;
  html: string;
}


export interface RepositoryDocument {
  path: string;
  markdown: string;
  html: string;
}


const FENCE = /^ {0,3}(`{3,}|~{3,})/;
const HEADING = /^(#{1,6})[ \t]+(.+?)[ \t]*$/;
const REPOSITORY_DOCUMENT = "https://github.com/H234598/Wirtelprimpf-generator/blob/main/";
const REPOSITORY = "https://github.com/H234598/";
const LOCAL_PATH = /\/(?:home|root)\/[A-Za-z0-9._/-]+/g;
const INTERNAL_DOCUMENT_ROUTES: Record<string, string> = {
  "docs/WEB-MEDIA.md": "/projekt/web-media/",
  "docs/WEB-MEDIA-SECURITY.md": "/projekt/web-media-security/",
};


function repositoryRoot(): string {
  return process.env.WIRTELPRIMPF_REPOSITORY_ROOT || resolve(process.cwd(), "..");
}


function readmePath(): string {
  return process.env.WIRTELPRIMPF_README_PATH || resolve(repositoryRoot(), "README.md");
}


function renderSection(title: string, markdown: string): ReadmeSection {
  return { title, markdown, html: renderSafeMarkdown(publicMarkdown(markdown)) };
}


function publicMarkdown(markdown: string): string {
  const withDocumentRoutes = markdown.replace(/\]\((?![a-z][a-z0-9+.-]*:|\/|#)([^)\s]+)\)/gi, (_match, target: string) => {
    const [path, fragment] = target.split("#", 2);
    const route = INTERNAL_DOCUMENT_ROUTES[path ?? ""];
    if (route) return `](${route}${fragment ? `#${fragment}` : ""})`;
    return `](${REPOSITORY_DOCUMENT}${target})`;
  });
  const withRepositoryLinks = withDocumentRoutes.replace(/`(Wirtelprimpf-\d{4})`/g, (_match, repository: string) => {
    return `[${repository}](${REPOSITORY}${repository})`;
  });
  return withRepositoryLinks.replace(LOCAL_PATH, "<lokaler-medienbestand>");
}


function repositoryDocumentPath(relativePath: string): string {
  if (!relativePath || relativePath.startsWith("/") || relativePath.includes("\\")) {
    throw new Error(`repository document path must be relative: ${relativePath}`);
  }
  const root = resolve(repositoryRoot());
  const candidate = resolve(root, relativePath);
  if (candidate !== root && !candidate.startsWith(`${root}/`)) {
    throw new Error(`repository document escapes repository root: ${relativePath}`);
  }
  return candidate;
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


export function loadRepositoryDocument(relativePath: string): RepositoryDocument {
  const markdown = readFileSync(repositoryDocumentPath(relativePath), "utf8");
  return { path: relativePath, markdown, html: renderSafeMarkdown(publicMarkdown(markdown)) };
}


export function renderReadmeWithoutCodeBlocks(section: ReadmeSection): ReadmeSection {
  const markdown = withoutFencedCodeBlocks(section.markdown);
  return { ...section, markdown, html: renderSafeMarkdown(publicMarkdown(markdown)) };
}
