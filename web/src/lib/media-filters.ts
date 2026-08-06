import type { MediaItem } from "./data.ts";


const MISC_TEST_TOKEN = /(?:^|[/_.-])(?:test|testbild)(?:$|[/_.-])/i;


export function isMiscMedia(item: Pick<MediaItem, "kind" | "source_path" | "asset_id">): boolean {
  return item.kind === "unknown"
    || MISC_TEST_TOKEN.test(item.source_path)
    || MISC_TEST_TOKEN.test(item.asset_id);
}
