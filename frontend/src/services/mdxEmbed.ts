/** Builds embed URLs from a provider + id. Arbitrary URLs are never embedded: the id must match the provider's strict pattern. */
const PROVIDERS: Record<string, { pattern: RegExp; url: (id: string) => string }> = {
  youtube: { pattern: /^[\w-]{11}$/, url: (id) => `https://www.youtube-nocookie.com/embed/${id}` },
  vimeo: { pattern: /^\d{1,12}$/, url: (id) => `https://player.vimeo.com/video/${id}` },
  loom: { pattern: /^[a-f0-9]{32}$/, url: (id) => `https://www.loom.com/embed/${id}` },
  codepen: { pattern: /^[\w-]{1,40}\/[\w-]{1,20}$/, url: (id) => `https://codepen.io/${id.replace("/", "/embed/")}` },
}

export function buildEmbedUrl(provider: string, id: string): string | null {
  const p = PROVIDERS[provider]
  if (!p || !p.pattern.test(id)) return null
  return p.url(id)
}
