export type FreshnessState = "fresh" | "warning" | "stale" | "unknown";

export interface PublicWebStatus {
  schema_version: "1.0.0";
  profile: "hub" | "archive";
  repository: string;
  archive_index: number | null;
  source_revision: string | null;
  media: {
    count: number;
    latest_id: string | null;
    latest_source_path: string | null;
    latest_sha256: string | null;
  };
  stories: {
    count: number;
    chapter_count: number;
    latest_id: string | null;
    latest_volume: number | null;
    latest_timestamp: string | null;
  };
  publication: { manifest_generated_at: string | null };
  build: { built_at: string; source_date_epoch: number | null };
  freshness: {
    state: FreshnessState;
    last_published_at: string | null;
    age_seconds: number | null;
    warning_after_seconds: number;
    stale_after_seconds: number;
  };
}


function record(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${label} must be an object`);
  return value as Record<string, unknown>;
}


function nullableString(value: unknown, label: string): string | null {
  if (value === null) return null;
  if (typeof value !== "string" || !value.trim()) throw new Error(`${label} must be a non-empty string or null`);
  return value;
}


function nullableInteger(value: unknown, label: string): number | null {
  if (value === null) return null;
  if (!Number.isSafeInteger(value) || Number(value) < 1) throw new Error(`${label} must be a positive integer or null`);
  return Number(value);
}


function nonNegativeInteger(value: unknown, label: string): number {
  if (!Number.isSafeInteger(value) || Number(value) < 0) throw new Error(`${label} must be a non-negative integer`);
  return Number(value);
}


function dateTime(value: unknown, label: string): string | null {
  if (value === null) return null;
  if (typeof value !== "string" || Number.isNaN(Date.parse(value))) throw new Error(`${label} must be an ISO timestamp or null`);
  return value;
}


function safePublicPath(value: string | null, label: string): string | null {
  if (value === null) return null;
  if (value.startsWith("/") || value.includes("\\") || value.split("/").includes("..")) {
    throw new Error(`${label} must not contain a local path`);
  }
  return value;
}


export function parsePublicWebStatus(value: unknown): PublicWebStatus {
  const root = record(value, "web status");
  if (root.schema_version !== "1.0.0") throw new Error("unsupported web status schema");
  if (root.profile !== "hub" && root.profile !== "archive") throw new Error("invalid web status profile");
  if (typeof root.repository !== "string" || !/^[A-Za-z0-9_.-]+$/.test(root.repository)) throw new Error("invalid web status repository");
  const sourceRevision = nullableString(root.source_revision, "source revision");
  if (sourceRevision !== null && !/^[0-9a-f]{40}$/.test(sourceRevision)) throw new Error("invalid source revision");

  const media = record(root.media, "web status media");
  const mediaLatestId = nullableString(media.latest_id, "latest media ID");
  const mediaLatestSource = safePublicPath(nullableString(media.latest_source_path, "latest media source"), "latest media source");
  const mediaLatestHash = nullableString(media.latest_sha256, "latest media hash");
  if (mediaLatestHash !== null && !/^[0-9a-f]{64}$/.test(mediaLatestHash)) throw new Error("invalid latest media hash");

  const stories = record(root.stories, "web status stories");
  const latestStoryId = nullableString(stories.latest_id, "latest chapter ID");
  if (latestStoryId !== null && !/^band-\d{4}-teil-[a-f0-9]{12}$/.test(latestStoryId)) throw new Error("invalid latest chapter ID");
  const latestTimestamp = dateTime(stories.latest_timestamp, "latest chapter timestamp");

  const publication = record(root.publication, "web status publication");
  const build = record(root.build, "web status build");
  const freshness = record(root.freshness, "web status freshness");
  const state = freshness.state;
  if (state !== "fresh" && state !== "warning" && state !== "stale" && state !== "unknown") throw new Error("invalid freshness state");
  const age = freshness.age_seconds === null ? null : nonNegativeInteger(freshness.age_seconds, "freshness age");
  const archiveIndex = nullableInteger(root.archive_index, "archive index");
  const builtAt = dateTime(build.built_at, "build timestamp");
  if (builtAt === null) throw new Error("build timestamp is required");

  return {
    schema_version: "1.0.0",
    profile: root.profile,
    repository: root.repository,
    archive_index: archiveIndex,
    source_revision: sourceRevision,
    media: {
      count: nonNegativeInteger(media.count, "media count"),
      latest_id: mediaLatestId,
      latest_source_path: mediaLatestSource,
      latest_sha256: mediaLatestHash,
    },
    stories: {
      count: nonNegativeInteger(stories.count, "story count"),
      chapter_count: nonNegativeInteger(stories.chapter_count, "chapter count"),
      latest_id: latestStoryId,
      latest_volume: nullableInteger(stories.latest_volume, "latest volume"),
      latest_timestamp: latestTimestamp,
    },
    publication: { manifest_generated_at: dateTime(publication.manifest_generated_at, "manifest timestamp") },
    build: {
      built_at: builtAt,
      source_date_epoch: build.source_date_epoch === null ? null : nonNegativeInteger(build.source_date_epoch, "source date epoch"),
    },
    freshness: {
      state,
      last_published_at: dateTime(freshness.last_published_at, "last published timestamp"),
      age_seconds: age,
      warning_after_seconds: nonNegativeInteger(freshness.warning_after_seconds, "freshness warning threshold"),
      stale_after_seconds: nonNegativeInteger(freshness.stale_after_seconds, "freshness stale threshold"),
    },
  };
}
