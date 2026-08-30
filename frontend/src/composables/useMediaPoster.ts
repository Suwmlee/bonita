import type { MediaItemWithWatches } from "@/client"
import { OpenAPI } from "@/client"
import { ref } from "vue"

const IMDB_POSTER_CDN = "https://images.metahub.space/poster/medium"

export function getItemImdbId(item: MediaItemWithWatches): string | null {
  const raw = item.media_type === "episode" ? item.series_imdb_id : item.imdb_id
  const id = raw?.trim()
  if (!id) return null
  return id.startsWith("tt") ? id : `tt${id}`
}

export function getImdbPosterUrl(imdbId: string): string {
  return `${IMDB_POSTER_CDN}/${encodeURIComponent(imdbId)}/img`
}

export function getPosterUrl(item: MediaItemWithWatches): string {
  const params = new URLSearchParams()
  const isEpisode = item.media_type === "episode"

  params.append(
    "title",
    isEpisode ? item.original_title || item.title : item.title,
  )

  const imdbId = isEpisode ? item.series_imdb_id : item.imdb_id
  if (imdbId) params.append("imdb_id", imdbId)

  const tmdbId = isEpisode ? item.series_tmdb_id : item.tmdb_id
  if (tmdbId) params.append("tmdb_id", tmdbId.toString())

  if (item.number) params.append("number", item.number)
  if (item.media_type === "video" && item.emby_item_id) {
    params.append("emby_id", item.emby_item_id)
  }
  if (item.updatetime) params.append("t", item.updatetime)

  return `${OpenAPI.BASE}/api/v1/resource/poster?${params.toString()}`
}

export function useMediaPoster() {
  const posterSrcOverrides = ref<Record<number, string>>({})
  const posterBroken = ref<Record<number, boolean>>({})

  function getDisplayPosterUrl(item: MediaItemWithWatches): string {
    return posterSrcOverrides.value[item.id] || getPosterUrl(item)
  }

  function handlePosterError(item: MediaItemWithWatches, event: Event) {
    const failedSrc = (event.target as HTMLImageElement | null)?.src || ""
    const imdbId = getItemImdbId(item)
    const fallback = imdbId ? getImdbPosterUrl(imdbId) : null

    if (fallback && failedSrc !== fallback) {
      posterSrcOverrides.value[item.id] = fallback
      return
    }

    posterBroken.value[item.id] = true
  }

  return {
    posterBroken,
    getPosterUrl,
    getDisplayPosterUrl,
    handlePosterError,
  }
}
