import type { MediaItemWithWatches } from "@/client"
import { OpenAPI } from "@/client"
import { request as __request } from "@/client/core/request"
import type { CancelablePromise } from "@/client/core/CancelablePromise"

export type CollectionSyncDirection = "from_server" | "to_server"

export type EmbyCollectionCandidate = {
  emby_id: string
  name: string
  child_count?: number
  image_tag?: string | null
  added?: boolean
}

export type CollectionPublic = {
  id: number
  emby_id: string
  name: string
  image_tag?: string | null
  item_count: number
  matched_count: number
  last_sync_at?: string | null
  createtime: string
  updatetime: string
}

export type CollectionDetail = CollectionPublic & {
  items: Array<MediaItemWithWatches>
}

export type CollectionCollection = {
  data: Array<CollectionPublic>
  count: number
}

export class CollectionService {
  public static searchEmby(search = "", limit = 50): CancelablePromise<Array<EmbyCollectionCandidate>> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/collections/emby",
      query: { search, limit },
    })
  }

  public static list(): CancelablePromise<CollectionCollection> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/collections/",
    })
  }

  public static add(embyId: string, name?: string): CancelablePromise<CollectionPublic> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/collections/",
      body: { emby_id: embyId, name },
      mediaType: "application/json",
    })
  }

  public static get(collectionId: number): CancelablePromise<CollectionDetail> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/collections/{collection_id}",
      path: { collection_id: collectionId },
    })
  }

  public static remove(collectionId: number): CancelablePromise<{ success: boolean; message?: string }> {
    return __request(OpenAPI, {
      method: "DELETE",
      url: "/api/v1/collections/{collection_id}",
      path: { collection_id: collectionId },
    })
  }

  public static syncOne(
    collectionId: number,
    direction: CollectionSyncDirection = "from_server",
  ): CancelablePromise<CollectionPublic> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/collections/{collection_id}/sync",
      path: { collection_id: collectionId },
      query: { direction },
    })
  }

  public static syncAll(
    direction: CollectionSyncDirection = "from_server",
  ): CancelablePromise<{ success: boolean; message?: string }> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/collections/sync",
      query: { direction },
    })
  }

  public static searchCandidates(
    collectionId: number,
    search = "",
    limit = 20,
  ): CancelablePromise<Array<MediaItemWithWatches>> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/collections/{collection_id}/candidates",
      path: { collection_id: collectionId },
      query: { search, limit },
    })
  }

  public static addItems(
    collectionId: number,
    mediaItemIds: number[],
  ): CancelablePromise<CollectionPublic> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/collections/{collection_id}/items",
      path: { collection_id: collectionId },
      body: { media_item_ids: mediaItemIds },
      mediaType: "application/json",
    })
  }

  public static removeItem(
    collectionId: number,
    mediaItemId: number,
  ): CancelablePromise<CollectionPublic> {
    return __request(OpenAPI, {
      method: "DELETE",
      url: "/api/v1/collections/{collection_id}/items/{media_item_id}",
      path: { collection_id: collectionId, media_item_id: mediaItemId },
    })
  }
}
