import { useCallback, useEffect, useRef, useState } from "react";

import { getPost } from "./api";
import type { PostDetail } from "./types";

export function useSelectedPost(
  selectedPostId: string | null,
  reloadToken: number,
  refreshingAfterCrawlRef: { current: boolean }
) {
  const [selectedPost, setSelectedPost] = useState<PostDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const selectedPostRef = useRef<PostDetail | null>(null);
  selectedPostRef.current = selectedPost;

  useEffect(() => {
    if (!selectedPostId) {
      return;
    }

    let active = true;
    setDetailLoading(true);
    setDetailError(null);
    const preserveCurrentPost =
      refreshingAfterCrawlRef.current && selectedPostRef.current?.post_id === selectedPostId;
    getPost(selectedPostId)
      .then((payload) => {
        if (active) {
          setSelectedPost(payload);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setDetailError(err instanceof Error ? err.message : "Failed to load post.");
          if (!preserveCurrentPost) {
            setSelectedPost(null);
          }
        }
      })
      .finally(() => {
        if (active) {
          setDetailLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [selectedPostId, reloadToken, refreshingAfterCrawlRef]);

  const clearSelectedPost = useCallback(() => setSelectedPost(null), []);

  return {
    clearSelectedPost,
    detailError,
    detailLoading,
    selectedPost
  };
}
