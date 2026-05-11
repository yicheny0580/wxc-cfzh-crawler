export type FavoriteFilterPreference = "all" | "favorites";

const FAVORITE_POSTS_STORAGE_KEY = "cfzh-inspector.favorite-post-ids.v1";

export const DEFAULT_FAVORITE_FILTER: FavoriteFilterPreference = "all";

export function readFavoritePostIds(): Set<string> {
  if (typeof window === "undefined") {
    return new Set();
  }

  try {
    const storedPostIds = window.localStorage.getItem(FAVORITE_POSTS_STORAGE_KEY);
    if (!storedPostIds) {
      return new Set();
    }

    const parsedPostIds: unknown = JSON.parse(storedPostIds);
    if (!Array.isArray(parsedPostIds)) {
      return new Set();
    }

    return new Set(
      parsedPostIds.filter(
        (postId): postId is string => typeof postId === "string" && postId.length > 0
      )
    );
  } catch {
    return new Set();
  }
}

export function writeFavoritePostIds(postIds: Set<string>) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    if (postIds.size === 0) {
      window.localStorage.removeItem(FAVORITE_POSTS_STORAGE_KEY);
      return;
    }
    window.localStorage.setItem(
      FAVORITE_POSTS_STORAGE_KEY,
      JSON.stringify(Array.from(postIds).sort())
    );
  } catch {
    return;
  }
}
