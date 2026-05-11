import { ChevronDown, ChevronRight, ExternalLink, Eye, EyeOff, Star } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { BodyContent, type ReaderImage } from "./BodyContent";
import { ImageOverlay } from "./ImageOverlay";
import { PostImageExport } from "./PostImageExport";
import { ReplyNode } from "./ReplyNode";
import { StateBlock } from "./StateBlock";
import { displayTitle, formatDate, formatNumber } from "./format";
import {
  allReplyIds,
  readReplyCollapseState,
  writeReplyCollapseState
} from "./replyCollapseState";
import type { PostDetail, PostListItem, ReplyDetail } from "./types";

export interface FocusRequest {
  id: number;
  postId: string | null;
  replyId: string | null;
}

function findReplyPath(replies: ReplyDetail[], replyId: string): string[] | null {
  for (const reply of replies) {
    if (reply.reply_id === replyId) {
      return [reply.reply_id];
    }

    const childPath = findReplyPath(reply.replies, replyId);
    if (childPath) {
      return [reply.reply_id, ...childPath];
    }
  }

  return null;
}

export function ReaderPane({
  post,
  focusRequest,
  loading,
  refreshing = false,
  error,
  empty,
  notInterested,
  favorite,
  onNotInterestedChange,
  onFavoriteChange
}: {
  post: PostDetail | null;
  focusRequest: FocusRequest;
  loading: boolean;
  refreshing?: boolean;
  error: string | null;
  empty: boolean;
  notInterested: boolean;
  favorite: boolean;
  onNotInterestedChange: (postId: string, hidden: boolean) => void;
  onFavoriteChange: (postId: string, favorite: boolean) => void;
}) {
  const articleRef = useRef<HTMLElement | null>(null);
  const handledFocusRequestIdRef = useRef(0);
  const [highlightedReplyId, setHighlightedReplyId] = useState<string | null>(null);
  const [collapsedReplyIds, setCollapsedReplyIds] = useState<Set<string>>(() => new Set());
  const [previewImage, setPreviewImage] = useState<ReaderImage | null>(null);

  useEffect(() => {
    setCollapsedReplyIds(post ? readReplyCollapseState(post.post_id, post.replies) : new Set());
    setPreviewImage(null);
  }, [post]);

  useEffect(() => {
    const article = articleRef.current;
    if (
      focusRequest.id === 0 ||
      handledFocusRequestIdRef.current === focusRequest.id ||
      !article ||
      !post ||
      post.post_id !== focusRequest.postId
    ) {
      return;
    }

    if (!focusRequest.replyId) {
      setHighlightedReplyId(null);
      handledFocusRequestIdRef.current = focusRequest.id;
      return;
    }

    const replyPath = findReplyPath(post.replies, focusRequest.replyId);
    if (replyPath) {
      setCollapsedReplyIds((current) => {
        const next = new Set(current);
        replyPath.forEach((replyId) => next.delete(replyId));
        writeReplyCollapseState(post.post_id, next, post.replies);
        return next;
      });
    } else {
      return;
    }

    const handle = window.setTimeout(() => {
      const target = Array.from(article.querySelectorAll<HTMLElement>("[data-reply-id]")).find(
        (node) => node.dataset.replyId === focusRequest.replyId
      );
      if (!target) {
        return;
      }
      target.scrollIntoView({ block: "center" });
      setHighlightedReplyId(focusRequest.replyId);
      handledFocusRequestIdRef.current = focusRequest.id;
    }, 0);
    const clearHighlight = window.setTimeout(() => setHighlightedReplyId(null), 2600);

    return () => {
      window.clearTimeout(handle);
      window.clearTimeout(clearHighlight);
    };
  }, [focusRequest, post]);

  const toggleReply = (replyId: string) => {
    updateCollapsedReplyIds((current) => {
      const next = new Set(current);
      if (next.has(replyId)) {
        next.delete(replyId);
      } else {
        next.add(replyId);
      }
      return next;
    });
  };

  const expandAllReplies = () => {
    updateCollapsedReplyIds(() => new Set());
  };

  const collapseAllReplies = () => {
    if (!post) {
      return;
    }
    updateCollapsedReplyIds(() => new Set(allReplyIds(post.replies)));
  };

  function updateCollapsedReplyIds(updater: (current: Set<string>) => Set<string>) {
    if (!post) {
      return;
    }

    setCollapsedReplyIds((current) => {
      const next = updater(current);
      writeReplyCollapseState(post.post_id, next, post.replies);
      return next;
    });
  }

  if (loading) {
    return <StateBlock text="Loading post..." />;
  }

  if (error && !post) {
    return <StateBlock text={error} />;
  }

  if (empty || !post) {
    return <StateBlock text="Select a post." />;
  }

  const currentReplyIds = allReplyIds(post.replies);
  const collapsedReplyCount = currentReplyIds.filter((replyId) =>
    collapsedReplyIds.has(replyId)
  ).length;

  return (
    <article ref={articleRef} className="min-w-0" aria-busy={refreshing}>
      {error ? (
        <div className="border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800 sm:px-5">
          {error}
        </div>
      ) : null}
      <div className="border-b border-stone-300 bg-white px-4 py-3 sm:px-5">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <h2 className="text-xl font-semibold leading-7 text-stone-950 sm:text-2xl">
              {displayTitle(post)}
            </h2>
            <MetaLine post={post} />
          </div>
          <div className="flex shrink-0 flex-wrap items-start gap-2 xl:justify-end">
            <button
              type="button"
              aria-pressed={favorite}
              onClick={() => onFavoriteChange(post.post_id, !favorite)}
              className={`inline-flex h-9 shrink-0 items-center justify-center gap-2 rounded-md border px-3 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-emerald-600 ${
                favorite
                  ? "border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100"
                  : "border-stone-300 bg-[#fffdf8] text-stone-800 hover:bg-stone-50"
              }`}
              title={favorite ? "Remove favorite" : "Add favorite"}
            >
              <Star className={`h-4 w-4 ${favorite ? "fill-current" : ""}`} />
              {favorite ? "Favorited" : "Favorite"}
            </button>
            <button
              type="button"
              aria-pressed={notInterested}
              onClick={() => onNotInterestedChange(post.post_id, !notInterested)}
              className={`inline-flex h-9 shrink-0 items-center justify-center gap-2 rounded-md border px-3 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-emerald-600 ${
                notInterested
                  ? "border-red-200 bg-red-50 text-red-800 hover:bg-red-100"
                  : "border-stone-300 bg-[#fffdf8] text-stone-800 hover:bg-stone-50"
              }`}
              title={notInterested ? "Undo hide" : "Hide"}
            >
              {notInterested ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
              {notInterested ? "Undo hide" : "Hide"}
            </button>
            <PostImageExport post={post} />
            <a
              href={post.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-9 shrink-0 items-center justify-center gap-2 rounded-md border border-stone-300 bg-[#fffdf8] px-3 text-sm font-medium text-stone-800 transition hover:bg-stone-50 focus:outline-none focus:ring-2 focus:ring-emerald-600"
            >
              <ExternalLink className="h-4 w-4" />
              Open
            </a>
          </div>
        </div>
      </div>

      <div className="px-4 py-4 sm:px-5">
        <BodyContent
          html={post.body_html}
          text={post.body_text}
          className="text-base leading-7 text-stone-900"
          onImageOpen={setPreviewImage}
        />
      </div>

      <div className="border-t border-stone-300 px-4 py-4 sm:px-5">
        <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-stone-950">Replies</h3>
            <span className="rounded-sm bg-amber-100 px-2 py-1 text-xs font-medium text-amber-900">
              {formatNumber(post.actual_reply_count)}
            </span>
          </div>
          {post.replies.length > 0 ? (
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={expandAllReplies}
                disabled={collapsedReplyCount === 0}
                className="inline-flex h-8 items-center justify-center gap-1.5 rounded-md border border-stone-300 bg-white px-2.5 text-sm font-medium text-stone-700 transition hover:bg-stone-50 focus:outline-none focus:ring-2 focus:ring-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <ChevronDown className="h-4 w-4" />
                Expand all
              </button>
              <button
                type="button"
                onClick={collapseAllReplies}
                disabled={collapsedReplyCount === currentReplyIds.length}
                className="inline-flex h-8 items-center justify-center gap-1.5 rounded-md border border-stone-300 bg-white px-2.5 text-sm font-medium text-stone-700 transition hover:bg-stone-50 focus:outline-none focus:ring-2 focus:ring-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <ChevronRight className="h-4 w-4" />
                Collapse all
              </button>
            </div>
          ) : null}
        </div>
        {post.replies.length > 0 ? (
          <div className="space-y-3">
            {post.replies.map((reply) => (
              <ReplyNode
                key={reply.reply_id}
                reply={reply}
                highlightedReplyId={highlightedReplyId}
                collapsedReplyIds={collapsedReplyIds}
                onToggle={toggleReply}
                onImageOpen={setPreviewImage}
              />
            ))}
          </div>
        ) : (
          <div className="border border-stone-300 bg-white px-3 py-6 text-center text-sm text-stone-600">
            No replies.
          </div>
        )}
      </div>
      {previewImage ? (
        <ImageOverlay image={previewImage} onClose={() => setPreviewImage(null)} />
      ) : null}
    </article>
  );
}

function MetaLine({ post }: { post: PostDetail | PostListItem }) {
  return (
    <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-sm text-stone-600">
      <span>{post.author || "Unknown author"}</span>
      <span>{formatDate(post.published_at)}</span>
      <span>{formatNumber(post.read_count)} reads</span>
      <span>{formatNumber(post.actual_reply_count)} replies</span>
      <span>#{post.post_id}</span>
    </div>
  );
}
