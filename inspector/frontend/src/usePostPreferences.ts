import { useMemo, useState, type Dispatch, type SetStateAction } from "react";

import {
  DEFAULT_FAVORITE_FILTER,
  readFavoritePostIds,
  type FavoriteFilterPreference,
  writeFavoritePostIds
} from "./favoritePosts";
import {
  DEFAULT_INTEREST_FILTER,
  readNotInterestedPostIds,
  type InterestFilterPreference,
  writeNotInterestedPostIds
} from "./notInterestedPosts";

type StoredPostIdSetter = Dispatch<SetStateAction<Set<string>>>;

export function usePostPreferences() {
  const [interestFilter, setInterestFilter] =
    useState<InterestFilterPreference>(DEFAULT_INTEREST_FILTER);
  const [favoriteFilter, setFavoriteFilter] =
    useState<FavoriteFilterPreference>(DEFAULT_FAVORITE_FILTER);
  const [notInterestedPostIds, setNotInterestedPostIds] =
    useState<Set<string>>(readNotInterestedPostIds);
  const [favoritePostIds, setFavoritePostIds] = useState<Set<string>>(readFavoritePostIds);
  const [pendingHidePostId, setPendingHidePostId] = useState<string | null>(null);

  const notInterestedPostIdList = useMemo(
    () => sortedPostIds(notInterestedPostIds),
    [notInterestedPostIds]
  );
  const favoritePostIdList = useMemo(() => sortedPostIds(favoritePostIds), [favoritePostIds]);

  const applyNotInterestedPostState = (postId: string, hidden: boolean) => {
    updateStoredPostIds(setNotInterestedPostIds, writeNotInterestedPostIds, (current) => {
      if (hidden) {
        current.add(postId);
      } else {
        current.delete(postId);
      }
      return current;
    });
    if (hidden) {
      updateStoredPostIds(setFavoritePostIds, writeFavoritePostIds, (current) => {
        current.delete(postId);
        return current;
      });
    }
  };

  const requestNotInterestedPostState = (postId: string, hidden: boolean) => {
    if (hidden && !notInterestedPostIds.has(postId)) {
      setPendingHidePostId(postId);
      return;
    }

    applyNotInterestedPostState(postId, hidden);
  };

  const confirmPendingHide = () => {
    if (!pendingHidePostId) {
      return;
    }

    applyNotInterestedPostState(pendingHidePostId, true);
    setPendingHidePostId(null);
  };

  const applyFavoritePostState = (postId: string, favorite: boolean) => {
    updateStoredPostIds(setFavoritePostIds, writeFavoritePostIds, (current) => {
      if (favorite) {
        current.add(postId);
      } else {
        current.delete(postId);
      }
      return current;
    });
    if (favorite) {
      updateStoredPostIds(setNotInterestedPostIds, writeNotInterestedPostIds, (current) => {
        current.delete(postId);
        return current;
      });
    }
  };

  const clearPostPreferenceFilters = () => {
    setInterestFilter(DEFAULT_INTEREST_FILTER);
    setFavoriteFilter(DEFAULT_FAVORITE_FILTER);
  };

  return {
    clearPostPreferenceFilters,
    confirmPendingHide,
    favoriteFilter,
    favoritePostIdList,
    favoritePostIds,
    interestFilter,
    notInterestedPostIdList,
    notInterestedPostIds,
    pendingHidePostId,
    requestNotInterestedPostState,
    setFavoriteFilter,
    setInterestFilter,
    setPendingHidePostId,
    updateFavoritePostState: applyFavoritePostState
  };
}

function sortedPostIds(postIds: Set<string>): string[] {
  return Array.from(postIds).sort();
}

function updateStoredPostIds(
  setPostIds: StoredPostIdSetter,
  writePostIds: (postIds: Set<string>) => void,
  updater: (postIds: Set<string>) => Set<string>
) {
  setPostIds((current) => {
    const next = updater(new Set(current));
    if (postIdsEqual(current, next)) {
      return current;
    }
    writePostIds(next);
    return next;
  });
}

function postIdsEqual(left: Set<string>, right: Set<string>): boolean {
  return left.size === right.size && Array.from(left).every((postId) => right.has(postId));
}
