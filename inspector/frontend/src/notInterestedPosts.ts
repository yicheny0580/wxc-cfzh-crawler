import type { ResultListResponse } from "./types";

export type InterestFilterPreference = "focus" | "show-all";

const NOT_INTERESTED_POSTS_STORAGE_KEY = "cfzh-inspector.not-interested-post-ids.v1";

export const DEFAULT_INTEREST_FILTER: InterestFilterPreference = "focus";

export function readNotInterestedPostIds(): Set<string> {
  if (typeof window === "undefined") {
    return new Set();
  }

  try {
    const storedPostIds = window.localStorage.getItem(NOT_INTERESTED_POSTS_STORAGE_KEY);
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

export function writeNotInterestedPostIds(postIds: Set<string>) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    if (postIds.size === 0) {
      window.localStorage.removeItem(NOT_INTERESTED_POSTS_STORAGE_KEY);
      return;
    }
    window.localStorage.setItem(
      NOT_INTERESTED_POSTS_STORAGE_KEY,
      JSON.stringify(Array.from(postIds).sort())
    );
  } catch {
    return;
  }
}

export function resultsVisibleForInterest(
  results: ResultListResponse | null,
  interestFilter: InterestFilterPreference,
  notInterestedPostIds: Set<string>
): ResultListResponse | null {
  if (!results || interestFilter !== "focus") {
    return results;
  }

  return {
    ...results,
    items: results.items.filter((item) => !notInterestedPostIds.has(item.root_post_id))
  };
}
