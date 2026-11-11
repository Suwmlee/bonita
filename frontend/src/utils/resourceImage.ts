import { client } from "@/client/client.gen"

const imageUrlCache = new Map<string, string>()

export type ResourceImageHints = {
  number?: string | null
  actor?: string | null
}

function cacheKey(path: string, hints?: ResourceImageHints) {
  const number = (hints?.number || "").trim()
  const actor = (hints?.actor || "").trim()
  return `${path}\0${number}\0${actor}`
}

/** 拼 /resource/image；预览未入库封面/头像时务必传 number 或 actor。 */
export function resourceImageUrl(path: string, hints?: ResourceImageHints) {
  if (!path) return ""
  const key = cacheKey(path, hints)
  const cached = imageUrlCache.get(key)
  if (cached) return cached

  const params = new URLSearchParams()
  params.set("path", path)
  params.set("t", String(Date.now()))
  const number = (hints?.number || "").trim()
  const actor = (hints?.actor || "").trim()
  if (number) params.set("number", number)
  if (actor) params.set("actor", actor)

  const url = `${client.getConfig().baseURL}/api/v1/resource/image?${params.toString()}`
  imageUrlCache.set(key, url)
  return url
}
