export interface DownloadTarget {
  asset_name: string;
  url: string;
}

export interface ResolvedDownload {
  filename: string;
  href: string;
}

function safeFilename(value: string): string | null {
  const filename = value.trim();
  if (!filename || filename === "." || filename === "..") return null;
  if (filename.includes("/") || filename.includes("\\") || /[\u0000-\u001f]/.test(filename)) return null;
  return filename;
}

function isReleaseAssetUrl(value: string): boolean {
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return false;
  }
  const segments = url.pathname.split("/").filter(Boolean);
  return url.protocol === "https:"
    && url.hostname === "github.com"
    && !url.username
    && !url.password
    && !url.search
    && !url.hash
    && segments.length === 6
    && segments[2] === "releases"
    && segments[3] === "download"
    && /^archive-\d{4}-media-\d{4}$/.test(segments[4] ?? "")
    && /^[A-Za-z0-9._-]*[a-f0-9]{16}[A-Za-z0-9._-]*$/.test(segments[5] ?? "");
}

export function resolveDownload(target: DownloadTarget | null | undefined): ResolvedDownload | null {
  if (!target || typeof target.url !== "string" || typeof target.asset_name !== "string") return null;
  if (!isReleaseAssetUrl(target.url)) return null;
  const filename = safeFilename(target.asset_name);
  return filename ? { href: target.url, filename } : null;
}
