import { client } from "@/client/client.gen"

const imageUrlCache = new Map<string, string>()

export function resourceImageUrl(path: string) {
  const cached = imageUrlCache.get(path)
  if (cached) return cached
  const url = `${client.getConfig().baseURL}/api/v1/resource/image?path=${encodeURIComponent(path)}&t=${Date.now()}`
  imageUrlCache.set(path, url)
  return url
}
