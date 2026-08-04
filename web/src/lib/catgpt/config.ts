export const CATGPT_LIGHT_ENDPOINT = "https://catgpt.wirtelprimpf.telacore.org/v1/chat" as const;
export const CATGPT_LIGHT_ORIGIN = "https://catgpt.wirtelprimpf.telacore.org" as const;

export type CatGptLightEndpoint = typeof CATGPT_LIGHT_ENDPOINT;

export function resolveCatGptLightEndpoint(value: string | undefined): CatGptLightEndpoint | undefined {
  return value === CATGPT_LIGHT_ENDPOINT ? CATGPT_LIGHT_ENDPOINT : undefined;
}
