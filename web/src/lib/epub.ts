import { existsSync, readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { relative, resolve } from "node:path";

import { assertReleaseAssetUrl } from "./content.ts";


const EPUB_MIME = "application/epub+zip";
const EPUB_MANIFEST = "epub-manifest.json";


export interface EpubDownload {
  volume: number;
  asset_name: string;
  url: string;
  size_bytes: number;
  sha256: string;
  mime_type: typeof EPUB_MIME;
}


function objectValue(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${label} must be an object`);
  return value as Record<string, unknown>;
}


function stringValue(value: unknown, label: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${label} must be a non-empty string`);
  return value;
}


function positiveInteger(value: unknown, label: string): number {
  if (!Number.isSafeInteger(value) || Number(value) < 1) throw new Error(`${label} must be a positive integer`);
  return Number(value);
}


function isInside(root: string, candidate: string): boolean {
  const path = relative(root, candidate);
  return path === "" || (path !== ".." && !path.startsWith("../") && !path.startsWith("..\\"));
}


function sha256(bytes: Buffer): string {
  return createHash("sha256").update(bytes).digest("hex");
}


export function isValidEpubBytes(bytes: Buffer): boolean {
  if (bytes.length < 30 || bytes.toString("ascii", 0, 4) !== "PK\x03\x04") return false;
  const flags = bytes.readUInt16LE(6);
  const method = bytes.readUInt16LE(8);
  const compressedSize = bytes.readUInt32LE(18);
  const uncompressedSize = bytes.readUInt32LE(22);
  const nameLength = bytes.readUInt16LE(26);
  const extraLength = bytes.readUInt16LE(28);
  const nameStart = 30;
  const dataStart = nameStart + nameLength + extraLength;
  if (flags !== 0 || method !== 0 || compressedSize !== uncompressedSize || dataStart > bytes.length) return false;
  if (bytes.toString("utf8", nameStart, nameStart + nameLength) !== "mimetype") return false;
  return bytes.toString("utf8", dataStart, dataStart + uncompressedSize) === EPUB_MIME;
}


export function formatDownloadSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}


export function loadEpubDownloads(dataRoot: string, owner: string, repository: string): EpubDownload[] {
  const path = process.env.WIRTELPRIMPF_EPUB_MANIFEST || resolve(dataRoot, EPUB_MANIFEST);
  if (!existsSync(path)) return [];
  let payload: unknown;
  try {
    payload = JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    throw new Error(`cannot read EPUB manifest ${path}: ${String(error)}`);
  }
  const object = objectValue(payload, "EPUB manifest");
  if (object.schema_version !== "1.0.0" || !Array.isArray(object.downloads)) {
    throw new Error("unsupported EPUB manifest schema");
  }
  const seen = new Set<number>();
  return object.downloads.map((raw, index): EpubDownload => {
    const item = objectValue(raw, `EPUB download ${index}`);
    const volume = positiveInteger(item.volume, "EPUB volume");
    if (seen.has(volume)) throw new Error(`duplicate EPUB volume: ${volume}`);
    seen.add(volume);
    const assetName = stringValue(item.asset_name, "EPUB asset name");
    if (!/^[A-Za-z0-9._-]+\.epub$/i.test(assetName)) throw new Error(`invalid EPUB asset name: ${assetName}`);
    const url = assertReleaseAssetUrl(stringValue(item.url, "EPUB URL"), owner, repository);
    if (decodeURIComponent(url.slice(url.lastIndexOf("/") + 1)) !== assetName) {
      throw new Error(`EPUB URL asset mismatch: ${assetName}`);
    }
    const sizeBytes = positiveInteger(item.size_bytes, "EPUB size");
    const digest = stringValue(item.sha256, "EPUB SHA-256").toLowerCase();
    if (!/^[a-f0-9]{64}$/.test(digest)) throw new Error(`invalid EPUB SHA-256: ${digest}`);
    if (item.mime_type !== EPUB_MIME || item.header_verified !== true || item.release_asset_verified !== true) {
      throw new Error(`EPUB ${assetName} lacks validated header/release metadata`);
    }
    const localPath = item.local_path;
    if (localPath !== undefined) {
      const relativePath = stringValue(localPath, "EPUB local path");
      const candidate = resolve(dataRoot, relativePath);
      if (!isInside(resolve(dataRoot), candidate) || !existsSync(candidate)) {
        throw new Error(`EPUB local file is unavailable: ${relativePath}`);
      }
      const bytes = readFileSync(candidate);
      if (bytes.length !== sizeBytes || sha256(bytes) !== digest || !isValidEpubBytes(bytes)) {
        throw new Error(`EPUB local file failed validation: ${relativePath}`);
      }
    }
    return {
      volume,
      asset_name: assetName,
      url,
      size_bytes: sizeBytes,
      sha256: digest,
      mime_type: EPUB_MIME,
    };
  }).sort((left, right) => left.volume - right.volume);
}
