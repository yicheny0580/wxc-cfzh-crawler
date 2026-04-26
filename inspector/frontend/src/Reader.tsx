import { ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { sanitizeBodyHtml } from "./bodyHtml";
import { StateBlock } from "./StateBlock";
import { countLabel, displayTitle, formatDate, formatNumber } from "./format";
import type { PostDetail, PostListItem, ReplyDetail } from "./types";

export interface FocusRequest {
  id: number;
  postId: string | null;
  replyId: string | null;
}

function descendantReplyCount(reply: ReplyDetail): number {
  return reply.replies.reduce((total, child) => total + 1 + descendantReplyCount(child), 0);
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

function shouldIgnoreReplyToggle(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return true;
  }
  return Boolean(target.closest("a, button, input, select, textarea, label"));
}

export function ReaderPane({
  post,
  focusRequest,
  loading,
  error,
  empty
}: {
  post: PostDetail | null;
  focusRequest: FocusRequest;
  loading: boolean;
  error: string | null;
  empty: boolean;
}) {
  const articleRef = useRef<HTMLElement | null>(null);
  const handledFocusRequestIdRef = useRef(0);
  const [highlightedReplyId, setHighlightedReplyId] = useState<string | null>(null);
  const [collapsedReplyIds, setCollapsedReplyIds] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    setCollapsedReplyIds(new Set());
  }, [post?.post_id]);

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
      const handle = window.setTimeout(() => {
        article.scrollIntoView({ block: "start" });
        setHighlightedReplyId(null);
        handledFocusRequestIdRef.current = focusRequest.id;
      }, 0);
      return () => window.clearTimeout(handle);
    }

    const replyPath = findReplyPath(post.replies, focusRequest.replyId);
    if (replyPath) {
      setCollapsedReplyIds((current) => {
        const next = new Set(current);
        replyPath.forEach((replyId) => next.delete(replyId));
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
    setCollapsedReplyIds((current) => {
      const next = new Set(current);
      if (next.has(replyId)) {
        next.delete(replyId);
      } else {
        next.add(replyId);
      }
      return next;
    });
  };

  if (loading) {
    return <StateBlock text="Loading post..." />;
  }

  if (error) {
    return <StateBlock text={error} />;
  }

  if (empty || !post) {
    return <StateBlock text="Select a post." />;
  }

  return (
    <article ref={articleRef} className="min-w-0">
      <div className="border-b border-stone-300 bg-white px-4 py-3 sm:px-5">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <h2 className="text-xl font-semibold leading-7 text-stone-950 sm:text-2xl">
              {displayTitle(post)}
            </h2>
            <MetaLine post={post} />
          </div>
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

      <div className="px-4 py-4 sm:px-5">
        <BodyContent
          html={post.body_html}
          text={post.body_text}
          className="text-base leading-7 text-stone-900"
        />
      </div>

      <div className="border-t border-stone-300 px-4 py-4 sm:px-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h3 className="text-base font-semibold text-stone-950">Replies</h3>
          <span className="rounded-sm bg-amber-100 px-2 py-1 text-xs font-medium text-amber-900">
            {formatNumber(post.actual_reply_count)}
          </span>
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
              />
            ))}
          </div>
        ) : (
          <div className="border border-stone-300 bg-white px-3 py-6 text-center text-sm text-stone-600">
            No replies.
          </div>
        )}
      </div>
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

function ReplyNode({
  reply,
  highlightedReplyId,
  collapsedReplyIds,
  onToggle
}: {
  reply: ReplyDetail;
  highlightedReplyId: string | null;
  collapsedReplyIds: Set<string>;
  onToggle: (replyId: string) => void;
}) {
  const highlighted = reply.reply_id === highlightedReplyId;
  const collapsed = collapsedReplyIds.has(reply.reply_id);
  const nestedCount = descendantReplyCount(reply);

  return (
    <div className="border-l-2 border-emerald-700 bg-white pl-3" data-reply-id={reply.reply_id}>
      <div
        onClick={(event) => {
          if (shouldIgnoreReplyToggle(event.target) || window.getSelection()?.toString()) {
            return;
          }
          onToggle(reply.reply_id);
        }}
        className={`cursor-pointer border px-3 py-3 transition-colors ${
          highlighted
            ? "border-emerald-500 bg-emerald-50 hover:bg-emerald-100"
            : collapsed
              ? "border-stone-300 bg-stone-50 hover:bg-stone-100"
              : "border-stone-200 hover:border-stone-300 hover:bg-stone-50"
        }`}
      >
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-2 text-sm">
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onToggle(reply.reply_id);
              }}
              className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-stone-500 transition hover:bg-stone-100 hover:text-stone-900 focus:outline-none focus:ring-2 focus:ring-emerald-600"
              title={collapsed ? "Expand reply" : "Collapse reply"}
              aria-label={collapsed ? "Expand reply" : "Collapse reply"}
              aria-expanded={!collapsed}
            >
              {collapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
            <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
              <span className="font-semibold text-stone-950">{reply.author || "Unknown"}</span>
              <span className="text-stone-500">{formatDate(reply.published_at)}</span>
              <span className="text-stone-500">#{reply.reply_id}</span>
              {collapsed && nestedCount > 0 ? (
                <span className="rounded-sm bg-stone-100 px-1.5 py-0.5 text-xs font-medium text-stone-600">
                  {countLabel(nestedCount, "reply")}
                </span>
              ) : null}
            </div>
          </div>
          <a
            href={reply.url}
            target="_blank"
            rel="noreferrer"
            onClick={(event) => event.stopPropagation()}
            className="inline-flex h-7 w-7 items-center justify-center rounded-md text-stone-500 hover:bg-stone-100 hover:text-stone-900"
            title="Open reply"
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        </div>
        {!collapsed ? <ReplyBody reply={reply} /> : null}
      </div>
      {!collapsed && reply.replies.length > 0 ? (
        <div className="mt-3 space-y-3 pl-3">
          {reply.replies.map((child) => (
            <ReplyNode
              key={child.reply_id}
              reply={child}
              highlightedReplyId={highlightedReplyId}
              collapsedReplyIds={collapsedReplyIds}
              onToggle={onToggle}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ReplyBody({ reply }: { reply: ReplyDetail }) {
  if (reply.title) {
    return (
      <>
        <div className="mt-2 text-sm font-medium text-stone-800">{reply.title}</div>
        {reply.body_html || reply.body_text ? (
          <BodyContent
            html={reply.body_html}
            text={reply.body_text}
            className="mt-2 text-sm leading-6 text-stone-800"
          />
        ) : null}
      </>
    );
  }

  if (reply.body_html || reply.body_text) {
    return (
      <BodyContent
        html={reply.body_html}
        text={reply.body_text}
        className="mt-2 text-sm leading-6 text-stone-800"
      />
    );
  }

  return <div className="mt-2 text-sm text-stone-500">No body text.</div>;
}

function BodyContent({
  html,
  text,
  className = ""
}: {
  html: string | null;
  text: string | null;
  className?: string;
}) {
  const sanitizedHtml = useMemo(() => sanitizeBodyHtml(html), [html]);
  const classes = `reader-body ${className}`.trim();

  if (sanitizedHtml) {
    return (
      <div
        className={`reader-body-html ${classes}`}
        dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
      />
    );
  }

  if (text) {
    return <div className={`whitespace-pre-wrap ${classes}`}>{text}</div>;
  }

  return <div className="text-sm text-stone-500">No body text.</div>;
}
